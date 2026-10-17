/* Step 16.28: Notification center UI. No invented alerts or API calls.
   Real notification data can be passed as window.VishakhaOneNotifications,
   or as JSON in <script type="application/json" id="portal-notification-data">.
   Expected objects: {id, title, message, url, date, type}. */
(function(){'use strict';document.addEventListener('DOMContentLoaded',function(){
 const panel=document.getElementById('notification-menu');
 const trigger=document.getElementById('notification-toggle');
 if(!panel||!trigger)return;
 const list=panel.querySelector('#nc-items'),count=panel.querySelector('#nc-count');
 const allRead=panel.querySelector('#nc-read-all');
 const close=panel.querySelector('#nc-close');
 const tabs=Array.from(panel.querySelectorAll('[data-nc-filter]'));
 let filter='all';
 function source(){
  const tag=document.getElementById('portal-notification-data');
  let input=[];
  if(tag){try{input=JSON.parse(tag.textContent||'[]');}catch(_){}}
  else if(Array.isArray(window.VishakhaOneNotifications))input=window.VishakhaOneNotifications;
  if(!Array.isArray(input))return [];
  return input.filter(n=>n&&typeof n==='object'&&n.id!=null&&typeof n.title==='string')
   .slice(0,100).map(n=>({id:String(n.id),title:n.title,message:String(n.message||''),url:typeof n.url==='string'?n.url:'',date:String(n.date||''),type:String(n.type||'Update')}));
 }
 const notices=source();
 const storageKey='vishakha_one_notice_read_v1';
 let read=new Set();
 try{const saved=JSON.parse(localStorage.getItem(storageKey)||'[]');if(Array.isArray(saved))read=new Set(saved.map(String));}catch(_){}
 function persist(){try{localStorage.setItem(storageKey,JSON.stringify([...read].slice(-500)));}catch(_){}}
 function el(tag,cls,txt){const node=document.createElement(tag);if(cls)node.className=cls;if(txt!=null)node.textContent=txt;return node;}
 function render(){
  const unread=notices.filter(n=>!read.has(n.id)).length;
  count.textContent=notices.length?(unread+' unread · '+notices.length+' total'):'No new notifications';
  trigger.setAttribute('aria-label',unread?'View notifications, '+unread+' unread':'View notifications');
  trigger.classList.toggle('nc-has-unread',unread>0);
  let badge=trigger.querySelector('.nc-badge');
  if(unread&&!badge){badge=el('span','nc-badge');badge.setAttribute('aria-hidden','true');trigger.append(badge);}
  if(badge){badge.textContent=unread>9?'9+':String(unread);badge.hidden=unread===0;}
  allRead.disabled=unread===0;
  tabs.forEach(tab=>tab.setAttribute('aria-pressed',String(tab.dataset.ncFilter===filter)));
  list.replaceChildren();
  const shown=notices.filter(n=>filter==='all'||!read.has(n.id));
  if(!shown.length){const empty=el('div','nc-empty');empty.append(el('span','nc-empty-icon','✓'),el('strong','',filter==='unread'?'No unread notifications':"You're all caught up"),el('p','',filter==='unread'?'All notifications are marked as read.':'New portal notifications will appear here when available.'));list.append(empty);return;}
  shown.forEach(n=>{
   const item=el('article','nc-item'+(read.has(n.id)?' is-read':''));
   const main=el('div','nc-item-body');
   const meta=el('div','nc-item-meta');meta.append(el('span','nc-type',n.type),el('time','',n.date));
   const title=el('strong','nc-item-title',n.title);
   main.append(meta,title);
   if(n.message)main.append(el('p','',n.message));
   if(n.url&&(/^(https?:\/\/|\/)(?!\/)/i).test(n.url)){
    const link=el('a','nc-item-link','Open update →');link.href=n.url;main.append(link);
   }
   const button=el('button','nc-mark',read.has(n.id)?'Mark unread':'Mark read');button.type='button';
   button.setAttribute('aria-label',(read.has(n.id)?'Mark unread: ':'Mark read: ')+n.title);
   button.addEventListener('click',()=>{read.has(n.id)?read.delete(n.id):read.add(n.id);persist();render();});
   item.append(main,button);list.append(item);
  });
 }
 tabs.forEach(t=>t.addEventListener('click',()=>{filter=t.dataset.ncFilter;render();}));
 allRead.addEventListener('click',()=>{notices.forEach(n=>read.add(n.id));persist();render();});
 close.addEventListener('click',()=>{panel.hidden=true;trigger.setAttribute('aria-expanded','false');trigger.focus();});
 window.addEventListener('storage',e=>{if(e.key===storageKey){try{read=new Set(JSON.parse(e.newValue||'[]').map(String));}catch(_){}render();}});
 render();
});})();
