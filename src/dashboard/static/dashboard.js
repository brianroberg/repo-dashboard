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
 * Expand or collapse all repo cards.
 */
function toggleAll(expand) {
    document.querySelectorAll('.repo-card').forEach(card => {
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
