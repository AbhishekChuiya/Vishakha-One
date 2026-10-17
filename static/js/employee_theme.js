document.addEventListener('DOMContentLoaded', function () {
  const root = document.documentElement;
  const buttons = Array.from(document.querySelectorAll('[data-theme-toggle]'));
  function update(theme) {
    const dark = theme === 'dark';
    root.dataset.theme = dark ? 'dark' : 'light';
    buttons.forEach(button => {
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
      const label = button.querySelector('[data-theme-label]');
      if (label) label.textContent = dark ? 'Light mode' : 'Dark mode';
      const icon = button.querySelector('use');
      if (icon) icon.setAttribute('href', dark ? '#vicon-sun' : '#vicon-moon');
    });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#192638' : '#10263f');
  }
  update(root.dataset.theme);
  buttons.forEach(button => button.addEventListener('click', function () {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    update(next);
    try { localStorage.setItem('vishakha_one_theme', next); } catch (e) {}
  }));
});
