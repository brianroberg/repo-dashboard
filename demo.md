# Filter Toggle Switches for Repo Dashboard

*2026-02-18T17:18:05Z by Showboat 0.6.0*
<!-- showboat-id: 2cb038b1-fbd2-486b-bb5e-57395cf36bc8 -->

Two toggle filter switches were added to the repo dashboard — a FastAPI + Jinja2 server-side rendered app with a GitHub dark theme. The filters let users focus on repos that need attention by hiding the quiet ones.

## What was built

1. **"Has divergence"** — hides repos where no branches are ahead or behind the default branch
2. **"Hide all-clear"** — hides repos where everything is fine (no ahead/behind, no codespaces, no Fly.io issues)

Both default to off and reset on page reload. The architecture uses **data attributes on cards** set by Jinja2, **CSS class toggling** on the grid container, and **CSS descendant selectors** for filtering — no per-card JS iteration needed.

## Files changed

```bash
git diff --stat HEAD
```

```output
 src/dashboard/static/dashboard.js               |  28 +++++-
 src/dashboard/static/style.css                  | 110 ++++++++++++++++++++++++
 src/dashboard/templates/dashboard.html          |  16 +++-
 src/dashboard/templates/partials/repo_card.html |   5 +-
 4 files changed, 156 insertions(+), 3 deletions(-)
```

### 1. Card data attributes (repo_card.html)

Each repo card now gets `data-has-divergence` and `data-all-clear` attributes set server-side by Jinja2. This means JS never needs to inspect badge DOM elements to determine filter state.

```bash
git diff HEAD -- src/dashboard/templates/partials/repo_card.html | head -20
```

```output
diff --git a/src/dashboard/templates/partials/repo_card.html b/src/dashboard/templates/partials/repo_card.html
index 1af6864..ffe6408 100644
--- a/src/dashboard/templates/partials/repo_card.html
+++ b/src/dashboard/templates/partials/repo_card.html
@@ -1,4 +1,7 @@
-<div class="repo-card" data-repo="{{ view.repo.full_name }}">
+<div class="repo-card"
+     data-repo="{{ view.repo.full_name }}"
+     data-has-divergence="{{ 'true' if (view.attention.branches_ahead_count > 0 or view.attention.branches_behind_count > 0) else 'false' }}"
+     data-all-clear="{{ 'true' if view.attention.all_clear else 'false' }}">
     <div class="repo-card-header" onclick="toggleCard(this)">
         <div class="repo-info">
             <h3 class="repo-name">
```

### 2. Filter toolbar (dashboard.html)

A filter toolbar with two toggle switches sits between the header and the repo grid. The grid also gets `id="repo-grid"` so JS can target it efficiently.

```bash
git diff HEAD -- src/dashboard/templates/dashboard.html
```

```output
diff --git a/src/dashboard/templates/dashboard.html b/src/dashboard/templates/dashboard.html
index 1695add..de1b9ac 100644
--- a/src/dashboard/templates/dashboard.html
+++ b/src/dashboard/templates/dashboard.html
@@ -7,6 +7,20 @@
         <p class="generated-at">Generated at {{ data.generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
     </header>
 
+    <div class="filter-toolbar">
+        <span class="filter-toolbar-label">Filter</span>
+        <label class="filter-switch">
+            <input type="checkbox" id="filter-divergence" class="filter-switch-input">
+            <span class="filter-switch-track" aria-hidden="true"></span>
+            <span class="filter-switch-text">Has divergence</span>
+        </label>
+        <label class="filter-switch">
+            <input type="checkbox" id="filter-all-clear" class="filter-switch-input">
+            <span class="filter-switch-track" aria-hidden="true"></span>
+            <span class="filter-switch-text">Hide all-clear</span>
+        </label>
+    </div>
+
     {% if data.errors %}
     <div class="errors">
         <h2>Errors</h2>
@@ -18,7 +32,7 @@
     </div>
     {% endif %}
 
-    <div class="repo-grid">
+    <div class="repo-grid" id="repo-grid">
         {% for view in data.repos %}
             {% include "partials/repo_card.html" %}
         {% endfor %}
```

### 3. Toggle switch CSS (style.css)

The toggle switch is built with a visually-hidden checkbox, a `.filter-switch-track` span styled as a pill, and the `::after` pseudo-element as the sliding thumb. The checked state uses `input:checked + .track` sibling combinators — no `:has()` needed.

```bash
sed -n '330,433p' src/dashboard/static/style.css
```

