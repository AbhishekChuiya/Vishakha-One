document.addEventListener('DOMContentLoaded', () => {
  const panel = document.getElementById('chat-panel');
  const input = document.getElementById('chat-input');
  const chatBody = document.getElementById('chat-body');
  const closeChat = () => { panel.classList.remove('open'); panel.setAttribute('aria-hidden','true'); };
  document.querySelectorAll('[data-open-ai]').forEach(button => button.addEventListener('click', () => { panel.classList.add('open'); panel.setAttribute('aria-hidden','false'); input.focus(); }));
  document.getElementById('close-chat')?.addEventListener('click', closeChat);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeChat(); closeMenu(); } });
  const sidebar = document.getElementById('sidebar');
  const scrim = document.getElementById('sidebar-scrim');
  const menu = document.getElementById('menu-toggle');
  const closeMenu = () => { sidebar.classList.remove('open'); scrim.classList.remove('show'); menu?.setAttribute('aria-expanded','false'); document.body.classList.remove('sidebar-is-open'); };
  menu?.addEventListener('click', () => { const open = sidebar.classList.toggle('open'); scrim.classList.toggle('show',open); menu.setAttribute('aria-expanded',String(open)); document.body.classList.toggle('sidebar-is-open',open); });
  scrim?.addEventListener('click', closeMenu);
  const date = document.getElementById('today-date');
  if (date) date.textContent = new Intl.DateTimeFormat('en-IN',{weekday:'short',day:'numeric',month:'long',year:'numeric'}).format(new Date());
  const filter = document.getElementById('app-filter');
  filter?.addEventListener('input', () => { const q=filter.value.toLowerCase().trim(); let visible=0; document.querySelectorAll('#app-grid .app-card').forEach(card => { const match=(card.dataset.name+' '+card.dataset.category).includes(q); card.hidden=!match; if(match) visible++; }); const empty=document.getElementById('apps-empty'); if(empty) empty.hidden=visible!==0; });
  document.querySelectorAll('[data-unconfigured]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); alert('This application link has not yet been configured.'); }));
  document.querySelectorAll('[data-prompt]').forEach(button => button.addEventListener('click', () => { input.value=button.dataset.prompt; input.focus(); }));
  document.getElementById('chat-form')?.addEventListener('submit', event => { event.preventDefault(); const value=input.value.trim(); if(!value)return; const user=document.createElement('div'); user.className='bubble user'; user.textContent=value; chatBody.appendChild(user); const response=document.createElement('div'); response.className='bubble'; response.textContent='This is a preview of Vishakha AI. We will connect the existing Darpan AI backend in a later step.'; chatBody.appendChild(response); input.value=''; chatBody.scrollTop=chatBody.scrollHeight; });
});


// UI-only enhancements; AI remains in preview mode.
document.addEventListener('DOMContentLoaded', () => {
  const favoritesKey = 'vishakha_one_favorites_v1';
  let favorites = [];
  try { favorites = JSON.parse(localStorage.getItem(favoritesKey) || '[]'); if (!Array.isArray(favorites)) favorites = []; } catch (_) { favorites = []; }
  const buttons = [...document.querySelectorAll('.favorite-toggle')];
  const filterButton = document.querySelector('.favorites-filter');
  const search = document.getElementById('app-filter');
  const empty = document.getElementById('apps-empty');
  function updateApps() {
    const query = (search?.value || '').trim().toLowerCase();
    const onlyFavorites = filterButton?.getAttribute('aria-pressed') === 'true';
    let visible = 0;
    document.querySelectorAll('#app-grid .app-card').forEach(card => {
      const name = card.querySelector('[data-favorite]')?.dataset.favorite;
      const text = `${card.dataset.name || ''} ${card.dataset.category || ''}`;
      const match = text.includes(query) && (!onlyFavorites || favorites.includes(name));
      card.hidden = !match;
      if (match) visible++;
    });
    if (empty) { empty.hidden = visible !== 0; if (!visible) empty.textContent = onlyFavorites ? 'No favorite applications match your search.' : 'No applications match your search.'; }
  }
  buttons.forEach(button => {
    const name = button.dataset.favorite;
    function sync() { const selected = favorites.includes(name); button.setAttribute('aria-pressed', String(selected)); button.textContent = selected ? '★' : '☆'; button.title = selected ? 'Remove from favorites' : 'Add to favorites'; }
    sync();
    button.addEventListener('click', event => {
      event.preventDefault(); event.stopPropagation();
      favorites = favorites.includes(name) ? favorites.filter(x => x !== name) : [...favorites, name];
      try { localStorage.setItem(favoritesKey, JSON.stringify(favorites)); } catch (_) {}
      buttons.forEach(b => { if (b.dataset.favorite === name) { const selected = favorites.includes(name); b.setAttribute('aria-pressed', String(selected)); b.textContent = selected ? '★' : '☆'; } });
      updateApps();
    });
  });
  search?.addEventListener('input', updateApps);
  filterButton?.addEventListener('click', () => { const pressed = filterButton.getAttribute('aria-pressed') === 'true'; filterButton.setAttribute('aria-pressed', String(!pressed)); updateApps(); });
  const profile = document.getElementById('profile-toggle');
  const profileMenu = document.getElementById('profile-menu');
  const notifications = document.getElementById('notification-toggle');
  const notificationMenu = document.getElementById('notification-menu');
  function closePopovers() { if (profileMenu) profileMenu.hidden = true; if (notificationMenu) notificationMenu.hidden = true; profile?.setAttribute('aria-expanded','false'); notifications?.setAttribute('aria-expanded','false'); }
  function toggle(button, menu) { if (!menu) return; const wasHidden = menu.hidden; closePopovers(); menu.hidden = !wasHidden; button?.setAttribute('aria-expanded',String(wasHidden)); }
  profile?.addEventListener('click', event => { event.stopPropagation(); toggle(profile,profileMenu); });
  notifications?.addEventListener('click', event => { event.stopPropagation(); toggle(notifications,notificationMenu); });
  [profileMenu,notificationMenu].forEach(menu => menu?.addEventListener('click',event => event.stopPropagation()));
  document.addEventListener('click',closePopovers);
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closePopovers(); if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); document.getElementById('global-search')?.focus(); } });
  updateApps();
});
