// ═══════════════════════════════════════════════════════════════════
// CityGate — Municipal Permit Compliance Platform
// Backend-integrated agent pipeline with HITL checkpoint + Three.js
// ═══════════════════════════════════════════════════════════════════

import { PermitScene3D } from './three-scene.js';

const API = window.location.origin;
let ticketCounter = 0;
let activeSessionId = null;
let activeTicketId = null;
let isProcessing = false;
const activeTickets = {};
let pipelineStages = [];

const PRESETS = {
    en: "Hi, I need a business license for my restaurant called La Cocina Familiar LLC. I'm Maria Rodriguez, located at 4521 Main Street Suite B, San Antonio TX 78205. My phone is (210) 555-0142 and EIN is 12-3456789.",
    es: "Hola, necesito un permiso de negocio para mi restaurante La Cocina Familiar LLC. Soy Maria Rodriguez, en 4521 Main Street Suite B, San Antonio 78205. Teléfono (210) 555-0142.",
    vi: "Xin giấy phép kinh doanh cho cửa hàng Oak Market tại 890 Commerce Blvd, zip 78205. Số điện thoại (210) 555-0199.",
};

const STAGE_COLORS = { yellow: '#FBBF24', blue: '#3B82F6', orange: '#FF6B00', green: '#22C55E' };

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// DOM refs
const queueList = document.getElementById('queue-list');
const queueCountBadge = document.getElementById('queue-count');
const emptyFeedText = document.getElementById('empty-feed-text');
const agentStateLabel = document.getElementById('agent-state-label');
const agentSpinner = document.getElementById('agent-spinner');
const trackerStages = document.getElementById('tracker-stages');
const schemaCode = document.getElementById('schema-code');
const schemaPre = document.getElementById('schema-pre');
const mcpLog = document.getElementById('mcp-log');
const proposedFixMd = document.getElementById('proposed-fix-md');
const langIndicator = document.getElementById('lang-indicator');
const hitlModal = document.getElementById('hitl-modal');
const hitlComparison = document.getElementById('hitl-comparison');
const hitlCompliance = document.getElementById('hitl-compliance');
const hitlTokenInput = document.getElementById('hitl-token-input');
const hitlTokenHint = document.getElementById('hitl-token-hint');
const modalOverlay = document.getElementById('modal-overlay');

let scene3d = null;

// ─── API Helpers ───
async function api(path, opts = {}) {
    const res = await fetch(`${API}${path}`, {
        headers: { 'Content-Type': 'application/json', ...opts.headers },
        ...opts,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'API error');
    }
    return res.json();
}

// ─── Agent Status Tracker ───
async function loadPipelineStages() {
    try {
        const data = await api('/api/pipeline/stages');
        pipelineStages = data.stages || [];
        renderTracker([]);
    } catch { /* backend may not be ready yet */ }
}

function renderTracker(completed, current) {
    if (!trackerStages) return;
    trackerStages.innerHTML = pipelineStages.map(s => {
        let state = 'pending';
        if (completed.includes(s.id)) state = 'completed';
        else if (s.id === current) state = 'active';
        const color = STAGE_COLORS[s.color] || '#888';
        return `<div class="tracker-stage tracker-${state}" style="--stage-color:${color}" title="${s.label}">
            <span class="tracker-dot"></span>
            <span class="tracker-label">${s.label}</span>
        </div>`;
    }).join('');
    if (scene3d && current) scene3d.setStage(current);
}

function setAgentLabel(text, color) {
    if (agentStateLabel) {
        agentStateLabel.textContent = text;
        agentStateLabel.style.color = color || 'var(--text-secondary)';
    }
}

// ─── Queue Management ───
function createQueueCard(id, item) {
    if (emptyFeedText) emptyFeedText.style.display = 'none';
    const card = document.createElement('div');
    card.className = 'queue-card active card-new-entry';
    card.id = `card-${id}`;
    card.innerHTML = `
        <div class="card-header">
            <span class="card-id">${item.id}</span>
            <span class="card-trade">${item.language?.toUpperCase() || 'EN'} · ${item.formType}</span>
        </div>
        <div class="card-text">${item.text.substring(0, 120)}${item.text.length > 120 ? '...' : ''}</div>
        <div class="card-footer">
            <span class="badge badge-blue" id="badge-${id}">${item.status}</span>
        </div>`;
    card.addEventListener('click', () => selectTicket(id));
    queueList.insertBefore(card, queueList.firstChild);
}

