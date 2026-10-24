/* Intercept home notice dismiss before mobile overlays or other handlers. */
document.addEventListener('DOMContentLoaded',()=>{
 const section=document.getElementById('vone-notice-section');
 if(!section)return;
 section.addEventListener('submit',async event=>{
  const form=event.target.closest('form[data-dismiss-notice]');
  if(!form)return;
  event.preventDefault();event.stopPropagation();
  const button=form.querySelector('button[type="submit"]');
  if(button)button.disabled=true;
  try{
   const response=await fetch(form.action,{method:'POST',credentials:'same-origin',body:new FormData(form),redirect:'manual',headers:{'X-Requested-With':'XMLHttpRequest'}});
   if(response.type==='opaqueredirect'||response.status===302||response.ok){location.reload();return;}
   throw new Error('HTTP '+response.status);
  }catch(error){if(button)button.disabled=false;alert('Could not dismiss this notice. Refresh and try again.');console.warn(error);}
 },true);
});
