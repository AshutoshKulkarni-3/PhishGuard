/**
 * PhishGuard — Minimal Client Application Script
 * Communicates directly with Spring Boot REST API
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const scanForm = document.getElementById('scanForm');
    const urlInput = document.getElementById('urlInput');
    const scanButton = document.getElementById('scanButton');
    const scanBtnText = document.getElementById('scanBtnText');
    const alertBox = document.getElementById('alertBox');
    const refreshBtn = document.getElementById('refreshBtn');

    // Result Card Elements
    const resultCard = document.getElementById('resultCard');
    const verdictBadge = document.getElementById('verdictBadge');
    const resultTitle = document.getElementById('resultTitle');
    const confidenceValue = document.getElementById('confidenceValue');
    const resultUrl = document.getElementById('resultUrl');
    const indLength = document.getElementById('indLength');
    const indIp = document.getElementById('indIp');
    const indHttps = document.getElementById('indHttps');
    const indSubdomains = document.getElementById('indSubdomains');

    // Badges & Stats
    const backendBadge = document.getElementById('backendBadge');
    const mlBadge = document.getElementById('mlBadge');
    const statTotal = document.getElementById('statTotal');
    const statPhishing = document.getElementById('statPhishing');
    const statLegitimate = document.getElementById('statLegitimate');
    const historyBody = document.getElementById('historyBody');

    // ── 1. Check System Status ───────────────────────────────────────────────
    async function checkStatus() {
        try {
            const res = await fetch('/api/scans/status');
            if (!res.ok) throw new Error('Status check failed');
            const data = await res.json();

            backendBadge.className = 'badge badge-success';
            backendBadge.textContent = 'Backend: Online';

            if (data.mlService === 'UP') {
                mlBadge.className = 'badge badge-success';
                mlBadge.textContent = 'ML Service: Online';
            } else {
                mlBadge.className = 'badge badge-danger';
                mlBadge.textContent = 'ML Service: Offline';
            }
        } catch (err) {
            backendBadge.className = 'badge badge-danger';
            backendBadge.textContent = 'Backend: Offline';
            mlBadge.className = 'badge badge-neutral';
            mlBadge.textContent = 'ML Service: Unknown';
        }
    }

    // ── 2. Load Dashboard Statistics ─────────────────────────────────────────
    async function loadStats() {
        try {
            const res = await fetch('/api/scans/dashboard');
            if (res.ok) {
                const stats = await res.json();
                statTotal.textContent = stats.totalScans ?? 0;
                statPhishing.textContent = stats.phishingScans ?? 0;
                statLegitimate.textContent = stats.legitimateScans ?? 0;
            }
        } catch (err) {
            console.warn('Could not load dashboard stats:', err);
        }
    }

    // ── 3. Load Scan History Table ───────────────────────────────────────────
    async function loadHistory() {
        try {
            const res = await fetch('/api/scans');
            if (!res.ok) throw new Error('Failed to load history');
            const scans = await res.json();

            if (!scans || scans.length === 0) {
                historyBody.innerHTML = `
                    <tr>
                        <td colspan="5" class="text-center text-muted">No scan history recorded yet.</td>
                    </tr>
                `;
                return;
            }

            historyBody.innerHTML = scans.map(s => {
                const isPhish = s.isPhishing;
                const badgeClass = isPhish ? 'badge-danger' : 'badge-success';
                const label = isPhish ? 'PHISHING' : 'SAFE';
                const confPercent = s.confidence ? (s.confidence * 100).toFixed(1) + '%' : 'N/A';
                const dateStr = s.scannedAt ? new Date(s.scannedAt).toLocaleString() : '-';

                return `
                    <tr>
                        <td><strong>#${s.scanId}</strong></td>
                        <td class="table-url" title="${escapeHtml(s.url)}">${escapeHtml(s.url)}</td>
                        <td><span class="badge ${badgeClass}">${label}</span></td>
                        <td>${confPercent}</td>
                        <td class="text-muted">${dateStr}</td>
                    </tr>
                `;
            }).join('');
        } catch (err) {
            historyBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted">Could not load scan history from backend.</td>
                </tr>
            `;
        }
    }

    // ── 4. Form Submission (Scan URL) ────────────────────────────────────────
    scanForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        hideAlert();
        setLoading(true);

        try {
            const res = await fetch('/api/scans', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const data = await res.json();

            if (!res.ok) {
                const errorMsg = data.message || 'Scan failed. Ensure the ML service is running.';
                showAlert(errorMsg, 'danger');
                return;
            }

            displayResult(data);
            loadStats();
            loadHistory();
        } catch (err) {
            showAlert('Network error: Unable to communicate with Spring Boot backend.', 'danger');
        } finally {
            setLoading(false);
        }
    });

    // ── 5. Render Scan Result Card ───────────────────────────────────────────
    function displayResult(result) {
        resultCard.classList.remove('hidden');

        const isPhish = result.isPhishing;
        resultCard.className = 'card result-card ' + (isPhish ? 'verdict-phishing' : 'verdict-safe');

        verdictBadge.className = 'verdict-badge ' + (isPhish ? 'badge-phishing' : 'badge-safe');
        verdictBadge.textContent = isPhish ? 'PHISHING DETECTED' : 'LEGITIMATE URL';

        resultTitle.textContent = isPhish ? 'Security Threat Flagged' : 'URL Verified Safe';

        const conf = result.confidence ? (result.confidence * 100).toFixed(1) + '%' : '100%';
        confidenceValue.textContent = conf;

        resultUrl.textContent = result.url;

        // Populate indicators if present
        const indicators = result.indicators || {};
        indLength.textContent = indicators.url_length ?? result.url.length;
        const hasIp = indicators.has_ip !== undefined ? indicators.has_ip : (indicators.has_ip_hostname ?? false);
        indIp.textContent = hasIp ? 'Yes (Suspicious)' : 'No';
        const isHttps = indicators.is_https !== undefined ? indicators.is_https : result.url.toLowerCase().startsWith('https://');
        indHttps.textContent = isHttps ? 'Yes' : 'No';
        indSubdomains.textContent = indicators.subdomain_count ?? indicators.n_subdomains ?? 0;

        resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // ── 6. Sample URL Buttons ────────────────────────────────────────────────
    document.querySelectorAll('.sample-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const sampleUrl = btn.getAttribute('data-url');
            if (sampleUrl) {
                urlInput.value = sampleUrl;
                urlInput.focus();
            }
        });
    });

    // ── 7. Refresh Button ────────────────────────────────────────────────────
    refreshBtn.addEventListener('click', () => {
        checkStatus();
        loadStats();
        loadHistory();
    });

    // ── Utility Helpers ──────────────────────────────────────────────────────
    function setLoading(isLoading) {
        scanButton.disabled = isLoading;
        scanBtnText.textContent = isLoading ? 'Analyzing...' : 'Scan URL';
    }

    function showAlert(msg, type = 'danger') {
        alertBox.className = `alert alert-${type}`;
        alertBox.textContent = msg;
        alertBox.classList.remove('hidden');
    }

    function hideAlert() {
        alertBox.classList.add('hidden');
    }

    function escapeHtml(text) {
        if (!text) return '';
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    // ── Initial Page Load ────────────────────────────────────────────────────
    checkStatus();
    loadStats();
    loadHistory();
});
