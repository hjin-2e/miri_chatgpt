async function send(type){
 const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
 const status=document.querySelector('#status');
 if(!tab?.url?.startsWith('https://chatgpt.com/')){status.textContent='ChatGPT 탭에서 실행하세요';return;}
 try{
  await chrome.storage.local.set({autoEnabled:type==='start'});
  await chrome.tabs.sendMessage(tab.id,{type});
  status.textContent=type==='start'?'자동 실행 활성화됨 (새로고침 후에도 유지)':'자동 실행 비활성화됨';
 }catch(e){status.textContent='탭을 새로고침한 후 다시 시도하세요';}
}
document.querySelector('#start').onclick=()=>send('start');
document.querySelector('#stop').onclick=()=>send('stop');
chrome.storage.local.get({autoEnabled:false},cfg=>{document.querySelector('#status').textContent=cfg.autoEnabled?'자동 실행 활성화됨':'자동 실행 비활성화됨';});
