/* ═══════════════════════════════════════════════════
   GreenCompliance AI — Frontend Logic  v3
   ═══════════════════════════════════════════════════ */

const API = window.location.origin;
let currentId = null;
let scoreChart = null;
let loadTimer = null;

/* ─── All 8 industry examples ─────────────────────── */
const EXAMPLES = {
    Restaurant: {
        text: 'We run a busy restaurant that deep-fries food daily in three large commercial fryers. Used cooking oil is poured down the kitchen sink drain — we have no oil collection service. All takeaway orders use non-recyclable styrofoam containers and plastic bags. We have five large refrigeration units running 24/7 and do not have a recycling or waste management program in place.'
    },
    Construction: {
        text: 'We carry out commercial demolition and construction projects. Concrete cutting and drilling produces large amounts of airborne dust on site with no suppression systems in place. Stormwater runoff from our site flows directly into a nearby drainage channel. Some older buildings we are demolishing may contain asbestos and lead paint. Construction debris including concrete, wood, and metal is mixed into general waste skips.'
    },
    Manufacturing: {
        text: 'We operate a metal fabrication plant with three large furnaces and a spray-painting booth. Smoke and particulate matter are discharged from chimney stacks without filtration systems. Industrial solvents are used for degreasing parts and the waste liquid is tipped into floor drains. Metal shavings, cutting fluid waste, and chemical coolants all go into general waste bins. We have no wastewater treatment before discharge.'
    },
    Agriculture: {
        text: 'We run a 200-acre farm that grows vegetables and rears chickens. We spray pesticides and herbicides weekly across all crop areas including near the riverbank at the farm boundary. Animal manure from chicken houses is stored in an open-air pit adjacent to a drainage stream. Excess fertilizer runoff from fields flows into the local waterway. We burn crop stubble after harvest to clear fields.'
    },
    Healthcare: {
        text: 'We operate a private healthcare clinic with 20 staff and 80 daily patients. Used syringes, sharps, and blood-contaminated materials are sometimes disposed of in regular waste bins due to sharps container shortages. Expired medications, including controlled substances, are flushed down clinic toilets. Mercury thermometers are disposed of in normal trash. Biohazardous waste bags are occasionally mixed with general clinical waste.'
    },
    Retail: {
        text: 'We operate a chain of 5 retail shops. We provide free single-use plastic bags to all customers and use non-recyclable packaging for all products. Our refrigerated display units are old models with known refrigerant leaks and poor energy ratings. Store lighting uses old fluorescent tubes and we have no energy efficiency measures in place. Cardboard and plastic packaging waste is sent to landfill rather than recycled.'
    },
    Technology: {
        text: 'We run a data center and IT services company. Old servers, PCs, monitors, and electronic equipment are disposed of in general commercial waste without using certified e-waste recyclers. Server cooling systems use refrigerants that may be subject to environmental controls. The data center runs at high power usage effectiveness (PUE) above 2.0 and we have no renewable energy sourcing. Batteries and UPS systems are disposed of in general waste.'
    },
    Transportation: {
        text: 'We operate a fleet of 40 diesel delivery trucks serving the city region. Vehicles are more than 10 years old and have never had formal emission testing done. Trucks frequently idle for 30+ minutes during loading and unloading. Engine oil and hydraulic fluid changes are performed in-house and waste oils are stored in open drums on site. Truck washing water containing detergent and oil runoff drains directly to the road gutter.'
    }
};

/* ─── DOM refs ─────────────────────────────────────── */
const analyzeBtn = document.getElementById('analyzeBtn');
const industryEl = document.getElementById('industry');
const descEl = document.getElementById('description');
const loadingEl = document.getElementById('loadingSection');
const resultsEl = document.getElementById('resultsSection');
const charCountEl = document.getElementById('charCount');

/* ─── Industry pill buttons ────────────────────────── */
document.querySelectorAll('.industry-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.industry-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        industryEl.value = btn.dataset.val;
        // Sync example active state
        document.querySelectorAll('.example-btn').forEach(b => {
            b.classList.toggle('active-ex', b.dataset.ex === btn.dataset.val);
        });
        setStep(2);
        descEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => descEl.focus(), 400);
    });
});

/* ─── Example buttons (all 8) ──────────────────────── */
document.querySelectorAll('.example-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const ind = btn.dataset.ex;
        const ex = EXAMPLES[ind];
        if (!ex) return;

        // Update industry selection
        industryEl.value = ind;
        document.querySelectorAll('.industry-btn').forEach(b =>
            b.classList.toggle('active', b.dataset.val === ind)
        );
        document.querySelectorAll('.example-btn').forEach(b =>
            b.classList.toggle('active-ex', b.dataset.ex === ind)
        );

        // Fill description with fast typewriter
        descEl.value = '';
        descEl.focus();
        let i = 0;
        const tick = () => {
            if (i < ex.text.length) {
                descEl.value += ex.text[i++];
                updateChar();
                setTimeout(tick, 4);
            } else {
                setStep(2);
                toast(`💡 ${ind} example loaded — click Analyze to run!`, 'info');
            }
        };
        tick();
    });
});

