/* Step 16.14: Works with existing search, category and favorites filters. */
document.addEventListener('DOMContentLoaded', function () {
  const grid = document.getElementById('app-grid');
  const sort = document.getElementById('app-sort');
  const status = document.getElementById('app-results-count');
  const reset = document.getElementById('app-reset-filters');
  if (!grid || !sort || !status || !reset) return;
  const cards = Array.from(grid.querySelectorAll('.app-card'));
  const original = new Map(cards.map((card, i) => [card, i]));
  const search = document.getElementById('app-filter');
  const favorite = document.querySelector('.favorites-filter');
  const categories = document.getElementById('app-category-options');
  const empty = document.getElementById('apps-empty');
  const name = card => (card.dataset.name || card.querySelector('.app-meta strong')?.textContent || '').trim();
  function reorder() {
    const sorted = cards.slice().sort((a,b) => {
      if (sort.value === 'default') return original.get(a) - original.get(b);
      const cmp = name(a).localeCompare(name(b), undefined, {numeric:true, sensitivity:'base'});
      return sort.value === 'za' ? -cmp : cmp;
    });
    sorted.forEach(card => grid.appendChild(card));
    refresh();
  }
  function refresh() {
    const count = cards.filter(card => !card.hidden && !card.classList.contains('category-filtered-out') && getComputedStyle(card).display !== 'none').length;
    status.textContent = `${count} of ${cards.length} application${cards.length === 1 ? '' : 's'} shown`;
    if (empty) empty.hidden = count !== 0;
  }
  sort.addEventListener('change', reorder);
  reset.addEventListener('click', function () {
    if (search) {
      search.value = '';
      search.dispatchEvent(new Event('input', {bubbles:true}));
    }
    if (favorite && favorite.getAttribute('aria-pressed') === 'true') favorite.click();
    const all = categories?.querySelector('[data-category-value=""]');
    if (all && all.getAttribute('aria-pressed') !== 'true') all.click();
    sort.value = 'default';
    reorder();
    queueMicrotask(refresh);
  });
  const observer = new MutationObserver(() => queueMicrotask(refresh));
  cards.forEach(card => observer.observe(card, {attributes:true, attributeFilter:['hidden','class','style']}));
  categories && observer.observe(categories, {subtree:true, attributes:true, attributeFilter:['aria-pressed']});
  search?.addEventListener('input', () => queueMicrotask(refresh));
  favorite?.addEventListener('click', () => queueMicrotask(refresh));
  reorder();
});
