import os
import json
import sqlite3
import datetime
import re
import io
import textwrap
import traceback
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────
# Load Regulations Dataset
# ─────────────────────────────────────────
def load_regulations():
    try:
        with open(os.path.join(os.path.dirname(__file__), "data", "regulations.json"), "r", encoding="utf-8") as f:
            return json.load(f).get("regulations", [])
    except Exception as e:
        print(f"[WARN] Could not load regulations.json: {e}")
        return []

REGULATIONS = load_regulations()

# ─────────────────────────────────────────
# SQLite Setup
# ─────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "greencompliance.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                industry TEXT NOT NULL,
                description TEXT NOT NULL,
                risk_level TEXT,
                compliance_score INTEGER,
                issues TEXT,
                recommendations TEXT,
                regulatory_areas TEXT,
                ai_insight TEXT,
                source TEXT DEFAULT 'rule-based',
                created_at TEXT
            )
        """)

try:
    init_db()
except Exception as e:
    print(f"[DB INIT ERROR] {e}")

def save_analysis(data: dict) -> int | None:
    try:
        with get_db() as conn:
            cur = conn.execute("""
                INSERT INTO analyses
                  (industry, description, risk_level, compliance_score,
                   issues, recommendations, regulatory_areas, ai_insight, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("industry", ""),
                data.get("description", ""),
                data.get("risk_level", "Low"),
                int(data.get("compliance_score", 50)),
                json.dumps(data.get("issues", [])),
                json.dumps(data.get("recommendations", [])),
                json.dumps(data.get("regulatory_areas", [])),
                data.get("ai_insight", ""),
                data.get("source", "rule-based"),
                datetime.datetime.now(datetime.timezone.utc).isoformat()
            ))
            return cur.lastrowid
    except Exception as e:
        print(f"[DB SAVE ERROR] {e}")
        return None

# ─────────────────────────────────────────
# Rule-Based Fallback Engine
# ─────────────────────────────────────────
def rule_based_analysis(industry: str, description: str) -> dict:
    text = (description + " " + industry).lower()
    industry_rules = [r for r in REGULATIONS if r.get("industry", "").lower() == industry.lower()]

    matched = []
    for rule in industry_rules:
        keywords = rule.get("keywords", [])
        if any(kw.lower() in text for kw in keywords):
            matched.append(rule)

    # Fallback: use all industry rules if nothing matched
    if not matched:
        matched = industry_rules[:4]  # cap at 4

    # Score calculation
    total_weight = sum(r.get("riskWeight", 1) for r in matched)
    max_weight = max(len(matched) * 5, 1)

    if total_weight >= 8:
        risk_level = "High"
    elif total_weight >= 4:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    compliance_score = max(10, min(100, 100 - int((total_weight / max_weight) * 70)))

    issues = [r["issue"] for r in matched]
    recommendations = [r["recommendation"] for r in matched]
    regulatory_areas = [
        {
            "title": r.get("regulation_title", "N/A"),
            "body":  r.get("regulatory_body", "N/A"),
            "severity": r.get("severity", "Medium")
        }
        for r in matched
    ]

    top_issues = issues[:2] if issues else ["general environmental practices"]
    insight = (
        f"Based on rule-based analysis for the {industry} sector, "
        f"{len(issues)} environmental compliance issue(s) were identified. "
        f"Overall compliance score: {compliance_score}/100 ({risk_level} risk). "
        f"Key concerns: {', '.join(top_issues)}. "
        f"Immediate corrective action is advised on highest-severity items."
    )

    return {
        "risk_level": risk_level,
        "compliance_score": compliance_score,
        "issues": issues,
        "recommendations": recommendations,
        "regulatory_areas": regulatory_areas,
        "ai_insight": insight,
        "source": "rule-based"
    }

