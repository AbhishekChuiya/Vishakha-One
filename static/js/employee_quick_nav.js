(function(){
'use strict';
document.addEventListener('DOMContentLoaded',function(){
 const overlay=document.getElementById('quick-nav-overlay');
 const input=document.getElementById('quick-nav-input');
 const results=document.getElementById('quick-nav-results');
 const launch=document.getElementById('quick-nav-launch');
 const closeBtn=document.getElementById('quick-nav-close');
 if(!overlay||!input||!results||!launch)return;
 const sidebarLinks=Array.from(document.querySelectorAll('.sidebar .nav-link'));
 const appLink=sidebarLinks.find(a=>/\/apps\/?(?:\?|$)/.test(a.getAttribute('href')||''))||sidebarLinks.find(a=>/apps/i.test(a.textContent));
 const appsUrl=appLink?appLink.href:null;
 const entries=[];
 const unique=new Set();
 let current=0, trigger=null, loading=false, fetched=false;
 function add(label,url,kind,enabled=true){
   label=(label||'').trim(); if(!label||!url)return;
   const key=kind+'|'+label.toLowerCase();if(unique.has(key))return;unique.add(key);
   entries.push({label,url,kind,enabled});
 }
 sidebarLinks.forEach(a=>add(a.textContent.trim(),a.href,'Page'));
 document.querySelectorAll('.desktop-bookmarks a').forEach(a=>add(a.textContent.trim(),a.href,'Bookmark'));
 function collectApps(doc){
   doc.querySelectorAll('#app-grid .app-card').forEach(a=>{
     const name=a.querySelector('.app-meta strong')?.textContent?.trim()||a.dataset.name||'';
     const category=a.querySelector('.app-meta small')?.textContent?.trim()||'';
     const enabled=!a.hasAttribute('data-unconfigured')&&a.getAttribute('href')!=='#';
     add(name,enabled?a.href:(appsUrl||'#'),'Application',enabled);
     const e=entries[entries.length-1];if(e&&e.label===name&&e.kind==='Application')e.category=category;
   });
 }
 collectApps(document);
 async function loadApps(){
   if(fetched||loading||!appsUrl)return;
   loading=true;
   try{
     const response=await fetch(appsUrl,{credentials:'same-origin',headers:{'X-Requested-With':'XMLHttpRequest'}});
     if(!response.ok)throw new Error('Application directory unavailable');
     const html=await response.text();
     const parsed=new DOMParser().parseFromString(html,'text/html');
     collectApps(parsed);
     fetched=true;
   }catch(e){/* Page navigation remains available when offline. */}
   finally{loading=false;if(!overlay.hidden)render();}
 }
 function matched(){
   const q=input.value.toLocaleLowerCase().trim();
   return entries.filter(e=>!q||[e.label,e.category||'',e.kind].join(' ').toLocaleLowerCase().includes(q))
     .sort((a,b)=>{
       if(!q)return ({Page:0,Bookmark:1,Application:2}[a.kind]||3)-({Page:0,Bookmark:1,Application:2}[b.kind]||3);
       const as=a.label.toLowerCase().startsWith(q)?0:1,bs=b.label.toLowerCase().startsWith(q)?0:1;
       return as-bs||a.label.localeCompare(b.label);
     }).slice(0,40);
 }
 function render(){
   const list=matched();results.replaceChildren();current=Math.max(0,Math.min(current,list.length-1));
   if(!list.length){const p=document.createElement('p');p.className='quick-nav-empty';p.textContent=loading?'Loading applications…':'No matching results';results.append(p);return;}
   list.forEach((e,i)=>{
     const el=document.createElement('button');el.type='button';el.className='quick-nav-result';el.setAttribute('role','option');
     el.setAttribute('aria-selected',String(i===current));el.dataset.index=String(i);
     if(!e.enabled)el.classList.add('quick-nav-unconfigured');
     const name=document.createElement('span');name.className='quick-nav-result-name';name.textContent=e.label;
     const detail=document.createElement('span');detail.className='quick-nav-result-kind';detail.textContent=e.enabled?e.kind:'Not configured';
     el.append(name,detail);el.addEventListener('click',()=>openResult(e));
     el.addEventListener('mouseenter',()=>select(i));results.append(el);
   });
 }
 function select(i){current=i;results.querySelectorAll('.quick-nav-result').forEach((el,j)=>el.setAttribute('aria-selected',String(j===i)));results.children[i]?.scrollIntoView({block:'nearest'});}
 function openResult(e){
   if(!e.enabled){input.value=e.label;render();return;}
   hide();
   if(e.kind==='Application')window.open(e.url,'_blank','noopener,noreferrer');
   else window.location.assign(e.url);
 }
 function show(){
   if(!overlay.hidden)return;
   trigger=document.activeElement;overlay.hidden=false;document.body.classList.add('quick-nav-open');
   input.value='';current=0;render();input.focus();loadApps();
 }
 function hide(){overlay.hidden=true;document.body.classList.remove('quick-nav-open');trigger?.focus?.();}
 launch.addEventListener('click',show);closeBtn?.addEventListener('click',hide);
 overlay.addEventListener('click',e=>{if(e.target===overlay)hide();});
 input.addEventListener('input',()=>{current=0;render();});
 document.addEventListener('keydown',e=>{
   if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();overlay.hidden?show():hide();return;}
   if(overlay.hidden)return;
   if(e.key==='Escape'){e.preventDefault();hide();}
   else if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();const n=matched().length;if(n)select((current+(e.key==='ArrowDown'?1:-1)+n)%n);}
   else if(e.key==='Enter'){e.preventDefault();const e0=matched()[current];if(e0)openResult(e0);}
   else if(e.key==='Tab'){
     const focusables=[input,closeBtn,...results.querySelectorAll('button')].filter(Boolean);
     const idx=focusables.indexOf(document.activeElement);const next=focusables[(idx+(e.shiftKey?-1:1)+focusables.length)%focusables.length];
     if(next){e.preventDefault();next.focus();}
   }
 });
});
})();
