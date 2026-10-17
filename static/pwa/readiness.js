(()=>{'use strict';document.addEventListener('DOMContentLoaded',()=>{
const output=document.getElementById('pwa-check-results'),refresh=document.getElementById('pwa-check-refresh');
if(!output)return;
const row=(label,ok,detail)=>{const div=document.createElement('div');div.className='vone-pwa-check-row';const mark=document.createElement('strong');mark.textContent=(ok?'✓ ':'! ')+label;mark.className=ok?'vone-ok':'vone-warning';const p=document.createElement('p');p.textContent=detail;div.append(mark,p);return div;};
async function check(){
 output.replaceChildren();const secure=window.isSecureContext;
 output.append(row('Secure connection',secure,secure?'This origin is a secure context.':'Use a trusted HTTPS domain. HTTP LAN IP addresses do not qualify.'));
 const standalone=matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;
 output.append(row('Installed app mode',standalone,standalone?'You are using the installed app.':'This page is currently open in a browser.'));
 let manifestOk=false;
 try{const r=await fetch('/manifest.webmanifest',{cache:'no-store',credentials:'same-origin'});if(r.ok){const m=await r.json();manifestOk=!!(m.name&&m.start_url&&m.icons&&m.icons.length);}}
 catch(e){}
 output.append(row('App manifest',manifestOk,manifestOk?'App name, start URL and icons are available.':'Check /manifest.webmanifest and icon URLs.'));
 const swSupported='serviceWorker' in navigator;
 let swOk=false;
 if(swSupported&&secure){try{const r=await fetch('/service-worker.js',{cache:'no-store',credentials:'same-origin'});swOk=r.ok&&((r.headers.get('content-type')||'').includes('javascript'));}catch(e){}}
 output.append(row('Service worker',swOk,swOk?'Service worker endpoint is available.':!secure?'Requires HTTPS on mobile.':swSupported?'Check /service-worker.js.':'This browser does not support service workers.'));
 const mobile=/Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
 output.append(row('Install guidance',true,mobile?'Use your mobile browser menu after all checks pass.':'Use the browser Install app menu. For mobile, open the HTTPS site on your phone.'));
}
refresh?.addEventListener('click',check);check();
});})();