```output
/* ── Filter Toolbar ──────────────────────────────────────────────── */

.filter-toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 0;
    margin-bottom: 16px;
    border-bottom: 1px solid var(--border);
}

.filter-toolbar-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-right: 4px;
}

/* ── Filter Switch ───────────────────────────────────────────────── */

.filter-switch {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
}

.filter-switch-input {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

.filter-switch-track {
    display: inline-block;
    position: relative;
    width: 32px;
    height: 18px;
    border-radius: 9px;
    background: var(--border);
    border: 1px solid var(--border);
    transition: background 0.15s, border-color 0.15s;
    flex-shrink: 0;
}

.filter-switch-track::after {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--text-muted);
    transition: transform 0.15s, background 0.15s;
}

.filter-switch-input:checked + .filter-switch-track {
    background: var(--accent);
    border-color: var(--accent);
}

.filter-switch-input:checked + .filter-switch-track::after {
    transform: translateX(14px);
    background: var(--text);
}

.filter-switch-input:focus-visible + .filter-switch-track {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
}

.filter-switch-text {
    font-size: 13px;
    color: var(--text-muted);
    transition: color 0.15s;
}

.filter-switch:hover .filter-switch-text {
    color: var(--text);
}

.filter-switch-input:checked ~ .filter-switch-text {
    color: var(--accent);
}

/* ── Filter Rules ────────────────────────────────────────────────── */

.repo-grid.filter-has-divergence .repo-card[data-has-divergence="false"] {
    display: none;
}

.repo-grid.filter-all-clear .repo-card[data-all-clear="true"] {
    display: none;
}
```

### 4. Filter JS (dashboard.js)

The JS is minimal — a data-driven `FILTERS` table maps checkbox IDs to CSS classes on the grid. `toggleAll` was also updated to skip CSS-hidden cards via `getComputedStyle`.

```bash
cat src/dashboard/static/dashboard.js
```

```output
/**
 * Toggle expand/collapse for repo cards.
 */
function toggleCard(headerEl) {
    const card = headerEl.closest('.repo-card');
    const details = card.querySelector('.repo-card-details');

    if (card.classList.contains('expanded')) {
        card.classList.remove('expanded');
        details.style.display = 'none';
    } else {
        card.classList.add('expanded');
        details.style.display = 'block';
    }
}

/**
 * Expand or collapse all visible repo cards.
 * Cards hidden by filters are skipped.
 */
function toggleAll(expand) {
    document.querySelectorAll('.repo-card').forEach(card => {
        if (getComputedStyle(card).display === 'none') return;
        const details = card.querySelector('.repo-card-details');
        if (expand) {
            card.classList.add('expanded');
            details.style.display = 'block';
        } else {
            card.classList.remove('expanded');
            details.style.display = 'none';
        }
    });
}

/* Keyboard shortcut: 'e' to expand all, 'c' to collapse all */
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'e') toggleAll(true);
    if (e.key === 'c') toggleAll(false);
});

/**
 * Wire filter toggle switches to CSS class mutations on the repo grid.
 * Each entry maps a checkbox ID to the CSS class toggled on #repo-grid.
 * CSS rules use that class + data attributes on cards to show/hide.
 */
const FILTERS = [
    ['filter-divergence', 'filter-has-divergence'],
    ['filter-all-clear',  'filter-all-clear'],
];

function initFilters() {
    const grid = document.getElementById('repo-grid');
    if (!grid) return;

    for (const [id, cls] of FILTERS) {
        const cb = document.getElementById(id);
        if (cb) {
            cb.addEventListener('change', () => grid.classList.toggle(cls, cb.checked));
        }
    }
}

document.addEventListener('DOMContentLoaded', initFilters);
```

## How it works

The data flow is clean and layered:

## How it works

The data flow is clean and layered:

    Jinja2 template renders data attributes on each card
      → data-has-divergence="true|false"
      → data-all-clear="true|false"

    User clicks toggle
      → checkbox.checked flips (native browser behavior)
      → JS change listener fires
      → grid.classList.toggle('filter-has-divergence', checked)

    CSS engine responds
      → .repo-grid.filter-has-divergence .repo-card[data-has-divergence="false"] { display: none }
      → Single style recalculation pass — no JS loop over cards

No Python files were modified. The existing `AttentionSignals` model already exposed all needed data (`branches_ahead_count`, `branches_behind_count`, `all_clear`).

## Quality review fixes

Five issues were identified and fixed during code review:

1. **CSS ordering** — Filter sections moved before the `@media` responsive block
2. **Design tokens** — Hard-coded `#fff` replaced with `var(--text)` for toggle thumb
3. **Accessibility** — Removed redundant `for` attributes on wrapping `<label>` elements
4. **Filter interaction** — `toggleAll` now uses `getComputedStyle` to skip hidden cards
5. **DRY** — Duplicate listener blocks refactored to a data-driven `FILTERS` table