/* ─── Char counter ─────────────────────────────────── */
descEl.addEventListener('input', updateChar);
function updateChar() {
    const n = descEl.value.length;
    charCountEl.textContent = `${n} / 500`;
    charCountEl.style.color = n > 490 ? 'var(--red)' : n > 400 ? 'var(--yellow)' : '';
    if (n > 10) setStep(2);
}

/* ─── Step indicator ────────────────────────────────── */
function setStep(n) {
    [1, 2, 3].forEach(i => {
        const el = document.getElementById(`step${i}`);
        if (!el) return;
        el.classList.remove('active', 'done');
        if (i < n) el.classList.add('done');
        if (i === n) el.classList.add('active');
    });
}

/* ─── Analyze ───────────────────────────────────────── */
analyzeBtn.addEventListener('click', async () => {
    const industry = industryEl.value.trim();
    const description = descEl.value.trim();

    if (!description || description.length < 10) {
        toast('⚠️ Please describe your business (at least 10 characters).', 'warn');
        descEl.focus();
        return;
    }

    setLoading(true);
    setStep(3);
    resultsEl.classList.add('hidden');

    try {
        const res = await fetch(`${API}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ industry, description }),
        });

        let data;
        try { data = await res.json(); }
        catch { throw new Error(`Could not read response (${res.status})`); }
        if (!res.ok) throw new Error(data.error || `Server error ${res.status}`);

        currentId = data.id;
        render(data);

    } catch (err) {
        toast(`❌ ${err.message}`, 'error');
        setStep(2);
        console.error('[Analyze]', err);
    } finally {
        setLoading(false);
    }
});

/* ─── Render results ────────────────────────────────── */
function render(data) {
    const level = (data.risk_level || 'low').toLowerCase();
    const bCls = { high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }[level] || 'badge-low';
    const icons = { high: '🔴', medium: '🟡', low: '🟢' };
    const icon = icons[level] || '🟢';
    const label = data.risk_level || 'Low';

    // Badges
    ['riskBadge', 'riskBadge2'].forEach(id => {
        const el = document.getElementById(id);
        if (el) { el.className = `badge ${bCls}`; el.innerHTML = `${icon} ${label}`; }
    });

    // Source chip
    const chip = document.getElementById('sourceChip');
    if (chip) {
        chip.className = data.source === 'gemini-ai' ? 'src-chip src-ai' : 'src-chip src-rule';
        chip.textContent = data.source === 'gemini-ai' ? '✨ Gemini AI' : '⚙️ Rule-Based';
    }

    // Score
    const score = clamp(parseInt(data.compliance_score) || 0, 0, 100);
    animNum('scoreValue', 0, score, 1100);
    renderChart(score, level);

    // Progress bar
    const pBar = document.getElementById('riskProgressBar');
    if (pBar) {
        const pct = { high: 86, medium: 54, low: 22 }[level] || 22;
        pBar.style.width = '0%';
        pBar.className = `progress-bar progress-${level}`;
        requestAnimationFrame(() => setTimeout(() => { pBar.style.width = pct + '%'; }, 80));
    }

    // Counts
    animNum('issueCount', 0, (data.issues || []).length, 700);
    animNum('recCount', 0, (data.recommendations || []).length, 700);

    // Lists
    renderList('issuesList', data.issues || [], 'issue');
    renderList('recList', data.recommendations || [], 'rec');
    renderRegCards(data.regulatory_areas || []);

    // AI Insight typewriter
    const insEl = document.getElementById('aiInsight');
    if (insEl) {
        insEl.textContent = '';
        insEl.classList.add('cursor');
        typewriter(insEl, data.ai_insight || 'No AI insight available.', 15, () =>
            insEl.classList.remove('cursor')
        );
    }

    // Show results with fade
    resultsEl.classList.remove('hidden');
    resultsEl.style.cssText = 'opacity:0;transform:translateY(14px)';
    requestAnimationFrame(() => {
        resultsEl.style.cssText = 'opacity:1;transform:translateY(0);transition:opacity .5s ease,transform .5s ease';
    });
    setTimeout(() => resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
}

/* ─── helpers ────────────────────────────────────────── */
function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

function animNum(id, from, to, ms) {
    const el = document.getElementById(id);
    if (!el) return;
    const t0 = performance.now();
    const step = now => {
        const p = Math.min((now - t0) / ms, 1);
        el.textContent = Math.round(from + (1 - Math.pow(1 - p, 3)) * (to - from));
        if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
}

function renderChart(score, level) {
    const ctx = document.getElementById('scoreChart');
    if (!ctx) return;
    const fg = { low: '#34d399', medium: '#fbbf24', high: '#f87171' }[level] || '#34d399';
    const bg = { low: 'rgba(52,211,153,.1)', medium: 'rgba(251,191,36,.1)', high: 'rgba(248,113,113,.1)' }[level];
    if (scoreChart) { scoreChart.destroy(); scoreChart = null; }
    scoreChart = new Chart(ctx, {
        type: 'doughnut',
        data: { datasets: [{ data: [score, 100 - score], backgroundColor: [fg, bg], borderWidth: 0, borderRadius: 8 }] },
        options: {
            cutout: '80%', responsive: false,
            animation: { duration: 1100, easing: 'easeInOutQuart' },
            plugins: { legend: { display: false }, tooltip: { enabled: false } },
        }
    });
}

function renderList(elId, items, type) {
    const el = document.getElementById(elId);
    if (!el) return;
    if (!items.length) {
        el.innerHTML = `<p class="text-gray-500 text-xs italic py-2">No ${type === 'issue' ? 'issues' : 'recommendations'} identified.</p>`;
        return;
    }
    const cls = type === 'issue' ? 'list-item-issue' : 'list-item-rec';
    const icon = type === 'issue' ? '⚠️' : '✅';
    el.innerHTML = items.map((t, i) =>
        `<div class="list-item ${cls} anim-slide" style="animation-delay:${i * .06}s">
       <span style="flex-shrink:0;margin-top:2px">${icon}</span><span>${esc(t)}</span>
     </div>`
    ).join('');
}

function renderRegCards(areas) {
    const el = document.getElementById('regCards');
    if (!el) return;
    if (!areas.length) {
        el.innerHTML = '<p class="text-gray-500 text-xs italic py-2">No regulatory areas identified.</p>';
        return;
    }
    el.innerHTML = areas.map((a, i) => {
        const isObj = typeof a === 'object' && a !== null;
        const sev = (isObj ? a.severity : 'Medium') || 'Medium';
        const title = isObj ? (a.title || 'N/A') : String(a);
        const body = isObj ? (a.body || '') : '';
        const sevIco = { Critical: '🔴', High: '🟠', Medium: '🟡', Low: '🟢' }[sev] || '🟡';
        return `
      <div class="reg-card anim-fade" style="animation-delay:${i * .07}s">
        <div class="flex items-start gap-2 justify-between flex-wrap">
          <span class="font-semibold text-gray-100 text-sm">${esc(title)}</span>
          <span class="sev-${sev.toLowerCase()} text-xs font-bold uppercase tracking-wide whitespace-nowrap">${sevIco} ${esc(sev)}</span>
        </div>
        ${body ? `<p class="text-gray-400 text-xs mt-1.5">📋 ${esc(body)}</p>` : ''}
      </div>`;
    }).join('');
}

function typewriter(el, text, speed, cb) {
    let i = 0;
    const t = () => { el.textContent += text[i++]; i < text.length ? setTimeout(t, speed) : cb && cb(); };
    t();
}

/* ─── Loading state ─────────────────────────────────── */
function setLoading(on) {
    analyzeBtn.disabled = on;
    if (on) {
        analyzeBtn.innerHTML = `
      <svg class="w-4 h-4 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
      </svg> Analyzing…`;
        loadingEl.classList.remove('hidden');
        // Animate loading steps
        const steps = document.querySelectorAll('.loading-step');
        steps.forEach(s => s.classList.remove('active', 'done'));
        let s = 0;
        loadTimer = setInterval(() => {
            if (s > 0 && steps[s - 1]) { steps[s - 1].classList.remove('active'); steps[s - 1].classList.add('done'); }
            if (steps[s]) steps[s].classList.add('active');
            s++;
            if (s >= steps.length) clearInterval(loadTimer);
        }, 1100);
    } else {
        clearInterval(loadTimer);
        analyzeBtn.innerHTML = `
      <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
      </svg> Analyze Compliance Risks
      <span class="btn-badge">Free · Instant</span>`;
        loadingEl.classList.add('hidden');
    }
}

/* ─── Download report ───────────────────────────────── */
document.getElementById('downloadBtn').addEventListener('click', async () => {
    if (!currentId) { toast('⚠️ Run an analysis first, then download the report.', 'warn'); return; }
    try {
        const res = await fetch(`${API}/report/${currentId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = Object.assign(document.createElement('a'), {
            href: url, download: `GreenCompliance_Report_${currentId}.txt`
        });
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        URL.revokeObjectURL(url);
        toast('✅ Report downloaded!', 'success');
    } catch (e) { toast(`❌ Download failed: ${e.message}`, 'error'); }
});

/* ─── Scroll to input ───────────────────────────────── */
function scrollToInput() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    setTimeout(() => descEl.focus(), 600);
}

/* ─── Toast ─────────────────────────────────────────── */
function toast(msg, type = 'info') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `t-${type}`;
    el.classList.add('show');
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove('show'), 4200);
}

/* ─── XSS escape ─────────────────────────────────────── */
function esc(s) {
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ─── Init ───────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('toast').className = '';
    // Pre-select Restaurant example button
    const first = document.querySelector('.example-btn[data-ex="Restaurant"]');
    if (first) first.classList.add('active-ex');
});
