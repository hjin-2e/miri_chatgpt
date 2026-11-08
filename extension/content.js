/* Best-effort browser DOM adapter. ChatGPT may change its UI; fail closed. */
(()=>{
const BASE='http://127.0.0.1:8765';let enabled=false,busy=false,previous=null;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function next(){const r=await fetch(BASE+'/next');if(!r.ok)throw Error('local server');return (await r.json()).item;}
const imgs=()=>[...document.querySelectorAll('img')].filter(x=>x.naturalWidth>=512&&x.naturalHeight>=512&&x.getBoundingClientRect().width>100);
function imageSnapshot(){return new Set(imgs().map(x=>x.currentSrc||x.src));}
function editor(){return document.querySelector('#prompt-textarea[contenteditable="true"]')||document.querySelector('[data-testid="composer-input"][contenteditable="true"]')||document.querySelector('[contenteditable="true"][role="textbox"]');}
function sendButton(){return document.querySelector('[data-testid="send-button"]')||document.querySelector('button[aria-label="Send prompt"]')||document.querySelector('button[aria-label="메시지 보내기"]');}
function submit(prompt){
 const el=editor();if(!el)throw Error('ChatGPT composer not found');
 el.focus();document.execCommand('selectAll',false,null);
 // execCommand inserts through the editable DOM and triggers app input handlers on many React versions.
 if(!document.execCommand('insertText',false,prompt))throw Error('text insertion blocked');
 el.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:prompt}));
 const btn=sendButton();if(!btn||btn.disabled)throw Error('send button not ready');btn.click();
}
function isDownload(b){const s=[b.getAttribute('aria-label'),b.getAttribute('title'),b.getAttribute('data-testid'),b.textContent].filter(Boolean).join(' ').toLowerCase();return /download|다운로드|저장/.test(s);}
async function extractImageUrl(img){
 let u=img.currentSrc||img.src;if(!u)return null;
 if(u.startsWith('https://'))return u;
 // blob URLs can't be downloaded by extension downloads API; not silently report success.
 return null;
}
async function runOne(item){
 const before=imageSnapshot();submit(item.prompt);
 let candidate=null;
 for(let i=0;i<180;i++){
   await sleep(2000);
   candidate=imgs().find(x=>!before.has(x.currentSrc||x.src)&&x.complete&&x.naturalWidth>=512);
   if(candidate)break;
 }
 if(!candidate)throw Error('No new completed image found within 6 minutes');
 let url=await extractImageUrl(candidate);
 if(!url){
   candidate.click();await sleep(1200);
   const buttons=[...document.querySelectorAll('button')].filter(isDownload).filter(x=>x.getBoundingClientRect().width>0);
   if(buttons.length!==1)throw Error('Download button ambiguous/missing: '+buttons.length);
   // Clicking may download without a discoverable URL. This version does not assume filename mapping.
   throw Error('Image URL is blob; requires a future download interception adapter');
 }
 const result=await chrome.runtime.sendMessage({type:'download',url,filename:item.filename});
 if(!result?.ok)throw Error(result?.error||'download failed');
 // Wait for Chrome download completion and local import before requesting the next item.
 for(let i=0;i<150;i++){
   await sleep(2000);
   const status=await (await fetch(BASE+'/status')).json();
   const entry=status.items.find(x=>x.filename===item.filename);
   if(entry?.status==='ready')return;
   if(['failed','import_error'].includes(entry?.status))throw Error(entry.message||entry.status);
 }
 throw Error('Download/import did not finish within 5 minutes');
}
async function tick(){
 if(!enabled||busy)return;busy=true;
 try{
  const item=await next();if(!item){enabled=false;return;}
  // Existing active item could have been submitted before page reload. Never resubmit silently.
  if(previous===item.filename)throw Error('Already attempted; refresh/restart required');
  previous=item.filename;
  await runOne(item);
 }catch(e){console.error('[Miri Auto]',e);enabled=false;
   if(previous)await chrome.runtime.sendMessage({type:'fail',filename:previous,message:String(e.message||e)});
 }finally{busy=false;if(enabled)setTimeout(tick,1500);}
}
chrome.runtime.onMessage.addListener((m,s,r)=>{if(m.type==='start'){enabled=true;tick();r({ok:true});}else if(m.type==='stop'){enabled=false;r({ok:true});}});
})();
