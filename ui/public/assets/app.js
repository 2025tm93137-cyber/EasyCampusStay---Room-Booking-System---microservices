'use strict';
const $=id=>document.getElementById(id);
const services=[['inventory','Python'],['reservation','Python'],['payment','PHP'],['notification','PHP']];
let rooms=[];let lastAttempt=null;let pollTimer=null;
const csrf=document.querySelector('meta[name="csrf-token"]').content;
const id=()=>crypto.randomUUID();
function message(text,error=false){$('message').hidden=false;$('message').textContent=text;$('message').className='message'+(error?' error':'');}
function raw(result){$('raw').textContent=JSON.stringify(result,null,2);}
async function call(action,extra={},show=true){
  const response=await fetch('/api.php',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({action,...extra})});
  const result=await response.json();
  if(!response.ok || !result.body)throw new Error(result.error||'The console request failed. Refresh the page and check the terminals.');
  if(show)raw(result);return result;
}
function escapeText(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function health(){
  try{const result=await call('health',{},false);$('health-cards').innerHTML=services.map(([name,lang])=>{
    const item=result.body.services[name];const ok=item.status===200&&item.body.status==='ok';
    return `<div class="health-card"><span class="dot ${ok?'ok':'bad'}"></span><strong>${name[0].toUpperCase()+name.slice(1)}</strong><small>${lang} · ${ok?'Healthy':'Unavailable'}</small></div>`;
  }).join('');}catch(error){message(error.message,true);}
}
async function loadRooms(selected=''){
  const result=await call('rooms',{},false);if(result.status!==200)throw new Error(result.body.error.message);
  rooms=result.body.room_types;const keep=selected||$('room-select').value;
  $('room-select').innerHTML='<option value="">Select a room type</option>'+rooms.map(room=>`<option value="${escapeText(room.room_type_id)}">${escapeText(room.name)} · ${escapeText(room.currency)} ${(room.price_minor/100).toLocaleString(undefined,{minimumFractionDigits:2})}</option>`).join('');
  if(rooms.some(room=>room.room_type_id===keep))$('room-select').value=keep;
}
async function availability(show=false){
  const room=$('room-select').value;if(!room)return;
  const result=await call('availability',{room_type_id:room,stay_date:$('stay-date').value},show);
  $('stock').textContent=result.status===200?`${result.body.available} of ${result.body.capacity} rooms available`:(result.body.error?.message||'Availability could not be read.');
}
function summary(booking){
  $('booking-status').textContent=booking.status;
  $('booking-status').className='status '+(booking.status==='CANCELLED'?'cancelled':booking.status==='CONFIRMED'?'':'pending');
  $('summary').innerHTML=[['Stay date',booking.stay_date],['Room price',booking.amount_minor?`${booking.currency} ${(booking.amount_minor/100).toLocaleString(undefined,{minimumFractionDigits:2})}`:'Awaiting inventory'],['Notification',booking.notification_status],['Booking state',booking.status]].map(([label,value])=>`<div><span class="label">${label}</span><strong>${escapeText(value)}</strong></div>`).join('');
}
async function inspect(show=true){
  const bid=$('booking-id').value.trim();if(!bid)return;
  const result=await call('booking',{booking_id:bid},show);
  if(result.status!==200){message(result.body.error.message,true);return;}
  summary(result.body);
  const steps=await call('steps',{booking_id:bid},false);
  $('timeline').innerHTML=(steps.body.steps||[]).map(step=>`<li>${escapeText(step.to_state)}</li>`).join('');
  await availability(false);
  if(result.body.status!=='CANCELLED'&&(result.body.status!=='CONFIRMED'||result.body.notification_status!=='SENT')){
    clearTimeout(pollTimer);pollTimer=setTimeout(()=>inspect(false).catch(error=>message(error.message,true)),1500);
  }else clearTimeout(pollTimer);
}
async function submitBooking(attempt,replay=false){
  const result=await call('book',attempt,true);
  const bid=result.body.booking_id||result.body.error?.details?.booking_id;
  if(bid){$('booking-id').value=bid;await inspect(false);}
  if(result.status>=400)message(`${result.status}: ${result.body.error.message}`,true);
  else if(result.status===202)message('Booking accepted. Payment is still being resolved. The current status will refresh safely.');
  else message(replay?'Original request replayed. The same booking response was returned.':'Booking confirmed. The workflow and current status are shown below.');
  raw(result);return result;
}
function guarded(handler){return async event=>{event.preventDefault();const button=event.submitter||event.currentTarget;const disabled='disabled'in button;if(disabled)button.disabled=true;try{await handler(event);}catch(error){message(error.message,true);}finally{if(disabled)button.disabled=false;}};}
$('room-form').addEventListener('submit',guarded(async()=>{
  const result=await call('create_room',{key:id(),payload:{name:$('room-name').value.trim(),capacity:Number($('capacity').value),price_minor:Number($('price').value)*100,currency:'INR',dates:[$('stay-date').value]}});
  if(result.status!==201)throw new Error(result.body.error.message);
  await loadRooms(result.body.room_type_id);await availability(false);message('Demo inventory created. Continue with Book a room.');
}));
$('booking-form').addEventListener('submit',guarded(async()=>{
  lastAttempt={key:id(),payload:{room_type_id:$('room-select').value,stay_date:$('stay-date').value,guest_ref:$('guest').value.trim(),recipient:$('recipient').value.trim(),payment_mode:$('payment-mode').value,notification_mode:$('notification-mode').value}};
  $('replay').disabled=false;$('conflict').disabled=false;await submitBooking(lastAttempt);
}));
$('lookup-form').addEventListener('submit',guarded(()=>inspect(true)));
$('replay').addEventListener('click',guarded(()=>submitBooking(lastAttempt,true)));
$('conflict').addEventListener('click',guarded(async()=>{
  const changed={key:lastAttempt.key,payload:{...lastAttempt.payload,guest_ref:lastAttempt.payload.guest_ref+'-changed'}};
  const result=await call('book',changed);message(result.status===409?'409: changed payload rejected for the same request key.':`Response ${result.status}; inspect the API result.`,result.status!==409);
}));
$('check-stock').addEventListener('click',guarded(()=>availability(true)));
$('room-select').addEventListener('change',()=>availability(false).catch(error=>message(error.message,true)));
$('stay-date').addEventListener('change',()=>availability(false).catch(error=>message(error.message,true)));
$('refresh-health').addEventListener('click',()=>health());
for(const name of ['payment','notification'])$('inspect-'+name).addEventListener('click',guarded(async()=>{
  const bid=$('booking-id').value.trim();if(!bid)throw new Error('Create or look up a booking first.');
  const result=await call(name,{booking_id:bid});if(result.status>=400)message(result.body.error.message,true);else message(`${name[0].toUpperCase()+name.slice(1)} response is available under Inspect the last API response.`);
  $('raw').parentElement.open=true;
}));
const day=new Date();day.setDate(day.getDate()+7);
$('stay-date').value=`${day.getFullYear()}-${String(day.getMonth()+1).padStart(2,'0')}-${String(day.getDate()).padStart(2,'0')}`;
health();loadRooms().catch(error=>message(error.message,true));
