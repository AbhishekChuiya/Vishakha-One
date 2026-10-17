/* Vishakha One PWA install flow: secure origins only; no auto prompts. */
(() => {
  'use strict';
  if (!('serviceWorker' in navigator) || !window.isSecureContext) return;
  navigator.serviceWorker.register('/service-worker.js', {scope: '/'})
    .catch(error => console.warn('Vishakha One PWA registration failed:', error));
  let deferredPrompt = null;
  const installButton = document.getElementById('vone-pwa-install');
  const instructions = document.getElementById('vone-pwa-ios-help');
  if (!installButton) return;
  const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  if (standalone) return;
  const isiOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (isiOS) {
    installButton.hidden = false;
    installButton.textContent = 'Add to Home Screen';
    installButton.addEventListener('click', () => {
      if (instructions) instructions.hidden = !instructions.hidden;
    });
  }
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferredPrompt = event;
    installButton.hidden = false;
  });
  installButton.addEventListener('click', async () => {
    if (!deferredPrompt) return;
    const prompt = deferredPrompt;
    deferredPrompt = null;
    installButton.hidden = true;
    try { await prompt.prompt(); } catch (error) { console.warn('PWA prompt failed:', error); }
  });
  window.addEventListener('appinstalled', () => {
    installButton.hidden = true;
    if (instructions) instructions.hidden = true;
  });
})();
