/* Step 16.18: customizable and reorderable Home dashboard; AI stays pinned first. */
(function () {
 'use strict';
 document.addEventListener('DOMContentLoaded', function () {
  const intro=document.querySelector('.dashboard-intro');
  const hero=document.querySelector('.hero');
  const apps=document.querySelector('.apps-section');
  if(!intro||!hero||!apps) return; // Home only
  const blocks=[
   {id:'apps',label:'Quick access to applications',selector:'.apps-section'},
   {id:'highlights',label:'Company highlights',selector:'.home-highlights'},
   {id:'updates',label:'Latest updates',selector:'.news-section'},
   {id:'policies',label:'Recently published policies',selector:'.step9-policies'},
   {id:'joiners',label:'New colleagues',selector:'.step7-grid > .section:first-child'},
   {id:'events',label:'Upcoming events',selector:'.step7-grid > .section:last-child'},
   {id:'gallery',label:'Life at Vishakha',selector:'.vone-home-gallery'},
   {id:'csr',label:'Corporate Social Responsibility',selector:'.vone-home-csr'},
   {id:'insider',label:'Vishakha Insider',selector:'.vone-home-insider'},
   {id:'bankbenefits',label:'Bank Benefits',selector:'.vone-home-benefits'},
   {id:'canteen',label:'Canteen Menu',selector:'.vone-home-canteen'},
   {id:'brochures',label:'Brochures',selector:'.vone-home-brochures'}
  ].map(x=>({...x,element:document.querySelector(x.selector)})).filter(x=>x.element);
  if(!blocks.length) return;
  const KEY='vishakha_one_dashboard_visibility_v1';
  const ORDER_KEY='vishakha_one_dashboard_order_v1';
  function readJSON(key,fallback){
   try {const value=JSON.parse(localStorage.getItem(key)||'null');return value===null?fallback:value;}
   catch(e){return fallback;}
  }
  let preferences=readJSON(KEY,{});
  if(!preferences||typeof preferences!=='object'||Array.isArray(preferences)) preferences={};
  const savedOrder=readJSON(ORDER_KEY,[]);
  let order=Array.isArray(savedOrder)?savedOrder.filter(id=>blocks.some(x=>x.id===id)):[];
  blocks.forEach(x=>{if(!order.includes(x.id))order.push(x.id);});
  const originalOrder=blocks.map(x=>x.id);
  // Keep AI banner outside the reorderable area, immediately below intro.
  const layout=document.createElement('div');
  layout.className='dashboard-reorder-layout';
  hero.insertAdjacentElement('afterend',layout);
  const oldContainers=new Set();
  blocks.forEach(item=>{
    const parent=item.element.parentElement;
    if(parent&&parent.classList.contains('content-grid'))oldContainers.add(parent);
    item.element.classList.add('dashboard-movable-section');
  });
  oldContainers.forEach(container=>container.remove());
  // The original hero remains first and cannot be hidden or reordered.
  hero.hidden=false;
  hero.classList.remove('dashboard-widget-hidden');
  const controls=document.createElement('div');
  controls.className='dashboard-customizer';
  const toggle=document.createElement('button');
  toggle.type='button';toggle.className='dashboard-customizer-toggle';
  toggle.setAttribute('aria-expanded','false');
  toggle.setAttribute('aria-controls','dashboard-customizer-panel');
  toggle.innerHTML='<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="currentColor" stroke="none"/><circle cx="16" cy="17" r="3" fill="currentColor" stroke="none"/></svg><span>Customize dashboard</span>';
  const panel=document.createElement('div');
  panel.className='dashboard-customizer-panel';panel.id='dashboard-customizer-panel';panel.hidden=true;
  const title=document.createElement('strong');title.textContent='Arrange your dashboard';
  const sub=document.createElement('p');sub.textContent='Drag sections to rearrange. Keyboard: focus a handle, then press Alt + ↑ or Alt + ↓.';
  const rows=document.createElement('div');rows.className='dashboard-customizer-rows';
  const reset=document.createElement('button');reset.type='button';reset.className='dashboard-customizer-reset';
  reset.textContent='Restore default layout';
  const status=document.createElement('span');
  status.className='dashboard-customizer-status';
  status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  panel.append(title,sub,rows,reset,status);
  controls.append(toggle,panel);intro.append(controls);
  const byId=new Map(blocks.map(x=>[x.id,x]));
  function changed(message){
    save();apply();renderRows();status.textContent=message;
  }
  function save(){
   try{localStorage.setItem(KEY,JSON.stringify(preferences));localStorage.setItem(ORDER_KEY,JSON.stringify(order));}catch(e){}
  }
  function apply(){
   order.forEach(id=>{
    const item=byId.get(id);if(!item)return;
    layout.appendChild(item.element);
    const hidden=preferences[id]===false;
    item.element.hidden=hidden;
    item.element.classList.toggle('dashboard-widget-hidden',hidden);
   });
   // AI is always first, even if old Step 16.17 preferences hid it.
   hero.hidden=false;
   hero.classList.remove('dashboard-widget-hidden');
  }
  function reorder(from,to){
   if(!byId.has(from)||!byId.has(to)||from===to)return;
   order=order.filter(id=>id!==from);
   order.splice(order.indexOf(to),0,from);
   changed('Section order updated.');
  }
  function renderRows(){
   rows.replaceChildren();
   order.forEach((id,index)=>{
    const item=byId.get(id);if(!item)return;
    const row=document.createElement('div');row.className='dashboard-arrange-row';
    row.dataset.row=id;row.draggable=true;
    const grip=document.createElement('span');grip.className='dashboard-arrange-grip';
    grip.textContent='⠿';grip.tabIndex=0;
    const label=document.createElement('label');label.className='dashboard-arrange-label';
    const check=document.createElement('input');check.type='checkbox';check.checked=preferences[id]!==false;
    check.setAttribute('aria-label','Show '+item.label);
    check.addEventListener('change',()=>{preferences[id]=check.checked;changed('Section visibility updated.');});
    const name=document.createElement('span');name.textContent=item.label;
    label.append(check,name);
    grip.title='Drag to rearrange';
    grip.setAttribute('aria-label','Reorder '+item.label+'. Press Alt and Up or Down arrow.');
    grip.setAttribute('role','button');
    row.append(grip,label);rows.append(row);
    grip.addEventListener('keydown',event=>{
      if(!event.altKey || (event.key!=='ArrowUp' && event.key!=='ArrowDown'))return;
      event.preventDefault();
      const current=order.indexOf(id);
      const next=current+(event.key==='ArrowUp'?-1:1);
      if(next<0 || next>=order.length){
        status.textContent='Already at the '+(next<0?'top.':'bottom.');
        return;
      }
         [order[current],order[next]]=[order[next],order[current]];
      changed(item.label+' moved '+(next<current?'up.':'down.'));
      rows.querySelector('[data-row="'+id+'"] .dashboard-arrange-grip')?.focus();
    });
    grip.addEventListener('pointerdown',event=>{
     if(event.pointerType==='mouse')return; // desktop uses native drag/drop
     event.preventDefault();
     const pointer=event.pointerId;
     let lastTarget=null;
     row.classList.add('dashboard-arrange-dragging');
     grip.setPointerCapture(pointer);
     function movePointer(ev){
      const hit=document.elementFromPoint(ev.clientX,ev.clientY);
      const target=hit?.closest('.dashboard-arrange-row');
      if(target&&target!==row){
       lastTarget=target.dataset.row;
       target.scrollIntoView({block:'nearest',behavior:'instant'});
      }
     }
     function endPointer(){
      grip.removeEventListener('pointermove',movePointer);
      grip.removeEventListener('pointerup',endPointer);
      grip.removeEventListener('pointercancel',cancelPointer);
      row.classList.remove('dashboard-arrange-dragging');
      if(lastTarget)reorder(id,lastTarget);
     }
     function cancelPointer(){
      lastTarget=null;endPointer();
     }
     grip.addEventListener('pointermove',movePointer);
     grip.addEventListener('pointerup',endPointer);
     grip.addEventListener('pointercancel',cancelPointer);
    });
    row.addEventListener('dragstart',event=>{
     if(event.target.closest('button,input')){event.preventDefault();return;}
     event.dataTransfer.effectAllowed='move';
     event.dataTransfer.setData('text/plain',id);
     row.classList.add('dashboard-arrange-dragging');
    });
    row.addEventListener('dragend',()=>row.classList.remove('dashboard-arrange-dragging'));
    row.addEventListener('dragover',event=>{event.preventDefault();event.dataTransfer.dropEffect='move';});
    row.addEventListener('drop',event=>{
     event.preventDefault();
     reorder(event.dataTransfer.getData('text/plain'),id);
    });
   });
  }
  reset.addEventListener('click',()=>{
   preferences={};order=originalOrder.slice();
   try{localStorage.removeItem(KEY);localStorage.removeItem(ORDER_KEY);}catch(e){}
   apply();renderRows();status.textContent='Default layout restored.';
  });
  function close(){panel.hidden=true;toggle.setAttribute('aria-expanded','false');}
  toggle.addEventListener('click',()=>{
   const opening=panel.hidden;panel.hidden=!opening;
   toggle.setAttribute('aria-expanded',String(opening));
   if(opening)rows.querySelector('.dashboard-arrange-grip')?.focus();
  });
  document.addEventListener('click',e=>{if(!controls.contains(e.target))close();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden){close();toggle.focus();}});
  window.addEventListener('storage',e=>{
   if(e.key!==KEY&&e.key!==ORDER_KEY)return;
   preferences=readJSON(KEY,{});
   status.textContent='';
   const next=readJSON(ORDER_KEY,[]);
   order=Array.isArray(next)?next.filter(id=>byId.has(id)):[];
   originalOrder.forEach(id=>{if(!order.includes(id))order.push(id);});
   apply();renderRows();
  });
  apply();renderRows();
 });
})();
