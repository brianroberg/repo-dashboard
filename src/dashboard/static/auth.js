/**
 * Client-side authentication layer for the dashboard.
 *
 * On page load, checks sessionStorage for a stored API key.
 * If found, fetches dashboard content silently.
 * If missing, shows the login form.
 *
 * The key is sent exclusively via the X-API-Key header —
 * it never appears in a URL.
 */

const STORAGE_KEY = 'dashboard_api_key';
const CONTENT_URL = '/api/dashboard/html';

/* ── State helpers ───────────────────────────────────────────────── */

let fetchInFlight = false;

function getStoredKey() {
    return sessionStorage.getItem(STORAGE_KEY);
}

function storeKey(key) {
    sessionStorage.setItem(STORAGE_KEY, key);
}

function clearKey() {
    sessionStorage.removeItem(STORAGE_KEY);
}

/* ── DOM references (set in init) ────────────────────────────────── */

let loginPanel, dashboardPanel, dashboardContent, dashboardLoading;
let loginForm, apiKeyInput, loginError, loginSubmit;

/* ── UI transitions ──────────────────────────────────────────────── */

function showLogin(errorMessage) {
    loginPanel.hidden = false;
    dashboardPanel.hidden = true;
    if (errorMessage) {
        loginError.textContent = errorMessage;
        loginError.hidden = false;
    } else {
        loginError.textContent = '';
        loginError.hidden = true;
    }
    apiKeyInput.focus();
}

function showDashboard() {
    loginPanel.hidden = true;
    dashboardPanel.hidden = false;
}

function showLoading(visible) {
    dashboardLoading.hidden = !visible;
}

function setFormBusy(busy) {
    loginSubmit.disabled = busy;
    loginSubmit.textContent = busy ? 'Checking\u2026' : 'Unlock Dashboard';
    apiKeyInput.disabled = busy;
}

/* ── Content fetching ────────────────────────────────────────────── */

async function fetchDashboard(key) {
    let response;
    try {
        response = await fetch(CONTENT_URL, {
            headers: { 'X-API-Key': key },
        });
    } catch (_) {
        return { ok: false, status: 0, message: 'Network error \u2014 check your connection and try again.' };
    }

    if (response.ok) {
        const html = await response.text();
        return { ok: true, html: html };
    }

    if (response.status === 401 || response.status === 403) {
        return { ok: false, status: response.status, message: 'Invalid API key. Please try again.' };
    }

    return { ok: false, status: response.status, message: 'Server error (' + response.status + '). Try again later.' };
}

/**
 * Inject server-rendered HTML into the dashboard container.
 * Safety: the HTML originates from our own Jinja2 templates which
 * auto-escape all dynamic values — this is trusted server content,
 * not user input.
 */
function injectContent(html) {
    dashboardContent.innerHTML = html;  // trusted: from our own /api/dashboard/html endpoint
    // Re-initialize filter switches now that the dashboard DOM exists.
    if (typeof initFilters === 'function') {
        initFilters();
    }
}

/* ── Auth flow ───────────────────────────────────────────────────── */

/**
 * Attempt to load the dashboard with the given key.
 * When silent is true (auto-load with stored key), the login panel stays
 * visible until the fetch succeeds — avoiding a flash of the loading
 * spinner if the stored key turns out to be expired.
 */
async function loadDashboard(key, silent = true) {
    if (fetchInFlight) return;
    fetchInFlight = true;

    if (!silent) {
        showDashboard();
        showLoading(true);
    }

    const result = await fetchDashboard(key);
    fetchInFlight = false;

    if (result.ok) {
        showDashboard();
        showLoading(false);
        injectContent(result.html);
    } else {
        clearKey();
        showLogin(silent ? null : result.message);
    }
}

async function handleLoginSubmit(event) {
    event.preventDefault();
    if (fetchInFlight) return;
    loginError.hidden = true;

    const key = apiKeyInput.value.trim();
    if (!key) {
        showLogin('Please enter your API key.');
        return;
    }

    setFormBusy(true);
    fetchInFlight = true;
    const result = await fetchDashboard(key);
    fetchInFlight = false;
    setFormBusy(false);

    if (result.ok) {
        storeKey(key);
        showDashboard();
        injectContent(result.html);
    } else {
        showLogin(result.message);
        apiKeyInput.select();
    }
}

/* ── Initialization ──────────────────────────────────────────────── */

function initAuth() {
    loginPanel = document.getElementById('login-panel');
    dashboardPanel = document.getElementById('dashboard-panel');
    dashboardContent = document.getElementById('dashboard-content');
    dashboardLoading = document.getElementById('dashboard-loading');
    loginForm = document.getElementById('login-form');
    apiKeyInput = document.getElementById('api-key-input');
    loginError = document.getElementById('login-error');
    loginSubmit = document.getElementById('login-submit');

    if (!loginPanel || !dashboardPanel) return;

    loginForm.addEventListener('submit', handleLoginSubmit);

    const storedKey = getStoredKey();
    if (storedKey) {
        loadDashboard(storedKey);
    } else {
        showLogin();
    }
}

document.addEventListener('DOMContentLoaded', initAuth);
