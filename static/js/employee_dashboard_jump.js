/* Step 16.23 – Dashboard section quick navigation, reflects current layout. */
(function(){
 'use strict';
 document.addEventListener('DOMContentLoaded',function(){
  const hero=document.querySelector('.dashboard-intro + .hero')||document.querySelector('.hero');
  const layout=document.querySelector('.dashboard-reorder-layout');
  if(!hero||!layout)return;
  const labels={apps:'Applications',highlights:'Highlights',updates:'Latest updates',policies:'Policies',joiners:'New colleagues',events:'Events'};
  const selectors={apps:'.apps-section',highlights:'.home-highlights',updates:'.news-section',policies:'.step9-policies',joiners:'.step7-grid > .section:first-child',events:'.step7-grid > .section:last-child'};
  const sections=new Map();
  Object.entries(selectors).forEach(([id,selector])=>{
   const node=layout.querySelector(selector)||document.querySelector(selector);
   if(node&&layout.contains(node)){sections.set(node,id);node.id=node.id||'dashboard-jump-'+id;node.classList.add('dashboard-jump-target');}
  });
  if(!sections.size)return;
  const nav=document.createElement('nav');nav.className='dashboard-jump';nav.setAttribute('aria-label','Dashboard sections');
  const header=document.createElement('div');header.className='dashboard-jump-heading';
  const label=document.createElement('strong');label.textContent='Explore your dashboard';
  const hint=document.createElement('span');hint.textContent='Jump to a section';
  header.append(label,hint);
  const track=document.createElement('div');track.className='dashboard-jump-track';
  nav.append(header,track);hero.insertAdjacentElement('afterend',nav);
  const icons={apps:'▦',highlights:'✦',updates:'◷',policies:'▤',joiners:'♙',events:'▣'};
  function refresh(){
   const visible=[...layout.children].filter(node=>sections.has(node)&&!node.hidden&&!node.classList.contains('dashboard-widget-hidden')&&getComputedStyle(node).display!=='none');
   const ids=visible.map(node=>sections.get(node));
   const current=[...track.children].map(el=>el.dataset.section);
   if(ids.join('|')===current.join('|')){nav.hidden=visible.length<2;return;}
   track.replaceChildren();
   visible.forEach(node=>{
    const id=sections.get(node);
    const a=document.createElement('a');a.className='dashboard-jump-link';a.href='#'+node.id;a.dataset.section=id;
    const glyph=document.createElement('span');glyph.className='dashboard-jump-icon';glyph.textContent=icons[id];glyph.setAttribute('aria-hidden','true');
    const name=document.createElement('span');name.textContent=labels[id];
    a.append(glyph,name);
    a.addEventListener('click',e=>{
     e.preventDefault();
     node.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
     history.replaceState(null,'',location.pathname+location.search+'#'+node.id);
    });
    track.append(a);
   });
   nav.hidden=visible.length<2;
  }
  let scheduled=false;
  const observer=new MutationObserver(()=>{
   if(scheduled)return;
   scheduled=true;
   requestAnimationFrame(()=>{scheduled=false;refresh();});
  });
  observer.observe(layout,{childList:true,subtree:false,attributes:true,attributeFilter:['hidden','class']});
  sections.forEach(node=>observer.observe(node,{attributes:true,attributeFilter:['hidden','class']}));
  refresh();
 });
})();
