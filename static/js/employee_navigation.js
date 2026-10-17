/* Step 16.10 – accessible search clear and back-to-top. */
document.addEventListener('DOMContentLoaded', function () {
  const search = document.getElementById('global-search');
  const clear = document.getElementById('search-clear');
  if (search && clear) {
    const refresh = () => { clear.hidden = !search.value; };
    refresh();
    search.addEventListener('input', refresh);
    clear.addEventListener('click', function () {
      search.value = '';
      refresh();
      search.focus();
      // On a filtered Apps page, clear the query and restore the full list.
      if (new URLSearchParams(window.location.search).has('q')) {
        const url = new URL(window.location.href);
        url.searchParams.delete('q');
        window.location.assign(url.pathname + url.search + url.hash);
      }
    });
    search.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && search.value) {
        event.preventDefault();
        clear.click();
      }
    });
  }
  const top = document.getElementById('back-to-top');
  if (top) {
    const refreshTop = () => { top.hidden = window.scrollY < 420; };
    refreshTop();
    window.addEventListener('scroll', refreshTop, { passive: true });
    top.addEventListener('click', () => window.scrollTo({top:0,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'}));
  }
});