function updateBadge(id, status, cls) {
    const badge = document.getElementById(`badge-${id}`);
    if (badge) { badge.textContent = status; badge.className = `badge ${cls}`; }
}

function updateDashboard() {
    const all = Object.values(activeTickets);
    const pending = all.filter(t => t.status !== 'Submitted' && t.status !== 'Rejected');
    if (queueCountBadge) queueCountBadge.textContent = `${pending.length} Pending`;

    const totalEl = document.getElementById('analytics-total-count');
    const resolvedEl = document.getElementById('analytics-resolved-count');
    const pendingEl = document.getElementById('analytics-pending-count');
    if (totalEl) totalEl.textContent = all.length;
    if (resolvedEl) resolvedEl.textContent = all.filter(t => t.status === 'Submitted').length;
    if (pendingEl) pendingEl.textContent = pending.length;

    const tbody = document.getElementById('archives-tbody');
    const archiveBadge = document.getElementById('archive-count-badge');
    if (!tbody) return;

    if (all.length === 0) {
        tbody.innerHTML = '<tr class="empty-archive-row"><td colspan="6" class="text-center">No permits processed yet.</td></tr>';
        if (archiveBadge) archiveBadge.textContent = '0 Records';
        return;
    }

    tbody.innerHTML = [...all].reverse().map(item => {
        const badgeCls = item.status === 'Submitted' ? 'badge-green' : item.status === 'Awaiting Approval' ? 'badge-orange' : 'badge-blue';
        return `<tr>
            <td style="font-weight:700">${item.id}</td>
            <td>${item.formType}</td>
            <td style="font-family:'Share Tech Mono',monospace">${item.zipCode || '—'}</td>
            <td>${item.complianceScore != null ? item.complianceScore + '%' : '—'}</td>
            <td style="font-family:'Share Tech Mono',monospace">${item.commitTime || '—'}</td>
            <td><span class="badge ${badgeCls}">${item.status}</span></td>
        </tr>`;
    }).join('');
    if (archiveBadge) archiveBadge.textContent = `${all.length} Records`;
}

