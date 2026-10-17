(()=>{'use strict';
const sections=[['apps','Applications','grid-2x2'],['news','News & Events','newspaper'],['documents','Documents','files'],['policies','Policies','shield-check'],['joiners','New Joiners','users'],['videos','Company Videos','play'],['bank-benefits','Bank Benefits','wallet'],['canteen-menu','Canteen Menu','utensils'],['insider','Vishakha Insider','book-open']];
const allowed=new Map(sections.map(([slug,label])=>[slug,label]));
// Store only a fixed section slug; never store search queries, names, tokens, or document URLs.
const key='vone_recent_sections_v1';
function read(){try{const value=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(value)?value.filter(v=>typeof v==='string'&&allowed.has(v)).slice(0,5):[];}catch{return [];}}
function save(a){try{localStorage.setItem(key,JSON.stringify(a));}catch{}}
function slugFromPath(path){const match=path.match(/^\/(?:section\/)?([a-z-]+)\/?$/);return match&&allowed.has(match[1])?match[1]:null;}
function record(slug){if(!allowed.has(slug))return;const next=[slug,...read().filter(s=>s!==slug)].slice(0,5);save(next);}
const current=slugFromPath(location.pathname);if(current)record(current);
document.addEventListener('DOMContentLoaded',()=>{
const section=document.getElementById('vone-continue-section'),grid=document.getElementById('vone-continue-grid'),clear=document.getElementById('vone-continue-clear');
if(!section||!grid)return;
function render(){grid.replaceChildren();const recent=read();section.hidden=!recent.length;recent.forEach(slug=>{const link=document.createElement('a');link.className='vone-continue-link';link.href='/'+slug+'/';link.textContent=allowed.get(slug);link.setAttribute('aria-label','Open '+allowed.get(slug));grid.append(link);});}
clear?.addEventListener('click',()=>{try{localStorage.removeItem(key);}catch{}render();});render();
});
})();