const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();
const pages=[['home','/'],['group','/zubehoer/chargers/'],['prod','/zubehoer/chargers/anker-nano-3-30w/'],['tiktok','/tiktok/#v14'],['duel','/vergleich/sony-wf-1000xm6-vs-apple-airpods-pro-3/'],['app','/app/']];
for(const [w,h,tag] of [[1280,900,'d'],[390,844,'m']]){const p=await b.newPage({viewport:{width:w,height:h}});
 const errs=[];p.on('pageerror',x=>errs.push(String(x).slice(0,150)));
 for(const [n,u] of pages){await p.goto('http://localhost:8765'+u,{waitUntil:'load'});await p.waitForTimeout(n==='app'?1500:200);
  const sw=await p.evaluate(()=>document.documentElement.scrollWidth);await p.screenshot({path:`/tmp/claude-0/-home-claude/2e2512fc-54c5-5d78-aeda-d1c0f2f87864/scratchpad/${n}-${tag}.png`});console.log(n,tag,'scrollW',sw)}
 console.log('errors',errs)}
await b.close()})();
