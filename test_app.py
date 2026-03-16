"""
GreenCompliance AI — Regression Test Suite
Run with: python -m pytest test_app.py -v
"""

import json
import pytest
import sys
import os

# Make sure app is importable from the project root
sys.path.insert(0, os.path.dirname(__file__))

from app import app, rule_based_analysis, REGULATIONS


# ─────────────────────────────────────────
# Test client fixture
# ─────────────────────────────────────────
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ═══════════════════════════════════════════
# 1. Health & routing
# ═══════════════════════════════════════════

def test_health_endpoint(client):
    """GET /health should return 200 with ok status."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"


def test_index_page_loads(client):
    """GET / should return 200 and contain page content."""
    res = client.get("/")
    assert res.status_code == 200
    assert b"GreenCompliance" in res.data


def test_404_returns_json(client):
    """Non-existent routes should return JSON 404."""
    res = client.get("/nonexistent-route")
    assert res.status_code == 404
    data = res.get_json()
    assert "error" in data


def test_405_on_wrong_method(client):
    """GET on /analyze should return 405."""
    res = client.get("/analyze")
    assert res.status_code == 405
    data = res.get_json()
    assert "error" in data


# ═══════════════════════════════════════════
# 2. /analyze — valid inputs
# ═══════════════════════════════════════════

def test_analyze_restaurant(client):
    """Valid Restaurant analysis returns correct structure."""
    res = client.post(
        "/analyze",
        json={
            "industry": "Restaurant",
            "description": "We fry food daily and dispose of cooking oil down the drain. "
                           "We use styrofoam takeaway containers."
        }
    )
    assert res.status_code == 200
    data = res.get_json()
    assert "risk_level" in data
    assert data["risk_level"] in ("Low", "Medium", "High")
    assert "compliance_score" in data
    assert 0 <= data["compliance_score"] <= 100
    assert isinstance(data["issues"], list)
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["regulatory_areas"], list)
    assert "ai_insight" in data
    assert "source" in data


def test_analyze_construction(client):
    """Valid Construction analysis returns correct structure."""
    res = client.post(
        "/analyze",
        json={
            "industry": "Construction",
            "description": "We conduct demolition work producing significant dust and debris. "
                           "Stormwater runoff reaches a nearby river."
        }
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["risk_level"] in ("Low", "Medium", "High")
    assert len(data["issues"]) >= 1


def test_analyze_all_industries(client):
    """All 8 industry options should return 200 without server crash."""
    industries = [
        "Restaurant", "Construction", "Manufacturing",
        "Agriculture", "Healthcare", "Retail", "Technology", "Transportation"
    ]
    for ind in industries:
        res = client.post(
            "/analyze",
            json={"industry": ind, "description": f"We operate a {ind} business with standard processes."}
        )
        assert res.status_code == 200, f"Failed for industry: {ind}"
        data = res.get_json()
        assert "risk_level" in data, f"Missing risk_level for {ind}"
        assert "compliance_score" in data


def test_analyze_returns_industry_and_description(client):
    """Response should echo back industry and description."""
    res = client.post(
        "/analyze",
        json={"industry": "Retail", "description": "We sell plastic bags in large quantities to customers."}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data.get("industry") == "Retail"
    assert "description" in data


# ═══════════════════════════════════════════
# 3. /analyze — invalid inputs (no crash)
# ═══════════════════════════════════════════

def test_analyze_empty_body(client):
    """Empty POST body should return 400, not 500."""
    res = client.post("/analyze", data="", content_type="application/json")
    assert res.status_code == 400
    data = res.get_json()
    assert "error" in data


def test_analyze_missing_description(client):
    """Missing description field should return 400."""
    res = client.post("/analyze", json={"industry": "Restaurant"})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_analyze_too_short_description(client):
    """Description shorter than 10 chars should return 400."""
    res = client.post("/analyze", json={"industry": "Retail", "description": "Hi"})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_analyze_missing_industry(client):
    """Missing industry field should return 400."""
    res = client.post("/analyze", json={"description": "We operate a large factory with chemical waste"})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_analyze_non_json_content_type(client):
    """Sending form data instead of JSON should return 400 gracefully."""
    res = client.post("/analyze", data={"industry": "Retail", "description": "Test store operations daily"})
    assert res.status_code in (400, 415)


def test_analyze_extremely_long_description(client):
    """Very long description should not crash the server."""
    long_desc = "We process industrial chemicals and manage waste streams. " * 30
    res = client.post("/analyze", json={"industry": "Manufacturing", "description": long_desc})
    # Should succeed or return a well-formed error, but NOT 500
    assert res.status_code in (200, 400)
    data = res.get_json()
    assert data is not None


# ═══════════════════════════════════════════
# 4. /history endpoint
# ═══════════════════════════════════════════

def test_history_returns_list(client):
    """GET /history should return a JSON list."""
    res = client.get("/history")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)


def test_history_after_analysis(client):
    """History should have at least one entry after an analysis."""
    client.post("/analyze", json={
        "industry": "Agriculture",
        "description": "We spray pesticides across our 200-acre farm weekly for crop protection."
    })
    res = client.get("/history")
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "industry" in data[0]
    assert "risk_level" in data[0]
    assert "compliance_score" in data[0]


# ═══════════════════════════════════════════
# 5. /report endpoint
# ═══════════════════════════════════════════

def test_report_invalid_id(client):
    """Non-existent report ID should return 404."""
    res = client.get("/report/999999")
    assert res.status_code == 404
    data = res.get_json()
    assert "error" in data


def test_report_download_after_analysis(client):
    """Should be able to download report after a successful analysis."""
    analyze_res = client.post("/analyze", json={
        "industry": "Healthcare",
        "description": "We dispose of pharmaceutical waste and medical sharps without proper segregation."
    })
    assert analyze_res.status_code == 200
    analysis_id = analyze_res.get_json().get("id")

    if analysis_id:  # Only test if DB saved successfully
        report_res = client.get(f"/report/{analysis_id}")
        assert report_res.status_code == 200
        assert b"GREENCOMPLIANCE" in report_res.data


# ═══════════════════════════════════════════
# 6. Rule-based engine unit tests
# ═══════════════════════════════════════════

def test_rule_engine_restaurant_oil():
    """Rule engine detects oil disposal issue for Restaurant."""
    result = rule_based_analysis(
        "Restaurant",
        "We pour used cooking oil down the drain every day"
    )
    assert result["risk_level"] in ("Low", "Medium", "High")
    assert 0 <= result["compliance_score"] <= 100
    assert len(result["issues"]) >= 1
    assert len(result["recommendations"]) >= 1
    assert len(result["regulatory_areas"]) >= 1
    assert result["source"] == "rule-based"
    assert "Restaurant" in result["ai_insight"] or len(result["ai_insight"]) > 0


def test_rule_engine_construction_dust():
    """Rule engine detects dust/particulate issue for Construction."""
    result = rule_based_analysis(
        "Construction",
        "We generate large amounts of dust from concrete cutting and demolition"
    )
    assert result["risk_level"] in ("Low", "Medium", "High")
    assert len(result["issues"]) >= 1


def test_rule_engine_unknown_keyword_fallback():
    """Rule engine falls back to all industry rules when no keyword matches."""
    result = rule_based_analysis("Restaurant", "We serve food to customers daily")
    assert isinstance(result["issues"], list)
    assert isinstance(result["recommendations"], list)
    # Should still return results from fallback
    assert len(result["issues"]) >= 1


def test_rule_engine_score_range():
    """Compliance score is always between 10 and 100."""
    for ind in ["Restaurant", "Construction", "Manufacturing", "Agriculture"]:
        result = rule_based_analysis(ind, f"We operate a standard {ind} business")
        assert 10 <= result["compliance_score"] <= 100, \
            f"Score out of range for {ind}: {result['compliance_score']}"


def test_rule_engine_risk_levels():
    """Risk level is always one of Low/Medium/High."""
    result = rule_based_analysis(
        "Manufacturing",
        "We release emissions from our chimney and use hazardous chemicals"
    )
    assert result["risk_level"] in ("Low", "Medium", "High")


# ═══════════════════════════════════════════
# 7. Regulations data integrity
# ═══════════════════════════════════════════

def test_regulations_loaded():
    """regulations.json must be loaded and non-empty."""
    assert isinstance(REGULATIONS, list)
    assert len(REGULATIONS) > 0


def test_regulations_schema():
    """Each regulation must have required fields."""
    required = {"industry", "keywords", "issue", "recommendation", "riskWeight", "regulation_title", "regulatory_body"}
    for reg in REGULATIONS:
        missing = required - set(reg.keys())
        assert not missing, f"Regulation {reg.get('id','?')} missing fields: {missing}"


def test_regulations_risk_weights():
    """All riskWeight values must be integers between 1 and 5."""
    for reg in REGULATIONS:
        w = reg.get("riskWeight", 0)
        assert isinstance(w, int) and 1 <= w <= 5, \
            f"Invalid riskWeight {w} for regulation {reg.get('id','?')}"


if __name__ == "__main__":
    # Run directly with: python test_app.py
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v", "--tb=short"], check=False)
