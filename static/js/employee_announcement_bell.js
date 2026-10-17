(()=>{'use strict';document.addEventListener('DOMContentLoaded',()=>{
const bell=document.getElementById('notification-toggle'),menu=document.getElementById('notification-menu');if(!bell||!menu)return;
let link=menu.querySelector('.vone-company-bell-link');if(!link){link=document.createElement('a');link.className='vone-company-bell-link';link.href='/notifications/';menu.appendChild(link);}
const indicator=document.createElement('span');indicator.className='vone-company-unread-count';indicator.setAttribute('aria-hidden','true');indicator.hidden=true;bell.appendChild(indicator);
let busy=false,previous=null;
async function refresh(){if(busy||document.hidden)return;busy=true;try{
const response=await fetch('/notifications/feed/',{credentials:'same-origin',cache:'no-store',headers:{Accept:'application/json'}});
if(!response.ok||!(response.headers.get('content-type')||'').includes('application/json'))return;
const data=await response.json();const n=Math.max(0,Math.floor(Number(data.unread_count)||0));
link.textContent=n?`Company announcements · ${n} unread →`:'Company announcements →';
bell.classList.toggle('vone-bell-unread',n>0);bell.setAttribute('aria-label',n?`View notifications, ${n} unread company announcements`:'View notifications');
indicator.textContent=n>99?'99+':n?String(n):'';indicator.hidden=n===0;
if(previous!==null&&n>previous)bell.classList.add('vone-bell-new-update');else bell.classList.remove('vone-bell-new-update');previous=n;
}catch(_){/* Network interruptions do not block the portal. */}finally{busy=false;}}
bell.addEventListener('click',()=>{bell.classList.remove('vone-bell-new-update');refresh();});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});window.addEventListener('focus',refresh);
window.setInterval(refresh,60000);refresh();
});})();