# ─────────────────────────────────────────
# Gemini AI Analysis
# ─────────────────────────────────────────
def gemini_analysis(industry: str, description: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key in ("your_gemini_api_key_here", ""):
        raise ValueError("Gemini API key not configured — using rule-based fallback")

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""You are an expert environmental compliance analyst for GreenCompliance AI.

Industry: {industry}
Business Activity: {description}

Analyze this for environmental compliance risks. Return ONLY a valid JSON object with NO markdown, NO code fences:
{{
  "risk_level": "High" or "Medium" or "Low",
  "compliance_score": <integer 0-100>,
  "issues": ["<issue 1>", "<issue 2>", "<issue 3>"],
  "recommendations": ["<rec 1>", "<rec 2>", "<rec 3>"],
  "regulatory_areas": [
    {{"title": "<regulation name>", "body": "<regulatory body>", "severity": "Critical|High|Medium|Low"}}
  ],
  "ai_insight": "<2-3 sentence expert compliance summary with urgent actions>"
}}

Rules:
- compliance_score 80-100 = Low risk; 50-79 = Medium; 0-49 = High
- Include minimum 2 issues, 2 recommendations, 2 regulatory areas
- Be specific to the {industry} industry context"""

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip any markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

    result = json.loads(raw)

    # Validate structure
    for key in ["risk_level", "compliance_score", "issues", "recommendations", "regulatory_areas", "ai_insight"]:
        if key not in result:
            raise ValueError(f"AI response missing key: {key}")

    result["source"] = "gemini-ai"
    return result

# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "Invalid JSON payload"}), 400

        industry    = str(data.get("industry", "")).strip()
        description = str(data.get("description", "")).strip()

        if not industry:
            return jsonify({"error": "Industry is required"}), 400
        if not description or len(description) < 10:
            return jsonify({"error": "Please provide a more detailed description (min 10 characters)"}), 400

        # Try AI first; fall back silently
        result = None
        try:
            result = gemini_analysis(industry, description)
        except Exception as ai_err:
            print(f"[AI Fallback] {ai_err}")
            result = rule_based_analysis(industry, description)

        result["industry"]    = industry
        result["description"] = description

        # Persist result
        result["id"] = save_analysis(result)

        return jsonify(result), 200

    except Exception as e:
        print(f"[/analyze ERROR] {traceback.format_exc()}")
        return jsonify({"error": "Internal server error. Please try again."}), 500


@app.route("/report/<int:analysis_id>")
def get_report(analysis_id):
    try:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()

        if not row:
            return jsonify({"error": "Report not found"}), 404

        issues = json.loads(row["issues"] or "[]")
        recs   = json.loads(row["recommendations"] or "[]")
        regs   = json.loads(row["regulatory_areas"] or "[]")
        score  = row["compliance_score"] or 0
        level  = row["risk_level"] or "Unknown"

        # Score bar visual
        filled = int(score / 5)
        bar = "█" * filled + "░" * (20 - filled)
        risk_emoji = {"High": "🚨", "Medium": "⚠️", "Low": "✅"}.get(level, "")

        W = 70  # line width

        def section(title):
            return f"\n{'─' * W}\n  {title}\n{'─' * W}"

        def wrap_items(items, bullet="•"):
            out = []
            for i, item in enumerate(items, 1):
                prefix = f"  [{i}] "
                wrapped = textwrap.fill(item, width=W - len(prefix),
                                        subsequent_indent=" " * len(prefix))
                out.append(prefix + wrapped)
            return "\n".join(out) if out else "  None identified."

        lines = [
            "═" * W,
            "  GREENCOMPLIANCE AI — ENVIRONMENTAL COMPLIANCE REPORT".center(W),
            "═" * W,
            "",
            f"  Report ID     : #{row['id']}",
            f"  Generated     : {row['created_at']} UTC",
            f"  Analysis By   : {row['source'].upper().replace('-', ' ')}",
            "",

            section("BUSINESS INFORMATION"),
            f"  Industry      : {row['industry']}",
            f"  Description   :",
        ]

        # Wrap description at 65 chars
        for chunk in textwrap.wrap(row["description"], width=65):
            lines.append(f"    {chunk}")

        lines += [
            "",
            section("COMPLIANCE OVERVIEW"),
            f"  Risk Level    : {risk_emoji} {level.upper()}",
            f"  Score         : {score} / 100",
            f"  Rating Bar    : [{bar}] {score}%",
            "",
            "  Score Guide   : 80-100 = Low Risk  |  50-79 = Medium Risk  |  0-49 = High Risk",
            "",

            section(f"ISSUES DETECTED  ({len(issues)} found)"),
            wrap_items(issues),
            "",

            section(f"RECOMMENDED ACTIONS  ({len(recs)} steps)"),
            wrap_items(recs),
            "",

            section(f"APPLICABLE REGULATIONS  ({len(regs)} areas)"),
        ]

        for reg in regs:
            if isinstance(reg, dict):
                sev  = reg.get('severity', 'Medium')
                sev_lbl = {"Critical":"🔴","High":"🟠","Medium":"🟡","Low":"🟢"}.get(sev, "")
                lines.append(f"  {sev_lbl} {reg.get('title','')}")
                if reg.get('body'):
                    lines.append(f"     Regulatory Body: {reg['body']}")
                lines.append(f"     Severity: {sev}")
                lines.append("")

        lines += [
            section("AI EXPERT SUMMARY"),
        ]
        for chunk in textwrap.wrap(row["ai_insight"] or "Not available.", width=W - 4):
            lines.append(f"  {chunk}")

        lines += [
            "",
            "═" * W,
            "  NEXT STEPS:".center(W),
            "  1. Address High/Critical regulatory issues first".center(W),
            "  2. Implement recommendations within 30 days".center(W),
            "  3. Re-analyze after changes using GreenCompliance AI".center(W),
            "",
            "  ⚠️  DISCLAIMER: This report is for informational purposes only.",
            "  Always consult a licensed environmental professional for legal advice.",
            "═" * W,
            "",
            f"  Powered by GreenCompliance AI  |  greencompliance.ai",
        ]

        content = "\n".join(lines)
        buf = io.BytesIO(content.encode("utf-8"))
        buf.seek(0)
        return send_file(
            buf, as_attachment=True,
            download_name=f"GreenCompliance_Report_{analysis_id}.txt",
            mimetype="text/plain"
        )

    except Exception as e:
        print(f"[/report ERROR] {traceback.format_exc()}")
        return jsonify({"error": "Could not generate report"}), 500


@app.route("/history")
def history():
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, industry, risk_level, compliance_score, source, created_at "
                "FROM analyses ORDER BY id DESC LIMIT 10"
            ).fetchall()
        return jsonify([dict(r) for r in rows]), 200
    except Exception as e:
        print(f"[/history ERROR] {e}")
        return jsonify([]), 200


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "1.0.0"}), 200


# ─────────────────────────────────────────
# Global Error Handlers (prevent crashes)
# ─────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
