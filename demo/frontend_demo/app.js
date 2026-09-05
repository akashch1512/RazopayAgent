const root = document.getElementById("root");

const CHANNELS = [
  "make_call",
  "send_sms",
  "send_whatsapp_message",
  "send_app_notification",
  "send_email",
];

const RETRYABLE_STATUSES = ["FAILED", "DEAD"];

// Bare channel labels the simulation-api uses for a customer reply (these are
// what the agent's outreach tools send to /simulate/*).
const REPLY_CHANNELS = ["whatsapp", "sms", "call", "email", "app_notification"];

// A real, payable Razorpay test order - so a demo viewer can also run the
// genuine hosted-checkout flow alongside the simulated one.
const RAZORPAY_TRY_URL = "https://rzp.io/rzp/cNHCgllt";

// ---------- Notification sound ----------

let _audioCtx = null;

function soundEnabled() {
  try {
    return localStorage.getItem("rzp_sound") !== "off";
  } catch (e) {
    return true;
  }
}

function setSoundEnabled(on) {
  try {
    localStorage.setItem("rzp_sound", on ? "on" : "off");
  } catch (e) {
    /* storage unavailable - keep default */
  }
}

// Browsers only allow audio after a user gesture; call this from click handlers
// so the first real notification can play.
function unlockAudio() {
  try {
    _audioCtx = _audioCtx || new (window.AudioContext || window["webkitAudioContext"])();
    if (_audioCtx.state === "suspended") _audioCtx.resume();
  } catch (e) {
    /* no Web Audio - notifications are silent */
  }
}

// A short two-note chime, synthesized (no asset file needed).
function playPing() {
  if (!soundEnabled()) return;
  try {
    _audioCtx = _audioCtx || new (window.AudioContext || window["webkitAudioContext"])();
    const ctx = _audioCtx;
    if (ctx.state === "suspended") ctx.resume();
    const now = ctx.currentTime;
    [880, 1174.7].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq;
      const start = now + i * 0.12;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.22, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.22);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.24);
    });
  } catch (e) {
    /* audio not available */
  }
}

function soundToggleLabel() {
  return soundEnabled() ? "🔔 Sound on" : "🔕 Muted";
}

// ---------- Live dashboard refresh ----------

const dashState = { timer: null, sig: null, tick: null };

function stopDashboardAutoRefresh() {
  if (dashState.timer) clearInterval(dashState.timer);
  if (dashState.tick) clearInterval(dashState.tick);
  dashState.timer = null;
  dashState.tick = null;
}

