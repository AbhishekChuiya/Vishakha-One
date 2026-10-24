(function(){
'use strict';
document.addEventListener('DOMContentLoaded',function(){
  // Homepage: progressive application reveal, with search and favorites left functional.
  const grid=document.querySelector('#app-grid[data-home-app-grid]');
  const more=document.getElementById('vone-app-load-more');
  if(grid&&more){
    let limit=window.matchMedia('(max-width: 767px)').matches?4:6;
    let step=window.matchMedia('(max-width: 767px)').matches?4:6;
    const cards=Array.from(grid.querySelectorAll('.app-card'));
    const search=document.getElementById('app-filter');
    const favorites=document.querySelector('.favorites-filter');
    function update(){
      const query=!!(search&&search.value.trim());
      const fav=!!(favorites&&favorites.getAttribute('aria-pressed')==='true');
      const active=cards.filter(el=>!el.hidden&&!el.classList.contains('category-filtered-out'));
      // Keep user searches and favorite filters fully visible.
      const progressive=!query&&!fav;
      grid.dataset.appExpanded=progressive && limit>step ? 'true' : 'false';
      cards.forEach((el,index)=>el.classList.toggle('vone-app-collapsed',progressive&&index>=limit));
      more.hidden=!progressive||limit>=cards.length;
    }
    more.addEventListener('click',()=>{limit+=step;update();});
    search?.addEventListener('input',update);
    favorites?.addEventListener('click',()=>requestAnimationFrame(update));
    /* No MutationObserver on classes we ourselves toggle: avoids feedback loops. */
    window.addEventListener('resize',()=>{
      const next=window.matchMedia('(max-width: 767px)').matches?4:6;
      if(step!==next){step=next;limit=next;update();}
    });
    update();
  }
  // Separate News & Events into labeled collections on All Updates.
  const newsGrid=document.querySelector('.vone-library-grid');
  const cards=newsGrid?Array.from(newsGrid.querySelectorAll('[data-news-type]')):[];
  if(cards.length && (!new URLSearchParams(location.search).has('category') || new URLSearchParams(location.search).get('category')==='all')){
    const groups=[['news','Company News'],['announcement','Announcements'],['recognition','Rewards & Recognition'],['gallery','Photo Albums']];
    const parent=newsGrid.parentNode;
    groups.forEach(([kind,label])=>{
      const matching=cards.filter(el=>el.dataset.newsType===kind);
      if(!matching.length)return;
      const heading=document.createElement('h3');heading.className='vone-library-group-heading';heading.textContent=label;
      const group=document.createElement('div');group.className='vone-library-grid vone-library-group';
      matching.forEach(el=>group.appendChild(el));
      parent.insertBefore(heading,newsGrid);parent.insertBefore(group,newsGrid);
    });
    newsGrid.remove();
  }
  // In-application media viewer: images, local browser-compatible videos, PDFs.
  // External pages and blocked PDF frames fall back to the original link.
  const modal=document.createElement('div');modal.className='vone-media-modal';modal.hidden=true;
  modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.setAttribute('aria-label','Document and media viewer');
  modal.innerHTML='<div class="vone-media-shell"><div class="vone-media-head"><strong id="vone-media-title">Media viewer</strong><div><a id="vone-media-original" target="_blank" rel="noopener noreferrer">Open original ↗</a><button type="button" id="vone-media-close">Close ✕</button></div></div><div class="vone-media-body" id="vone-media-body"></div></div>';
  document.body.append(modal);
  const body=modal.querySelector('#vone-media-body'),title=modal.querySelector('#vone-media-title'),original=modal.querySelector('#vone-media-original'),close=modal.querySelector('#vone-media-close');
  let focusBefore=null;
  function closeModal(){if(modal.hidden)return;modal.hidden=true;body.replaceChildren();document.body.classList.remove('vone-media-active');focusBefore?.focus();}
  close.addEventListener('click',closeModal);
  modal.addEventListener('click',e=>{if(e.target===modal)closeModal();});
  document.addEventListener('keydown',e=>{if(!modal.hidden&&e.key==='Escape'){e.preventDefault();closeModal();}});
  function ext(url){try{return new URL(url,location.href).pathname.toLowerCase().split('.').pop();}catch(_){return '';}}
  function openMedia(url,label,poster){
    const type=ext(url);
    if(!['png','jpg','jpeg','webp','gif','bmp','avif','pdf','mp4','webm','ogg'].includes(type))return false;
    const u=new URL(url,location.href);
    // PDF embedded from another host can be blocked by frame policy. Open original.
    if(type==='pdf'&&u.origin!==location.origin)return false;
    body.replaceChildren();
    let node;
    if(['png','jpg','jpeg','webp','gif','bmp','avif'].includes(type)){
      node=document.createElement('img');node.src=u.href;node.alt=label||'Document image';
    }else if(['mp4','webm','ogg'].includes(type)){
      node=document.createElement('video');node.controls=true;node.autoplay=false;node.playsInline=true;node.src=u.href;if(poster)node.poster=poster;
    }else{
      node=document.createElement('iframe');
      node.src=u.href+'#toolbar=1&navpanes=0&view=FitH';
      node.title=label||'PDF document';
      node.setAttribute('loading','eager');
      node.setAttribute('referrerpolicy','same-origin');
    }
    body.append(node);title.textContent=label||'Media viewer';original.href=u.href;
    focusBefore=document.activeElement;modal.hidden=false;document.body.classList.add('vone-media-active');close.focus();
    return true;
  }
  document.addEventListener('click',e=>{
    if(e.defaultPrevented||e.button!==0||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;
    const a=e.target.closest('a[href]');if(!a||a.closest('.vone-media-modal'))return;
    if(!a.matches('.vone-resource-launch,.vone-resource-title-link,.vone-library-card a,.vone-preview-card a,.vone-csr-banner a,.step9-policy-card a,.vone-joiner-open[href],.vone-joiner-document-link'))return;
    if(a.closest('.vone-csr-banner'))return;
    const href=a.getAttribute('href');if(!href||href==='#')return;
    const poster=a.closest('.vone-preview-card')?.querySelector('img')?.src||'';
    if(openMedia(href,a.getAttribute('aria-label')||a.textContent.trim()||'Media',poster))e.preventDefault();
  });
});
})();
