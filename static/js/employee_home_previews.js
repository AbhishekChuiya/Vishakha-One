/* Step 16.36: reliable media previews, no iframe to localhost. */
(function(){
'use strict';
document.addEventListener('DOMContentLoaded',function(){
 const railButtons=document.querySelectorAll('[data-rail-prev],[data-rail-next]');
 railButtons.forEach(btn=>btn.addEventListener('click',()=>{
   const key=btn.dataset.railPrev||btn.dataset.railNext;
   const rail=Array.from(document.querySelectorAll('[data-preview-rail]')).find(el=>el.dataset.previewRail===key);
   if(!rail)return;
   const step=Math.max(220,Math.round(rail.clientWidth*.82));
   rail.scrollBy({left:btn.hasAttribute('data-rail-prev')?-step:step,behavior:'smooth'});
 }));
 const triggers=Array.from(document.querySelectorAll('[data-preview-image],[data-preview-resource]'));
 if(!triggers.length)return;
 const modal=document.createElement('div');modal.className='vone-preview-dialog';modal.hidden=true;
 modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.setAttribute('aria-label','Media preview');
 const shell=document.createElement('div');shell.className='vone-preview-shell';
 const bar=document.createElement('div');bar.className='vone-preview-toolbar';
 const title=document.createElement('strong');const nav=document.createElement('div');nav.className='vone-preview-nav';
 const prev=document.createElement('button');prev.type='button';prev.textContent='←';prev.setAttribute('aria-label','Previous photo');
 const next=document.createElement('button');next.type='button';next.textContent='→';next.setAttribute('aria-label','Next photo');
 const close=document.createElement('button');close.type='button';close.textContent='Close ✕';
 nav.append(prev,next,close);bar.append(title,nav);
 const stage=document.createElement('div');stage.className='vone-preview-stage';
 const footer=document.createElement('div');footer.className='vone-preview-toolbar';
 const help=document.createElement('span');help.textContent='Esc to close · Images fit to screen';
 const link=document.createElement('a');link.target='_blank';link.rel='noopener noreferrer';link.textContent='Open original ↗';
 footer.append(help,link);shell.append(bar,stage,footer);modal.append(shell);document.body.append(modal);
 let current=null,previousFocus=null;
 const photos=triggers.filter(el=>el.hasAttribute('data-preview-image'));
 function imageUrl(url){
   try{return /\.(png|jpe?g|webp|gif|avif|bmp)$/i.test(new URL(url,location.href).pathname);}
   catch(_){return false;}
 }
 function displayImage(src,alt){
   const img=document.createElement('img');img.src=src;img.alt=alt;
   img.addEventListener('error',()=>{stage.replaceChildren();const p=document.createElement('p');p.className='vone-preview-error';p.textContent='This image could not be loaded. Check that the media URL is accessible from your device.';stage.append(p);});
   stage.append(img);
 }
 function show(el){
   current=el;stage.replaceChildren();
   const url=el.dataset.previewImage||el.dataset.previewResource||'';
   const cover=el.dataset.previewCover||'';
   title.textContent=el.dataset.previewTitle||'Preview';
   const photo=el.hasAttribute('data-preview-image');
   prev.hidden=next.hidden=!photo||photos.length<2;
   link.hidden=!url; if(url)link.href=url;
   if(photo||imageUrl(url)){displayImage(photo?url:url,title.textContent);}
   else if(cover){displayImage(cover,title.textContent+' cover');}
   else{
     const info=document.createElement('p');info.className='vone-preview-error';
     info.textContent='No preview image is available. Upload a cover image in Content Manager, or open the original document.';
     stage.append(info);
   }
   modal.hidden=false;document.body.classList.add('vone-preview-open');close.focus();
 }
 function dismiss(){
   if(modal.hidden)return;
   modal.hidden=true;stage.replaceChildren();document.body.classList.remove('vone-preview-open');
   previousFocus?.focus();current=null;
 }
 triggers.forEach(el=>el.addEventListener('click',()=>{previousFocus=document.activeElement;show(el);}));
 close.addEventListener('click',dismiss);
 modal.addEventListener('click',e=>{if(e.target===modal)dismiss();});
 function shift(delta){
   const idx=photos.indexOf(current);if(idx<0)return;
   show(photos[(idx+delta+photos.length)%photos.length]);
 }
 prev.addEventListener('click',()=>shift(-1));next.addEventListener('click',()=>shift(1));
 document.addEventListener('keydown',e=>{
   if(modal.hidden)return;
   if(e.key==='Escape'){e.preventDefault();dismiss();}
   else if(e.key==='ArrowLeft'&&photos.includes(current)){e.preventDefault();shift(-1);}
   else if(e.key==='ArrowRight'&&photos.includes(current)){e.preventDefault();shift(1);}
   else if(e.key==='Tab'){
     const focusable=[prev,next,close,link].filter(x=>!x.hidden);
     const first=focusable[0],last=focusable[focusable.length-1];
     if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
     else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
   }
 });
});
})();