// ─── Pipeline Execution ───
async function runPermitPipeline(text, formType, language) {
    if (isProcessing) return;
    isProcessing = true;

    ticketCounter++;
    const ticketId = `PERMIT #${ticketCounter}`;
    activeTicketId = ticketId;

    activeTickets[ticketId] = {
        id: ticketId, text, formType, language,
        status: 'Processing', zipCode: null, complianceScore: null, commitTime: null,
    };

    createQueueCard(ticketId, activeTickets[ticketId]);
    updateDashboard();
    document.getElementById('modal-overlay').style.display = 'none';

    if (scene3d) scene3d.activate(formType, 'San Antonio');

    agentSpinner.style.display = 'block';
    setAgentLabel('Starting Agent Pipeline...', 'var(--accent-blue)');

    tabPlaceholdersHide();
    schemaPre.style.display = 'block';
    mcpLog.style.display = 'block';
    proposedFixMd.style.display = 'block';
    schemaCode.textContent = '// Agents processing...';
    mcpLog.innerHTML = '';
    proposedFixMd.innerHTML = '<p>Compliance analysis in progress...</p>';

    const stageOrder = ['intake', 'vault', 'parse', 'city_code', 'compliance', 'form_fill', 'hitl'];
    const stageLabels = {
        intake: 'Processing Intake', vault: 'Vaulting PII', parse: 'Parsing Photo',
        city_code: 'Looking Up City Code', compliance: 'Reviewing Legal Terms',
        form_fill: 'Preparing Form', hitl: 'Awaiting Human Approval',
    };

    try {
        for (let i = 0; i < stageOrder.length; i++) {
            const stage = stageOrder[i];
            renderTracker(stageOrder.slice(0, i), stage);
            setAgentLabel(`[${stageLabels[stage]}]`, STAGE_COLORS[i < 3 ? 'yellow' : 'blue']);

            if (i === 0) {
                const session = await api('/api/session', {
                    method: 'POST',
                    body: JSON.stringify({ text, image_source: formType, language }),
                });
                activeSessionId = session.session_id;
                activeTickets[ticketId].sessionId = session.session_id;
                activeTickets[ticketId].token = session.token;

                appendLog(`[Intake] Language: ${session.results?.intake?.language_detected || language}`);
                appendLog(`[PII Vault] ${session.results?.intake?.pii_vaulted || 0} sensitive values vaulted locally`, 'vault');
                schemaCode.textContent = JSON.stringify(session.results?.intake || {}, null, 2);

                if (langIndicator) langIndicator.textContent = (session.results?.intake?.language_detected || language).toUpperCase();
            }

            await sleep(600);
        }

        const session = await api(`/api/session/${activeSessionId}`);
        const intake = session.results?.intake || {};
        const doc = session.results?.document || {};
        const city = session.results?.city_code || {};
        const compliance = session.results?.compliance || {};
        const comparison = session.results?.form_comparison || {};

        activeTickets[ticketId].zipCode = city.zip_code;
        activeTickets[ticketId].complianceScore = compliance.compliance_score;
        if (scene3d) scene3d.setComplianceScore(compliance.compliance_score);

        appendLog(`[Document Parser] Extracted ${doc.field_count || 0} fields from ${doc.form_type}`, 'query');
        appendLog(`[MCP] City code lookup: ${city.city}, ${city.state} — ${city.requirements?.length || 0} requirements`, 'query');
        appendLog(`[Compliance] Score: ${compliance.compliance_score}% — ${compliance.gaps?.length || 0} gaps found`, compliance.compliance_score >= 70 ? 'pass' : 'warn');

        schemaCode.textContent = JSON.stringify({ intake: intake.extracted_fields, document: doc.fields, compliance }, null, 2);

        proposedFixMd.innerHTML = buildComplianceHtml(compliance, city, comparison);

        renderTracker(stageOrder, 'hitl');
        setAgentLabel('[Awaiting Human Approval]', STAGE_COLORS.orange);
        if (scene3d) scene3d.setStage('hitl');
        activeTickets[ticketId].status = 'Awaiting Approval';
        updateBadge(ticketId, 'Awaiting Approval', 'badge-orange');
        updateDashboard();

        showHitlModal(session);

    } catch (err) {
        setAgentLabel('Pipeline Error — check backend', 'var(--accent-red)');
        if (scene3d) scene3d.setStage('error');
        appendLog(`[ERROR] ${err.message}`, 'warn');
        activeTickets[ticketId].status = 'Error';
        updateBadge(ticketId, 'Error', 'badge-red');
    }

    agentSpinner.style.display = 'none';
    isProcessing = false;
}

function appendLog(msg, type = 'info') {
    const line = document.createElement('div');
    const cls = type === 'query' ? 'mcp-query' : type === 'pass' ? 'mcp-pass' : type === 'vault' ? 'mcp-vault' : type === 'warn' ? 'mcp-warn' : 'mcp-info';
    line.innerHTML = `<span class="${cls}">${msg}</span>`;
    mcpLog.appendChild(line);
    mcpLog.scrollTop = mcpLog.scrollHeight;
}

function buildComplianceHtml(compliance, city, comparison) {
    const gaps = (compliance.gaps || []).map(g =>
        `<li><strong>${g.gap_id || g.field_id}</strong>: ${g.description || g.remediation}</li>`
    ).join('');
    const fields = (comparison.comparison || []).map(c =>
        `<tr><td>${c.form_asks}</td><td>${c.agent_filled || '<em>missing</em>'}</td><td>${c.match ? '✓' : '✗'}</td></tr>`
    ).join('');

    return `
        <h4>Compliance Analysis — ${city.city || 'Unknown'}</h4>
        <p>Score: <strong style="color:${compliance.compliance_score >= 70 ? 'var(--accent-green)' : 'var(--accent-orange)'}">${compliance.compliance_score}%</strong></p>
        ${gaps ? `<ul>${gaps}</ul>` : '<p>No compliance gaps detected.</p>'}
        <h4>Form Mapping Preview</h4>
        <table class="mini-table"><thead><tr><th>Form Asks</th><th>Agent Filled</th><th>OK</th></tr></thead><tbody>${fields}</tbody></table>
        <p class="form-hint">Full review required in HITL modal before submission.</p>`;
}

