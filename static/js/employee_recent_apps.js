document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('app-grid');
  const section = document.getElementById('recent-apps');
  const list = document.getElementById('recent-apps-list');
  const clear = document.getElementById('recent-apps-clear');
  if (!grid || !section || !list) return;
  const KEY = 'vishakha_one_recent_apps_v1';
  const LIMIT = 5;
  function read() {
    try {
      const data = JSON.parse(localStorage.getItem(KEY) || '[]');
      return Array.isArray(data) ? data.filter(x => typeof x === 'string').slice(0,LIMIT) : [];
    } catch (_) { return []; }
  }
  function write(items) { try { localStorage.setItem(KEY, JSON.stringify(items)); } catch (_) {} }
  function appCards() { return [...grid.querySelectorAll('.app-card')]; }
  function cardName(card) { return (card.querySelector('.app-meta strong')?.textContent || '').trim(); }
  function render() {
    list.replaceChildren();
    const cards = appCards();
    const matches = read().map(name => cards.find(card => cardName(card) === name && card.hasAttribute('href') && !card.hasAttribute('data-unconfigured'))).filter(Boolean);
    section.hidden = matches.length === 0;
    for (const card of matches) {
      const link = document.createElement('a');
      link.className = 'recent-app-link';
      link.href = card.getAttribute('href');
      if (card.target === '_blank') { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
      const icon = card.querySelector('.app-icon-wrap');
      const avatar = document.createElement('span');
      avatar.className = 'recent-app-icon';
      if (icon) avatar.appendChild(icon.cloneNode(true));
      const label = document.createElement('span');
      label.textContent = cardName(card);
      link.append(avatar,label);
      link.addEventListener('click', () => record(card));
      list.appendChild(link);
    }
  }
  function record(card) {
    if (card.hasAttribute('data-unconfigured') || !card.getAttribute('href') || card.getAttribute('href') === '#') return;
    const name = cardName(card);
    if (!name) return;
    write([name,...read().filter(x => x !== name)].slice(0,LIMIT));
    render();
  }
  grid.addEventListener('click', event => {
    const card = event.target.closest('.app-card');
    if (!card || event.target.closest('.favorite-toggle')) return;
    record(card);
  });
  clear?.addEventListener('click', () => { write([]); render(); });
  render();
});
