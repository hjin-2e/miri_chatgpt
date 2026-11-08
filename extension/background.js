const BASE='http://127.0.0.1:8765';
async function post(path,obj){try{await fetch(BASE+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});}catch(e){console.warn('Local server:',e);}}
chrome.runtime.onMessage.addListener((m,sender,reply)=>{
 if(m.type==='download'){
   // Download URL must originate from a ChatGPT image element, not arbitrary remote instructions.
   if(!m.url || !/^https:\/\//.test(m.url)){reply({ok:false,error:'invalid URL'});return;}
   const filename='miri_auto_inbox/'+m.filename;
   if(!/^[\w.-]+\.png$/.test(m.filename)||m.filename.includes('..')){reply({ok:false,error:'invalid filename'});return;}
   chrome.downloads.download({url:m.url,filename,conflictAction:'uniquify',saveAs:false},id=>{
     if(chrome.runtime.lastError||!id){reply({ok:false,error:chrome.runtime.lastError?.message||'download failed'});return;}
     chrome.storage.local.set({['dl_'+id]:m.filename});reply({ok:true,id});
   });return true;
 }
 if(m.type==='fail'){post('/fail',{filename:m.filename,message:m.message});reply({ok:true});}
});
chrome.downloads.onChanged.addListener(async delta=>{
 if(!delta.state||!['complete','interrupted'].includes(delta.state.current))return;
 const key='dl_'+delta.id;const stored=await chrome.storage.local.get(key);const name=stored[key];if(!name)return;
 await chrome.storage.local.remove(key);
 await post(delta.state.current==='complete'?'/complete':'/fail',{filename:name,message:delta.state.current});
});