// ─── HITL Modal ───
function showHitlModal(session) {
    const comparison = session.results?.form_comparison || {};
    const compliance = session.results?.compliance || {};

    hitlComparison.innerHTML = `
        <div class="hitl-table-header">
            <span>What the Form Asks</span>
            <span>What the Agent Filled In</span>
        </div>
        ${(comparison.comparison || []).map(c => `
            <div class="hitl-row ${c.match ? 'hitl-match' : 'hitl-miss'}">
                <div class="hitl-form-asks">
                    <strong>${c.form_asks}</strong>
                    ${c.required ? '<span class="req-tag">Required</span>' : ''}
                    ${c.pii ? '<span class="pii-tag">PII</span>' : ''}
                </div>
                <div class="hitl-agent-filled">${c.agent_filled || '<em>Not filled</em>'}</div>
            </div>`).join('')}`;

    hitlCompliance.innerHTML = `
        <div class="compliance-summary">
            Compliance: <strong>${compliance.compliance_score}%</strong> ·
            Fields filled: <strong>${comparison.filled_count}/${comparison.total_fields}</strong> ·
            Ready: <strong>${comparison.ready_for_submission ? 'Yes' : 'Review needed'}</strong>
        </div>`;

    hitlTokenHint.textContent = `Security code: ${session.token}`;
    hitlTokenInput.value = '';
    hitlModal.style.display = 'flex';
}

async function handleHitlApprove() {
    const token = hitlTokenInput.value.trim();
    const ticket = activeTickets[activeTicketId];
    if (!ticket?.sessionId) return;

    try {
        const result = await api(`/api/session/${ticket.sessionId}/approve`, {
            method: 'POST',
            body: JSON.stringify({ token }),
        });

        hitlModal.style.display = 'none';
        ticket.status = 'Submitted';
        ticket.commitTime = new Date().toLocaleTimeString();
        updateBadge(activeTicketId, 'Submitted', 'badge-green');
        renderTracker(['intake','vault','parse','city_code','compliance','form_fill','hitl','complete'], 'complete');
        setAgentLabel('[Complete] Permit Filed Successfully', STAGE_COLORS.green);
        if (scene3d) scene3d.setStage('complete');

        appendLog(`[HITL] Approved & filed — Submission ID: ${result.results?.submission?.submission_id}`, 'pass');
        appendLog(`[Permit Status] ${result.results?.permit_status?.stage || 'Under Review'}`, 'query');

        const card = document.getElementById(`card-${activeTicketId}`);
        if (card) { card.classList.add('card-success-exit'); await sleep(600); card.remove(); }

        updateDashboard();
        loadAdvocacyData();
    } catch (err) {
        hitlTokenInput.style.borderColor = 'var(--accent-red)';
        alert(`Approval denied: ${err.message}`);
    }
}

function handleHitlReject() {
    hitlModal.style.display = 'none';
    if (scene3d) scene3d.setStage('error');
    if (activeTickets[activeTicketId]) {
        activeTickets[activeTicketId].status = 'Rejected';
        activeTickets[activeTicketId].commitTime = new Date().toLocaleTimeString();
        updateBadge(activeTicketId, 'Rejected', 'badge-red');
        setAgentLabel('Submission Rejected by User', 'var(--accent-red)');
        updateDashboard();
    }
}

// ─── Advocacy View ───
async function loadAdvocacyData() {
    try {
        const [licenses, alerts, vault] = await Promise.all([
            api('/api/advocacy/licenses'),
            api('/api/alerts'),
            api('/api/vault/stats'),
        ]);

        document.getElementById('adv-licenses-count').textContent = licenses.total || 0;
        document.getElementById('adv-renewal-count').textContent = licenses.renewal_due_count || 0;
        document.getElementById('adv-alerts-count').textContent = (alerts.alerts || []).length;
        document.getElementById('adv-vault-count').textContent = vault.total_entries || 0;

        const licenseList = document.getElementById('license-list');
        if (licenseList) {
            licenseList.innerHTML = (licenses.licenses || []).map(l => `
                <div class="license-item ${l.status === 'renewal_due' ? 'renewal-due' : ''}">
                    <strong>${l.business_name}</strong>
                    <span>${l.license_type}</span>
                    <span class="license-expiry">${l.days_until_expiry} days left · ${l.expiry_date}</span>
                </div>`).join('') || '<p class="form-hint">No licenses tracked yet.</p>';
        }

        const alertsList = document.getElementById('alerts-list');
        if (alertsList) {
            alertsList.innerHTML = (alerts.alerts || []).map(a => `
                <div class="alert-item">
                    <strong>${a.push_header}</strong>
                    <p>${a.push_body_preview}</p>
                    <span class="alert-meta">${a.type} · PII check: ${a.pii_leak_check}</span>
                </div>`).join('') || '<p class="form-hint">No alerts yet. Run renewal check.</p>';
        }
    } catch { /* backend not ready */ }
}

