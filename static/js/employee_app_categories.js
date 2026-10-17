document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('app-grid');
  const bar = document.getElementById('app-category-bar');
  const options = document.getElementById('app-category-options');
  if (!grid || !bar || !options) return;
  const cards = Array.from(grid.querySelectorAll('.app-card'));
  const search = document.getElementById('app-filter');
  const favorite = document.querySelector('.favorites-filter');
  const empty = document.getElementById('apps-empty');
  const counts = new Map();
  cards.forEach(card => {
    const name = (card.dataset.category || '').trim();
    if (name) counts.set(name, (counts.get(name) || 0) + 1);
  });
  if (counts.size < 2) return;
  let selected = '';
  function label(category) { return category.replace(/\b\w/g, x => x.toUpperCase()); }
  function addButton(value, caption, count) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'app-category-chip';
    button.dataset.categoryValue = value;
    button.setAttribute('aria-pressed', String(selected === value));
    button.textContent = `${caption} (${count})`;
    button.addEventListener('click', () => {
      selected = value;
      options.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
      apply();
    });
    options.appendChild(button);
  }
  addButton('', 'All', cards.length);
  Array.from(counts.entries()).sort((a,b) => a[0].localeCompare(b[0])).forEach(([name,count]) => addButton(name,label(name),count));
  bar.hidden = false;
  function apply() {
    let visible = 0;
    cards.forEach(card => {
      const matchesCategory = !selected || (card.dataset.category || '').trim() === selected;
      card.classList.toggle('category-filtered-out', !matchesCategory);
      // Preserve the portal's existing search and favorites visibility rules.
      if (matchesCategory && !card.hidden) visible++;
    });
    if (empty) {
      empty.hidden = visible > 0;
      if (!visible) empty.textContent = selected ? 'No applications match this category and your current filters.' : 'No applications match your search.';
    }
  }
  search?.addEventListener('input', () => queueMicrotask(apply));
  favorite?.addEventListener('click', () => queueMicrotask(apply));
  grid.addEventListener('click', e => { if (e.target.closest('.favorite-toggle')) queueMicrotask(apply); });
  apply();
});