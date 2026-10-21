/* A1.9: handle dismissal with server JSON; never treat a login redirect as success. */
document.addEventListener('DOMContentLoaded',()=>{
 const section=document.getElementById('vone-notice-section');
 if(!section)return;
 section.addEventListener('submit',async event=>{
  const form=event.target.closest('form[data-dismiss-notice]');
  if(!form)return;
  event.preventDefault();event.stopImmediatePropagation();
  const button=form.querySelector('button[type="submit"]');
  if(button)button.disabled=true;
  try{
   const response=await fetch(form.action,{method:'POST',credentials:'same-origin',body:new FormData(form),headers:{'X-Requested-With':'XMLHttpRequest','Accept':'application/json'},redirect:'follow'});
   const type=response.headers.get('content-type')||'';
   if(!response.ok||!type.includes('application/json'))throw Error('Expected JSON acknowledgement, got '+response.status+' '+response.url);
   const result=await response.json();if(!result.ok)throw Error('Dismiss not confirmed');
   form.closest('.vone-notice-modern-item')?.remove();
   if(!section.querySelector('.vone-notice-modern-item'))section.remove();
   document.dispatchEvent(new Event('vone:notice-read'));
  }catch(error){console.error('Notice dismiss:',error);alert('Could not dismiss notice. Please refresh and try again.');}
  finally{if(button)button.disabled=false;}
 },true);
});
