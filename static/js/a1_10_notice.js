/* A1.10: single notice-dismiss handler, no navigation, no duplicate submit listeners. */
(() => {
 'use strict';
 document.addEventListener('DOMContentLoaded', () => {
   const section = document.getElementById('vone-notice-section');
   if (!section) return;
   section.addEventListener('click', (event) => {
     const button = event.target.closest('.vone-notice-modern-close');
     if (!button || !section.contains(button)) return;
     event.stopPropagation();
   }, true);
   section.addEventListener('submit', async (event) => {
     const form = event.target.closest('.vone-notice-read-form, form[data-dismiss-notice]');
     if (!form || !section.contains(form)) return;
     event.preventDefault();
     event.stopImmediatePropagation();
     const button = form.querySelector('button[type="submit"]');
     if (button) button.disabled = true;
     try {
       const response = await fetch(form.action, {
         method: 'POST', body: new FormData(form), credentials: 'same-origin',
         headers: {'X-Requested-With':'XMLHttpRequest','Accept':'application/json'},
         redirect:'follow', cache:'no-store'
       });
       if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json'))
         throw new Error('Unexpected response: '+response.status+' '+response.url);
       const data = await response.json();
       if (!data.ok) throw new Error('Dismissal not acknowledged');
       form.closest('.vone-notice-modern-item')?.remove();
       if (!section.querySelector('.vone-notice-modern-item')) section.remove();
       document.dispatchEvent(new Event('vone:notice-read'));
       window.dispatchEvent(new Event('focus')); // refresh bell count
     } catch (err) {
       console.warn('Notice dismissal failed', err);
       alert('Unable to dismiss notice. Refresh the page and try again.');
     } finally { if (button) button.disabled = false; }
   }, true);
 });
})();
