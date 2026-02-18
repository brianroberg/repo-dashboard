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
