/* Vishakha One Step 16.16: Home dashboard favorite shortcuts.
   Uses the existing favorites key; no backend or external data calls. */
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    const section = document.querySelector('.apps-section');
    const grid = section?.querySelector('.app-grid');
    // Homepage only: the Apps directory has its own filters and Recently Used section.
    if (!section || !grid || document.querySelector('.app-directory-tools')) return;
    const cards = Array.from(grid.querySelectorAll('.app-card[data-name]'));
    if (!cards.length) return;
    const KEY = 'vishakha_one_favorites_v1';
    const wrapper = document.createElement('section');
    wrapper.className = 'favorite-shortcuts';
    wrapper.setAttribute('aria-labelledby', 'favorite-shortcuts-title');
    wrapper.hidden = true;
    const head = document.createElement('div');
    head.className = 'favorite-shortcuts-heading';
    const title = document.createElement('h3');
    title.id = 'favorite-shortcuts-title';
    title.textContent = 'Your favorite applications';
    const note = document.createElement('span');
    note.textContent = 'Quick launch';
    head.append(title, note);
    const track = document.createElement('div');
    track.className = 'favorite-shortcuts-track';
    wrapper.append(head, track);
    section.insertBefore(wrapper, section.querySelector('.app-toolbar') || grid);

    function savedFavorites() {
      try {
        const list = JSON.parse(localStorage.getItem(KEY) || '[]');
        return Array.isArray(list) ? list.filter(x => typeof x === 'string') : [];
      } catch (_) { return []; }
    }
    function render() {
      const names = new Set(savedFavorites());
      track.replaceChildren();
      cards.filter(card => names.has(card.querySelector('[data-favorite]')?.dataset.favorite))
        .slice(0, 8).forEach(card => {
          const shortcut = document.createElement('a');
          shortcut.className = 'favorite-shortcut';
          const configured = card.dataset.unconfigured !== 'true' && card.getAttribute('href') !== '#';
          shortcut.href = configured ? card.getAttribute('href') : '#';
          if (configured && card.target === '_blank') {
            shortcut.target = '_blank';
            shortcut.rel = 'noopener noreferrer';
          } else if (!configured) {
            shortcut.dataset.unconfigured = 'true';
          }
          const icon = document.createElement('span');
          icon.className = 'favorite-shortcut-icon';
          const originalImg = card.querySelector('.app-icon-wrap img');
          if (originalImg) {
            const img = document.createElement('img');
            img.src = originalImg.getAttribute('src');
            img.alt = '';
            img.loading = 'lazy';
            icon.append(img);
          } else {
            icon.textContent = card.querySelector('.app-initial')?.textContent || '◻';
          }
          const label = document.createElement('span');
          label.className = 'favorite-shortcut-name';
          label.textContent = card.querySelector('.app-meta strong')?.textContent || 'Application';
          shortcut.append(icon, label);
          track.append(shortcut);
        });
      wrapper.hidden = track.childElementCount === 0;
    }
    render();
    // The existing favorite toggle writes localStorage during its click handler.
    grid.addEventListener('click', function (e) {
      if (e.target.closest('.favorite-toggle')) setTimeout(render, 0);
    });
    window.addEventListener('storage', function (e) {
      if (e.key === KEY) render();
    });
    window.addEventListener('pageshow', render);
  });
})();
