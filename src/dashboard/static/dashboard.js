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
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
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

/**
 * Sort option registry.
 * key:        matches <option value="..."> in the sort-field select
 * extract:    reads a data attribute from a card, returns a comparable value
 * defaultDir: initial direction when this option is first selected
 *
 * To add a new sort option:
 *   1. Add a <option value="my-key"> to #sort-field in dashboard_content.html
 *   2. Add a data-sort-my-key attribute to .repo-card in repo_card.html
 *   3. Add one entry here.
 */
const SORT_OPTIONS = [
    {
        key: 'name',
        extract: card => card.dataset.sortName || '',
        defaultDir: 'asc',
    },
    {
        key: 'pushed-at',
        extract: card => card.dataset.sortPushedAt || '',
        defaultDir: 'desc',
    },
    {
        key: 'commit-count',
        extract: card => parseInt(card.dataset.sortCommitCount || '0', 10),
        defaultDir: 'desc',
    },
];

/**
 * Re-order .repo-card elements inside #repo-grid.
 * Uses appendChild to move nodes — preserves event listeners and expanded state.
 */
function applySort() {
    const grid = document.getElementById('repo-grid');
    const fieldEl = document.getElementById('sort-field');
    const dirBtn = document.getElementById('sort-dir');
    if (!grid || !fieldEl || !dirBtn) return;

    const option = SORT_OPTIONS.find(o => o.key === fieldEl.value);
    if (!option) return;

    const dir = dirBtn.dataset.dir || 'asc';
    const cards = Array.from(grid.querySelectorAll('.repo-card'));

    cards.sort((a, b) => {
        const av = option.extract(a);
        const bv = option.extract(b);
        let cmp;
        if (typeof av === 'number') {
            cmp = av - bv;
        } else {
            // Empty values always sort last regardless of direction
            if (av === '' && bv === '') return 0;
            if (av === '') return 1;
            if (bv === '') return -1;
            cmp = av.localeCompare(bv);
        }
        return dir === 'asc' ? cmp : -cmp;
    });

    for (const card of cards) {
        grid.appendChild(card);
    }
}

function setSortDir(btn, dir) {
    btn.dataset.dir = dir;
    const isAsc = dir === 'asc';
    btn.querySelector('.sort-dir-icon').textContent = isAsc ? '\u2191' : '\u2193';
    btn.querySelector('.sort-dir-text').textContent = isAsc ? 'Asc' : 'Desc';
    btn.setAttribute('aria-label', isAsc ? 'Sort ascending' : 'Sort descending');
}

function initSort() {
    const fieldEl = document.getElementById('sort-field');
    const dirBtn = document.getElementById('sort-dir');
    if (!fieldEl || !dirBtn) return;
    if (fieldEl.dataset.sortInit) return;  // already initialized
    fieldEl.dataset.sortInit = 'true';

    fieldEl.addEventListener('change', () => {
        const option = SORT_OPTIONS.find(o => o.key === fieldEl.value);
        if (option) setSortDir(dirBtn, option.defaultDir);
        applySort();
    });

    dirBtn.addEventListener('click', () => {
        const current = dirBtn.dataset.dir || 'asc';
        setSortDir(dirBtn, current === 'asc' ? 'desc' : 'asc');
        applySort();
    });

    fieldEl.value = 'name';
    setSortDir(dirBtn, 'asc');
    applySort();
}

document.addEventListener('DOMContentLoaded', initSort);