function formatCountdown(ms) {
  const total = Math.max(0, Math.round(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

// Updates every `.queue-timer` (a QUEUED case waiting out its grace window).
function tickQueueTimers() {
  const now = Date.now();
  let anyWaiting = false;
  document.querySelectorAll(".queue-timer").forEach((el) => {
    const untilStr = el.dataset.until;
    if (!untilStr) return;
    const until = new Date(untilStr).getTime();
    if (isNaN(until)) return;
    const remaining = until - now;
    const out = el.querySelector(".queue-remaining");
    if (!out) return;
    if (remaining > 0) {
      anyWaiting = true;
      out.textContent = formatCountdown(remaining);
      el.classList.remove("queue-timer-due");
    } else {
      out.textContent = "starting…";
      el.classList.add("queue-timer-due");
    }
  });
  const banner = document.getElementById("queue-banner-count");
  if (banner && !anyWaiting) {
    const card = document.getElementById("queue-banner");
    if (card) card.hidden = true;
  }
}

function caseSignature(cases) {
  return (cases || [])
    .map((c) => `${c.id}:${c.processingStatus}:${c.lastEventAt}:${c.nextVisibleAt || c.next_visible_at || ""}`)
    .sort()
    .join("|");
}

async function dashboardTick(businessId) {
  // Never redraw the page out from under an open overlay, an expanded case, or
  // someone editing a field.
  if (document.getElementById("controls-overlay")) return;
  const active = document.activeElement;
  if (active && (active.tagName === "INPUT" || active.tagName === "TEXTAREA")) return;
  if (document.querySelector(".case-detail-row:not([hidden])")) return;

  let cases;
  try {
    cases = await api(`/recovery-cases/?business_id=${businessId}`);
  } catch (e) {
    return;
  }

  const sig = caseSignature(cases);
  if (dashState.sig === null || sig === dashState.sig) {
    dashState.sig = sig;
    return;
  }
  dashState.sig = sig;
  playPing();
  renderDashboard();
}

function startDashboardAutoRefresh(businessId, cases) {
  stopDashboardAutoRefresh();
  dashState.sig = caseSignature(cases);
  dashState.timer = setInterval(() => dashboardTick(businessId), 8000);
  dashState.tick = setInterval(tickQueueTimers, 1000);
  tickQueueTimers();
}

function waitingCases(cases) {
  const now = Date.now();
  return (cases || []).filter((c) => {
    const next = c.nextVisibleAt || c.next_visible_at;
    return c.processingStatus === "QUEUED" && next && new Date(next).getTime() > now;
  });
}

// The "Runs in" table cell - a live countdown for a case still in its grace
// window, or a short status word for everything else.
function queueCell(c) {
  const status = c.processingStatus;
  const next = c.nextVisibleAt || c.next_visible_at;
  if (status === "QUEUED" && next && new Date(next).getTime() > Date.now()) {
    return `<span class="queue-timer" data-until="${escapeHtml(next)}" title="Grace window - the customer has this long to fix it before the agent starts">⏳ <span class="queue-remaining">…</span></span>`;
  }
  if (status === "QUEUED" || status === "RECEIVED") return `<span class="muted">any moment</span>`;
  if (status === "PROCESSING") return `<span class="muted">running now</span>`;
  if (status === "FAILED") return `<span class="muted">retry pending</span>`;
  return "-";
}

function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "object") return escapeHtml(JSON.stringify(value));
  return escapeHtml(value);
}

// Razorpay amounts are always in the smallest currency unit (paise for INR).
function formatAmount(amountInSmallestUnit) {
  if (amountInSmallestUnit === null || amountInSmallestUnit === undefined || amountInSmallestUnit === "") {
    return "-";
  }
  return (Number(amountInSmallestUnit) / 100).toFixed(2);
}

async function request(baseUrl, pathname, options = {}) {
  const res = await fetch(`${baseUrl}${pathname}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch (e) {
    data = text;
  }
  if (!res.ok) {
    const detail = data && data.detail ? data.detail : res.statusText;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    err.status = res.status;
    throw err;
  }
  return data;
}

function api(pathname, options = {}) {
  return request(CONFIG.BACKEND_BASE_URL, pathname, options);
}

function simApi(pathname, options = {}) {
  return request(CONFIG.SIMULATION_API_BASE_URL, pathname, options);
}

function getBusinessId() {
  return localStorage.getItem("rzp_business_id");
}

function setBusinessId(id) {
  localStorage.setItem("rzp_business_id", id);
}

function clearBusinessId() {
  localStorage.removeItem("rzp_business_id");
}

function navigate(pathname) {
  window.history.pushState({}, "", pathname);
  render();
}

// ---------- Onboarding page ----------

function renderOnboarding(message) {
  root.innerHTML = `
    <div class="center">
      <h1>Razopay Recovery Agent</h1>
      <p class="hint">Connect your Razorpay business account to get started.</p>
      ${
        message
          ? `
        <div class="${message.type} dismissable" id="onboarding-message">
          <span>${escapeHtml(message.text)}</span>
          <button id="dismiss-message-btn" class="dismiss-btn" aria-label="Dismiss">&times;</button>
        </div>
      `
          : ""
      }

      <button class="primary" id="continue-razorpay-btn">
        <img class="logo" src="/assets/icon.webp" alt="Razorpay" />
        <span>Continue with Razorpay</span>
      </button>

      <hr class="divider" style="width:100%" />

      <div style="width:100%; max-width:360px; text-align:left;">
        <div class="field">
          <label for="lookup-reference">Existing business reference ID</label>
          <input id="lookup-reference" type="text" value="test-business-1" />
        </div>
        <button id="lookup-btn" style="width:100%">Open business dashboard</button>
      </div>
    </div>
  `;

  document.getElementById("continue-razorpay-btn").addEventListener("click", startOnboarding);
  document.getElementById("lookup-btn").addEventListener("click", lookupBusiness);

  const dismissBtn = document.getElementById("dismiss-message-btn");
  if (dismissBtn) {
    dismissBtn.addEventListener("click", () => {
      document.getElementById("onboarding-message").remove();
    });
  }
}

async function startOnboarding() {
  const btn = document.getElementById("continue-razorpay-btn");
  btn.disabled = true;
  try {
    const referenceId = `demo-business-${Date.now()}`;
    const result = await api("/businesses/", {
      method: "POST",
      body: JSON.stringify({
        name: "Demo Business",
        reference_id: referenceId,
      }),
    });
    window.location.href = result.authorization_url;
  } catch (err) {
    const credentialsMissing = /RAZORPAY_CLIENT_ID|RAZORPAY_CLIENT_SECRET/i.test(err.message);
    const text = credentialsMissing
      ? "Due to unavailability of Razorpay Technological Partner Credentials. Either run your own copy of repo with credentials or use demo mode which uses api keys."
      : `Could not start onboarding: ${err.message}`;
    renderOnboarding({ type: "error", text });
  }
}

async function lookupBusiness() {
  const referenceId = document.getElementById("lookup-reference").value.trim();
  if (!referenceId) return;
  try {
    const business = await api(`/businesses/lookup?reference_id=${encodeURIComponent(referenceId)}`);
    setBusinessId(business.id);
    navigate("/business");
  } catch (err) {
    renderOnboarding({ type: "error", text: `Business not found: ${err.message}` });
  }
}

// ---------- Onboarding callback ----------

function handleOnboardComplete() {
  const params = new URLSearchParams(window.location.search);
  const businessId = params.get("business_id");
  const status = params.get("status");
  const error = params.get("error");

  if (error) {
    navigate("/");
    setTimeout(() => renderOnboarding({ type: "error", text: `Onboarding failed: ${error}` }), 0);
    return;
  }

  if (businessId) {
    setBusinessId(businessId);
  }

  window.history.replaceState({}, "", "/business");
  renderDashboard(status ? { type: "success", text: `Onboarding status: ${status}` } : null);
}

// ---------- Dashboard ----------

async function renderDashboard(message) {
  stopDashboardAutoRefresh();
  const businessId = getBusinessId();
  if (!businessId) {
    navigate("/");
    return;
  }

  root.innerHTML = `<p class="muted">Loading business dashboard...</p>`;

  let business, webhook, settings, invoices, cases;
  try {
    [business, webhook, settings, invoices, cases] = await Promise.all([
      api(`/businesses/${businessId}`),
      api(`/businesses/${businessId}/webhook`).catch(() => null),
      api(`/businesses/${businessId}/settings`).catch(() => null),
      api(`/invoices/${businessId}`).catch(() => []),
      api(`/recovery-cases/?business_id=${businessId}`).catch(() => []),
    ]);
  } catch (err) {
    root.innerHTML = `<div class="error">Failed to load business: ${escapeHtml(err.message)}</div>
      <button id="back-btn">Back to onboarding</button>`;
    document.getElementById("back-btn").addEventListener("click", () => {
      clearBusinessId();
      navigate("/");
    });
    return;
  }

  root.innerHTML = `
    <div class="top-bar">
      <h1>Business Dashboard</h1>
      <div class="top-bar-actions">
        <button id="controls-btn" class="accent-btn">Controls</button>
        <a class="btn-link" href="${RAZORPAY_TRY_URL}" target="_blank" rel="noopener noreferrer">Try actual Razorpay order</a>
        <button id="sound-toggle-btn" title="Notification sound">${soundToggleLabel()}</button>
        <button id="logout-btn">Switch business</button>
      </div>
    </div>

    ${message ? `<div class="${message.type}">${escapeHtml(message.text)}</div>` : ""}
    <div id="action-message"></div>

    <div class="card">
      <div class="card-title">Business Details</div>
      <div class="row"><span class="key">Name</span><span>${formatValue(business.name)}</span></div>
      <div class="row"><span class="key">Reference ID</span><span>${formatValue(business.referenceId)}</span></div>
      <div class="row"><span class="key">Contact Email</span><span>${formatValue(business.contactEmail)}</span></div>
      <div class="row"><span class="key">Status</span><span class="tag">${formatValue(business.status)}</span></div>
      <div class="row"><span class="key">Razorpay Account ID</span><span>${formatValue(business.razorpayAccountId)}</span></div>
      <div class="row"><span class="key">Token Scope</span><span>${formatValue(business.tokenScope)}</span></div>
      <div class="row"><span class="key">Created At</span><span>${formatValue(business.createdAt)}</span></div>
    </div>

    <div class="card">
      <div class="card-title">Webhook Configuration</div>
      ${
        webhook
          ? `
        <div class="row"><span class="key">URL</span><span>${formatValue(webhook.url)}</span></div>
        <div class="row"><span class="key">Active</span><span>${formatValue(webhook.active)}</span></div>
        <div class="row"><span class="key">Events</span><span>${formatValue((webhook.events || []).join(", "))}</span></div>
        <div class="row"><span class="key">Alert Email</span><span>${formatValue(webhook.alert_email)}</span></div>
      `
          : `<p class="muted">Inside Test Mode API Keys are being used due to unavailibility of Razorpay Technological Partner Credentials.</p>`
      }
    </div>

    ${renderCaseStats(cases)}

    ${renderQueueBanner(cases)}

    <div class="card">
      <div class="card-title-row">
        <div class="card-title">Recovery Cases (${cases.length})</div>
        <button id="refresh-cases-btn" title="Refresh">Refresh</button>
      </div>
      ${
        cases.length === 0
          ? `<p class="muted">No recovery cases found.</p>`
          : `
        <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Case</th><th>Customer</th><th>Event</th><th>Status</th><th>Runs in</th><th>Priority</th><th>Last Event</th><th></th></tr>
          </thead>
          <tbody>
            ${cases
              .map(
                (c) => `
              <tr>
                <td>${formatValue(c.caseKey)}</td>
                <td>${formatValue(c.customerEmail || c.customerContact)}</td>
                <td>${formatValue(c.latestEventType)}</td>
                <td><span class="tag">${formatValue(c.processingStatus)}</span></td>
                <td>${queueCell(c)}</td>
                <td>${formatValue(c.priority)}</td>
                <td>${formatValue(c.lastEventAt)}</td>
                <td class="actions">
                  <button class="view-case-btn" data-case-id="${c.id}">View</button>
                  ${
                    RETRYABLE_STATUSES.includes(c.processingStatus)
                      ? `<button class="retry-case-btn" data-case-id="${c.id}">Retry</button>`
                      : ""
                  }
                </td>
              </tr>
              <tr id="case-detail-${c.id}" class="case-detail-row" hidden>
                <td colspan="8"><div class="case-detail"></div></td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
        </div>
      `
      }
    </div>

    <div class="card">
      <div class="card-title">Invoices (${invoices.length})</div>
      ${
        invoices.length === 0
          ? `<p class="muted">No invoices found.</p>`
          : `
        <div class="table-wrap">
        <table>
          <thead>
            <tr><th>Invoice #</th><th>Customer</th><th>Amount</th><th>Due</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            ${invoices
              .map(
                (inv) => `
              <tr>
                <td>${formatValue(inv.invoice_number)}</td>
                <td>${formatValue(inv.customer_details ? inv.customer_details.name || inv.customer_details.email : "")}</td>
                <td>${formatAmount(inv.amount)} ${formatValue(inv.currency)}</td>
                <td>${formatAmount(inv.amount_due)}</td>
                <td><span class="tag">${formatValue(inv.status)}</span></td>
                <td><button class="chase-btn" data-invoice-id="${inv.id}">Chase</button></td>
              </tr>
            `
              )
              .join("")}
          </tbody>
        </table>
        </div>
      `
      }
    </div>

    <div class="card agent-settings-card">
      <div class="card-title">Agent Settings</div>
      <form id="settings-form">
        <div class="field">
          <label for="settings-description">Business Description</label>
          <textarea id="settings-description" rows="2">${settings ? escapeHtml(settings.businessDescription || "") : ""}</textarea>
        </div>
        <div class="field">
          <label for="settings-tone">Tone</label>
          <input id="settings-tone" type="text" value="${settings ? escapeHtml(settings.tone || "") : "friendly and professional"}" />
        </div>
        <div class="field">
          <label for="settings-instructions">Custom Instructions</label>
          <textarea id="settings-instructions" rows="2">${settings ? escapeHtml(settings.customInstructions || "") : ""}</textarea>
        </div>
        <div class="field">
          <label>Enabled Channels (none checked = all allowed)</label>
          <div class="checkbox-list">
            ${CHANNELS.map((channel) => {
              const checked =
                settings && Array.isArray(settings.enabledChannels) && settings.enabledChannels.includes(channel)
                  ? "checked"
                  : "";
              return `<label><input type="checkbox" name="channel" value="${channel}" ${checked} /> ${channel}</label>`;
            }).join("")}
          </div>
        </div>
        <div class="save-row">
          <button type="submit">Save Settings</button>
          <span id="settings-status" class="save-status"></span>
        </div>
      </form>
    </div>
  `;

  document.getElementById("logout-btn").addEventListener("click", () => {
    clearBusinessId();
    navigate("/");
  });

  document.getElementById("controls-btn").addEventListener("click", () => {
    unlockAudio();
    openControlsOverlay(cases);
  });

  document.getElementById("sound-toggle-btn").addEventListener("click", (e) => {
    setSoundEnabled(!soundEnabled());
    unlockAudio();
    if (soundEnabled()) playPing();
    e.target.textContent = soundToggleLabel();
  });

  document.getElementById("settings-form").addEventListener("submit", (e) => saveSettings(e, businessId));

  document.getElementById("refresh-cases-btn").addEventListener("click", () => renderDashboard());

  document.querySelectorAll(".chase-btn").forEach((btn) => {
    btn.addEventListener("click", () => chaseInvoice(businessId, btn.dataset.invoiceId));
  });

  document.querySelectorAll(".view-case-btn").forEach((btn) => {
    btn.addEventListener("click", () => toggleCaseDetail(btn.dataset.caseId));
  });

  document.querySelectorAll(".retry-case-btn").forEach((btn) => {
    btn.addEventListener("click", () => retryCase(btn.dataset.caseId, businessId));
  });

  // Keep the dashboard live - no manual refresh needed.
  startDashboardAutoRefresh(businessId, cases);
}

const PROCESSING_STATUSES = ["RECEIVED", "QUEUED", "PROCESSING"];
const HANDLED_STATUSES = ["RESOLVED", "PROCESSED"];
const FAILED_STATUSES = ["FAILED", "DEAD"];

function renderQueueBanner(cases) {
  const waiting = waitingCases(cases);
  if (waiting.length === 0) return "";
  const soonest = waiting
    .map((c) => new Date(c.nextVisibleAt || c.next_visible_at).getTime())
    .sort((a, b) => a - b)[0];
  return `
    <div class="card queue-banner" id="queue-banner">
      <span id="queue-banner-count">⏳ ${waiting.length} case${waiting.length > 1 ? "s" : ""} waiting out the grace window</span>
      - next one starts in
      <span class="queue-timer" data-until="${escapeHtml(new Date(soonest).toISOString())}"><span class="queue-remaining">…</span></span>.
      <span class="hint">The customer gets this window to fix it themselves before the agent steps in.</span>
    </div>
  `;
}

function renderCaseStats(cases) {
  const total = cases.length;
  const handled = cases.filter((c) => HANDLED_STATUSES.includes(c.processingStatus)).length;
  const processing = cases.filter((c) => PROCESSING_STATUSES.includes(c.processingStatus)).length;
  const failed = cases.filter((c) => FAILED_STATUSES.includes(c.processingStatus)).length;

  return `
    <div class="card">
      <div class="card-title">Recovery Case Stats</div>
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-value">${total}</div>
          <div class="stat-label">Total Cases</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${handled}</div>
          <div class="stat-label">Handled</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${processing}</div>
          <div class="stat-label">Under Processing</div>
        </div>
        <div class="stat-box">
          <div class="stat-value">${failed}</div>
          <div class="stat-label">Failed</div>
        </div>
      </div>
    </div>
  `;
}

function showActionMessage(type, text) {
  const el = document.getElementById("action-message");
  if (el) el.innerHTML = `<div class="${type}">${escapeHtml(text)}</div>`;
}

async function saveSettings(event, businessId) {
  event.preventDefault();
  const channels = Array.from(document.querySelectorAll('input[name="channel"]:checked')).map((el) => el.value);
  const payload = {
    business_description: document.getElementById("settings-description").value || null,
    tone: document.getElementById("settings-tone").value || "friendly and professional",
    custom_instructions: document.getElementById("settings-instructions").value || null,
    enabled_channels: channels.length > 0 ? channels : null,
  };
  const status = document.getElementById("settings-status");
  const setStatus = (text, ok) => {
    if (!status) return;
    status.textContent = text;
    status.classList.toggle("save-status-error", !ok);
  };
  const submitBtn = event.target.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.disabled = true;
  setStatus("Saving...", true);
  try {
    await api(`/businesses/${businessId}/settings`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
    setStatus("✓ Settings saved", true);
    setTimeout(() => setStatus("", true), 4000);
  } catch (err) {
    setStatus(`Failed: ${err.message}`, false);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

async function chaseInvoice(businessId, invoiceId) {
  const reason = window.prompt("Reason for chasing this invoice (optional):", "");
  try {
    await api(`/invoices/${businessId}/${invoiceId}/chase`, {
      method: "POST",
      body: JSON.stringify({ reason: reason || null }),
    });
    showActionMessage("success", `Chase started for invoice ${invoiceId}.`);
  } catch (err) {
    showActionMessage("error", `Failed to start chase: ${err.message}`);
  }
}

async function retryCase(caseId, businessId) {
  try {
    await api(`/recovery-cases/${caseId}/retry`, { method: "POST" });
    showActionMessage("success", `Case ${caseId} re-queued.`);
    renderDashboard();
  } catch (err) {
    showActionMessage("error", `Failed to retry case: ${err.message}`);
  }
}

async function toggleCaseDetail(caseId) {
  const row = document.getElementById(`case-detail-${caseId}`);
  if (!row) return;

  if (!row.hidden) {
    row.hidden = true;
    return;
  }

  const container = row.querySelector(".case-detail");
  container.innerHTML = `<p class="muted">Loading case detail...</p>`;
  row.hidden = false;

  try {
    const detail = await api(`/recovery-cases/${caseId}`);
    const nextVisible = detail.nextVisibleAt || detail.next_visible_at;
    container.innerHTML = `
      <div class="row"><span class="key">Entity Type</span><span>${formatValue(detail.entityType)}</span></div>
      <div class="row"><span class="key">Primary Entity ID</span><span>${formatValue(detail.primaryEntityId)}</span></div>
      <div class="row"><span class="key">Priority Reason</span><span>${formatValue(detail.priorityReason)}</span></div>
      <div class="row"><span class="key">Processing Attempts</span><span>${formatValue(detail.processingAttempts)}</span></div>
      ${
        nextVisible
          ? `<div class="row"><span class="key">Runs in</span><span>${queueCell(detail)}</span></div>`
          : ""
      }
      <div class="row"><span class="key">Last Error</span><span>${formatValue(detail.lastError)}</span></div>

      <h3>Agent Actions</h3>
      ${
        detail.actions && detail.actions.length > 0
          ? `<div class="table-wrap"><table>
              <thead><tr><th>Tool</th><th>Status</th><th>Created At</th></tr></thead>
              <tbody>
                ${detail.actions
                  .map(
                    (a) => `<tr><td>${formatValue(a.toolName)}</td><td>${formatValue(a.status)}</td><td>${formatValue(a.createdAt)}</td></tr>`
                  )
                  .join("")}
              </tbody>
            </table></div>`
          : `<p class="muted">No agent actions yet.</p>`
      }

      <h3>Webhook History</h3>
      <p class="hint">Click a row to see its full detail.</p>
      ${
        detail.history && detail.history.length > 0
          ? `<div class="table-wrap"><table>
              <thead><tr><th>Event Type</th><th>Entity Status</th><th>Received At</th></tr></thead>
              <tbody>
                ${detail.history
                  .map(
                    (h, idx) => `
                    <tr class="webhook-history-row" data-idx="${idx}">
                      <td>${formatValue(h.eventType)}</td><td>${formatValue(h.entityStatus)}</td><td>${formatValue(h.receivedAt)}</td>
                    </tr>
                    <tr id="webhook-history-detail-${caseId}-${idx}" class="webhook-history-detail-row" hidden>
                      <td colspan="3"><div class="case-detail"></div></td>
                    </tr>
                  `
                  )
                  .join("")}
              </tbody>
            </table></div>`
          : `<p class="muted">No webhook history yet.</p>`
      }
    `;

    container.querySelectorAll(".webhook-history-row").forEach((historyRow) => {
      historyRow.addEventListener("click", () => {
        const idx = Number(historyRow.dataset.idx);
        toggleWebhookHistoryDetail(caseId, idx, detail.history[idx]);
      });
    });
    tickQueueTimers();
  } catch (err) {
    container.innerHTML = `<div class="error">Failed to load case detail: ${escapeHtml(err.message)}</div>`;
  }
}

function toggleWebhookHistoryDetail(caseId, idx, event) {
  const row = document.getElementById(`webhook-history-detail-${caseId}-${idx}`);
  if (!row) return;

  if (!row.hidden) {
    row.hidden = true;
    return;
  }

  const container = row.querySelector(".case-detail");

  if (event.eventType === "customer.feedback") {
    const feedback = event.payload && event.payload.payload && event.payload.payload.customer_feedback
      ? event.payload.payload.customer_feedback.entity
      : null;

    container.innerHTML = feedback
      ? `
        <div class="row"><span class="key">Channel</span><span>${formatValue(feedback.channel)}</span></div>
        <div class="row"><span class="key">Message</span><span>${formatValue(feedback.message)}</span></div>
        <div class="row"><span class="key">Status</span><span>${formatValue(feedback.status)}</span></div>
      `
      : `<pre class="json-block">${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre>`;
  } else {
    container.innerHTML = `<pre class="json-block">${escapeHtml(JSON.stringify(event.payload, null, 2))}</pre>`;
  }

  row.hidden = false;
}

// ---------- Customer Controls overlay ----------

const controlsState = {
  caseId: null,
  pollTimer: null,
  cases: [],
  seenAgentCount: null,
  pendingChannel: null,
  userPickedChannel: false,
};

function customerLabel(c) {
  const who = c.customerEmail || c.customerContact || "unknown customer";
  return `${who}  ·  ${c.caseKey || "case " + c.id}  ·  ${c.processingStatus}`;
}

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function openControlsOverlay(cases) {
  controlsState.cases = cases || [];

  const existing = document.getElementById("controls-overlay");
  if (existing) existing.remove();

  const overlay = document.createElement("div");
  overlay.id = "controls-overlay";
  overlay.className = "overlay-backdrop";
  overlay.innerHTML = `
    <div class="overlay-panel" role="dialog" aria-modal="true" aria-label="Customer controls">
      <div class="overlay-head">
        <div>
          <div class="overlay-title">Customer Controls</div>
          <div class="hint">Simulate the customer side - see what the agent sent, reply back, or mark a case paid. New messages arrive automatically.</div>
        </div>
        <div class="overlay-head-actions">
          <button id="controls-sound" title="Notification sound">${soundToggleLabel()}</button>
          <button id="controls-close" class="dismiss-btn" aria-label="Close">&times;</button>
        </div>
      </div>

      <div class="overlay-body">
        <div class="field">
          <label for="controls-customer">Customer / case</label>
          <select id="controls-customer">
            <option value="">Select a customer...</option>
            ${controlsState.cases
              .map((c) => `<option value="${c.id}">${escapeHtml(customerLabel(c))}</option>`)
              .join("")}
          </select>
          ${controlsState.cases.length === 0 ? `<p class="hint">No recovery cases for this business yet.</p>` : ""}
        </div>

        <div id="controls-conversation" class="conversation">
          <p class="muted">Select a customer to see the message history.</p>
        </div>

        <form id="controls-reply-form" class="reply-form" hidden>
          <div id="controls-pending-hint" class="pending-hint" hidden></div>
          <div class="reply-row">
            <select id="controls-reply-channel" class="reply-channel">
              ${REPLY_CHANNELS.map((ch) => `<option value="${ch}">${ch}</option>`).join("")}
            </select>
            <input id="controls-reply-message" type="text" placeholder="Type the customer's reply..." autocomplete="off" />
            <button type="submit">Send as customer</button>
          </div>
        </form>

        <div class="overlay-footer" hidden id="controls-footer">
          <button id="controls-mark-paid" class="accent-btn">Mark this case as paid</button>
          <span id="controls-status" class="hint"></span>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);
  document.body.classList.add("overlay-open");
  unlockAudio();

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeControlsOverlay();
  });
  document.getElementById("controls-close").addEventListener("click", closeControlsOverlay);
  document.getElementById("controls-sound").addEventListener("click", (e) => {
    setSoundEnabled(!soundEnabled());
    unlockAudio();
    if (soundEnabled()) playPing();
    e.target.textContent = soundToggleLabel();
    const topToggle = document.getElementById("sound-toggle-btn");
    if (topToggle) topToggle.textContent = soundToggleLabel();
  });
  document.addEventListener("keydown", onControlsKeydown);

  document.getElementById("controls-customer").addEventListener("change", (e) => {
    selectControlsCase(e.target.value);
  });
  document.getElementById("controls-reply-form").addEventListener("submit", sendControlsReply);
  document.getElementById("controls-reply-channel").addEventListener("change", () => {
    controlsState.userPickedChannel = true;
  });
  document.getElementById("controls-mark-paid").addEventListener("click", markControlsCasePaid);
}

function onControlsKeydown(e) {
  if (e.key === "Escape") closeControlsOverlay();
}

let _titleResetTimer = null;
function flashOverlayTitle() {
  const box = document.getElementById("controls-conversation");
  if (box) {
    box.classList.add("conversation-flash");
    setTimeout(() => box.classList.remove("conversation-flash"), 1200);
  }
  if (document.hidden) {
    document.title = "● New message - Razopay Agent Demo";
    clearTimeout(_titleResetTimer);
    const restore = () => {
      document.title = "Razopay Agent Demo";
      document.removeEventListener("visibilitychange", restore);
    };
    document.addEventListener("visibilitychange", restore);
    _titleResetTimer = setTimeout(restore, 10000);
  }
}

function closeControlsOverlay() {
  if (controlsState.pollTimer) clearInterval(controlsState.pollTimer);
  controlsState.pollTimer = null;
  controlsState.caseId = null;
  controlsState.seenAgentCount = null;
  controlsState.pendingChannel = null;
  controlsState.userPickedChannel = false;
  document.removeEventListener("keydown", onControlsKeydown);
  document.body.classList.remove("overlay-open");
  const overlay = document.getElementById("controls-overlay");
  if (overlay) overlay.remove();
  // Case status may have changed (mark paid / new reply re-queued it).
  renderDashboard();
}

function selectControlsCase(caseId) {
  controlsState.caseId = caseId || null;
  controlsState.seenAgentCount = null; // first load of a case never pings
  controlsState.pendingChannel = null;
  controlsState.userPickedChannel = false;
  const hint = document.getElementById("controls-pending-hint");
  if (hint) hint.hidden = true;
  if (controlsState.pollTimer) clearInterval(controlsState.pollTimer);
  controlsState.pollTimer = null;

  const form = document.getElementById("controls-reply-form");
  const footer = document.getElementById("controls-footer");
  form.hidden = !caseId;
  footer.hidden = !caseId;
  setControlsStatus("");

  if (!caseId) {
    document.getElementById("controls-conversation").innerHTML =
      `<p class="muted">Select a customer to see the message history.</p>`;
    return;
  }

  loadConversation();
  controlsState.pollTimer = setInterval(loadConversation, 4000);
}

async function loadConversation() {
  const caseId = controlsState.caseId;
  if (!caseId) return;
  const box = document.getElementById("controls-conversation");
  if (!box) return;

  let dashboard;
  try {
    dashboard = await simApi(`/dashboard/users/${encodeURIComponent(caseId)}`);
  } catch (err) {
    if (err.status === 404) {
      box.innerHTML = `<p class="muted">No messages yet - the agent hasn't contacted this customer.</p>`;
    } else {
      box.innerHTML = `<p class="error">Could not load messages: ${escapeHtml(err.message)}</p>`;
    }
    return;
  }

  const comms = (dashboard.recovery_case && dashboard.recovery_case.communications) || [];
  if (comms.length === 0) {
    box.innerHTML = `<p class="muted">No messages yet - the agent hasn't contacted this customer.</p>`;
    controlsState.seenAgentCount = 0;
    return;
  }

  // Ring the notification when a new agent message appears (not on first load).
  const agentCount = comms.filter((c) => c.message).length;
  if (controlsState.seenAgentCount !== null && agentCount > controlsState.seenAgentCount) {
    playPing();
    flashOverlayTitle();
  }
  controlsState.seenAgentCount = agentCount;

  // The channel of the newest agent message the customer hasn't answered yet -
  // make that the default reply channel and flag it.
  const unanswered = comms.filter((c) => c.message && !c.customer_response);
  updatePendingChannel(unanswered.length ? unanswered[0].channel : null);

  // Store keeps newest first; show oldest first like a chat.
  const ordered = [...comms].reverse();
  const wasNearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;

  box.innerHTML = ordered
    .map((c) => {
      const parts = [];
      if (c.message) {
        parts.push(`
          <div class="msg msg-agent">
            <div class="msg-meta">Agent · ${escapeHtml(c.channel)} · ${escapeHtml(formatTime(c.created_at))}</div>
            <div class="msg-body">${escapeHtml(c.message)}</div>
          </div>`);
      }
      if (c.customer_response) {
        parts.push(`
          <div class="msg msg-customer">
            <div class="msg-meta">Customer · ${escapeHtml(c.channel)}</div>
            <div class="msg-body">${escapeHtml(c.customer_response)}</div>
          </div>`);
      }
      return parts.join("");
    })
    .join("");

  if (wasNearBottom) box.scrollTop = box.scrollHeight;
}

function updatePendingChannel(channel) {
  const select = document.getElementById("controls-reply-channel");
  const hint = document.getElementById("controls-pending-hint");
  if (!select || !hint) return;

  // Refresh option labels: a dot marks the channel with an unanswered message.
  Array.from(select.options).forEach((opt) => {
    opt.textContent = opt.value === channel ? `● ${opt.value}` : opt.value;
  });

  if (!channel) {
    hint.hidden = true;
    controlsState.pendingChannel = null;
    return;
  }

  const isNew = channel !== controlsState.pendingChannel;
  controlsState.pendingChannel = channel;
  if (isNew && !controlsState.userPickedChannel && Array.from(select.options).some((o) => o.value === channel)) {
    select.value = channel;
  }
  hint.textContent = `💬 New message on "${channel}" - your reply will go out on this channel.`;
  hint.hidden = false;
}

async function sendControlsReply(event) {
  event.preventDefault();
  unlockAudio();
  const caseId = controlsState.caseId;
  if (!caseId) return;
  const channel = document.getElementById("controls-reply-channel").value;
  const input = document.getElementById("controls-reply-message");
  const message = input.value.trim();
  if (!message) return;

  const submitBtn = event.target.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  try {
    await simApi(`/dashboard/users/${encodeURIComponent(caseId)}/messages`, {
      method: "POST",
      body: JSON.stringify({ case_id: String(caseId), channel, message }),
    });
    input.value = "";
    controlsState.userPickedChannel = false;
    setControlsStatus("Reply sent - the agent will see it on its next run.");
    await loadConversation();
  } catch (err) {
    setControlsStatus(`Could not send reply: ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
}

async function markControlsCasePaid() {
  const caseId = controlsState.caseId;
  if (!caseId) return;
  if (!window.confirm("Mark this case as paid? This closes it as RESOLVED.")) return;

  const btn = document.getElementById("controls-mark-paid");
  btn.disabled = true;
  try {
    const result = await api(`/recovery-cases/${encodeURIComponent(caseId)}/mark-paid`, { method: "POST" });
    // Best-effort: keep the simulation store's narrative in sync too.
    await simApi(`/dashboard/users/${encodeURIComponent(caseId)}/pay`, {
      method: "POST",
      body: JSON.stringify({ case_id: String(caseId) }),
    }).catch(() => {});
    setControlsStatus(`Case marked paid (status: ${result.status || "RESOLVED"}).`);
    await loadConversation();
  } catch (err) {
    setControlsStatus(`Could not mark paid: ${err.message}`, true);
  } finally {
    btn.disabled = false;
  }
}

function setControlsStatus(text, isError) {
  const el = document.getElementById("controls-status");
  if (!el) return;
  el.textContent = text;
  el.classList.toggle("status-error", Boolean(isError));
}

// ---------- Router ----------

function render() {
  const pathname = window.location.pathname;
  if (pathname !== "/business") stopDashboardAutoRefresh();

  if (pathname === "/business/onboard/complete") {
    handleOnboardComplete();
    return;
  }

  if (pathname === "/business") {
    renderDashboard();
    return;
  }

  renderOnboarding();
}

window.addEventListener("popstate", render);
render();