// ─── Tab placeholders ───
const tabPlaceholders = {
    'extracted-schema': document.getElementById('empty-tab-1'),
    'mcp-stream': document.getElementById('empty-tab-2'),
    'engineering-fix': document.getElementById('empty-tab-3'),
};

function tabPlaceholdersHide() {
    Object.values(tabPlaceholders).forEach(el => { if (el) el.style.display = 'none'; });
}

function selectTicket(id) {
    activeTicketId = id;
    document.querySelectorAll('.queue-card').forEach(c => c.classList.remove('active'));
    const card = document.getElementById(`card-${id}`);
    if (card) card.classList.add('active');
}

// ─── Event Bindings ───
document.getElementById('btn-transmit')?.addEventListener('click', () => {
    const text = document.getElementById('conflict-description').value.trim();
    if (!text) { alert('Please describe your permit request or load a preset.'); return; }
    const formType = document.getElementById('form-type-select').value;
    const language = document.getElementById('language-select').value;
    runPermitPipeline(text, formType, language);
});

document.getElementById('btn-preset-en')?.addEventListener('click', () => {
    document.getElementById('conflict-description').value = PRESETS.en;
    document.getElementById('language-select').value = 'en';
});
document.getElementById('btn-preset-es')?.addEventListener('click', () => {
    document.getElementById('conflict-description').value = PRESETS.es;
    document.getElementById('language-select').value = 'es';
});
document.getElementById('btn-preset-vi')?.addEventListener('click', () => {
    document.getElementById('conflict-description').value = PRESETS.vi;
    document.getElementById('language-select').value = 'vi';
});

document.getElementById('hitl-approve')?.addEventListener('click', handleHitlApprove);
document.getElementById('hitl-reject')?.addEventListener('click', handleHitlReject);

document.getElementById('btn-new-rfi')?.addEventListener('click', () => { modalOverlay.style.display = 'flex'; });
document.getElementById('modal-close')?.addEventListener('click', () => { modalOverlay.style.display = 'none'; });
modalOverlay?.addEventListener('click', (e) => { if (e.target === modalOverlay) modalOverlay.style.display = 'none'; });

document.getElementById('btn-check-renewals')?.addEventListener('click', async () => {
    await api('/api/advocacy/check-renewals', { method: 'POST' });
    loadAdvocacyData();
});

// Tab switching
document.querySelectorAll('.tab-btn').forEach(tab => {
    tab.addEventListener('click', () => {
        const target = tab.getAttribute('data-tab');
        document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        document.getElementById(target)?.classList.add('active');
    });
});

// Navigation
const views = {
    queue: document.getElementById('view-queue'),
    analysis: document.getElementById('view-analysis'),
    advocacy: document.getElementById('view-advocacy'),
    archives: document.getElementById('view-archives'),
};

function switchView(name) {
    Object.values(views).forEach(v => v?.classList.remove('active-view'));
    views[name]?.classList.add('active-view');
    document.querySelectorAll('.nav-link, .sidebar-link').forEach(l => l.classList.remove('active'));
    document.getElementById(`nav-top-${name}`)?.classList.add('active');
    document.getElementById(`nav-${name}`)?.classList.add('active');
    if (name === 'analysis' || name === 'archives') updateDashboard();
    if (name === 'advocacy') loadAdvocacyData();
}

['queue', 'analysis', 'advocacy', 'archives'].forEach(name => {
    document.getElementById(`nav-top-${name}`)?.addEventListener('click', (e) => { e.preventDefault(); switchView(name); });
    document.getElementById(`nav-${name}`)?.addEventListener('click', (e) => { e.preventDefault(); switchView(name); });
});

// Accessibility: larger text toggle via keyboard
document.addEventListener('keydown', (e) => {
    if (e.altKey && e.key === 'l') {
        document.body.classList.toggle('large-text');
    }
});

// Init
window.addEventListener('DOMContentLoaded', () => {
    scene3d = new PermitScene3D('cad-container');
    loadPipelineStages();
    loadAdvocacyData();
    updateDashboard();
    setTimeout(() => scene3d?.resize(), 100);
});
