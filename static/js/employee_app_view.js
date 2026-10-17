/* Step 16.15 – layout choice is stored in this browser. */
document.addEventListener('DOMContentLoaded', function () {
  const grid = document.getElementById('app-grid');
  const gridButton = document.getElementById('app-view-grid');
  const listButton = document.getElementById('app-view-list');
  if (!grid || !gridButton || !listButton) return;
  const key = 'vishakha_one_app_view';
  function apply(view) {
    const list = view === 'list';
    grid.classList.toggle('app-list-view', list);
    gridButton.setAttribute('aria-pressed', String(!list));
    listButton.setAttribute('aria-pressed', String(list));
  }
  let initial = 'grid';
  try { if (localStorage.getItem(key) === 'list') initial = 'list'; } catch (e) {}
  apply(initial);
  function choose(view) {
    apply(view);
    try { localStorage.setItem(key, view); } catch (e) {}
  }
  gridButton.addEventListener('click', () => choose('grid'));
  listButton.addEventListener('click', () => choose('list'));
});
