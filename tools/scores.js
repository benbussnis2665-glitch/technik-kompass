const {chromium}=require('playwright');const fs=require('fs');
(async()=>{const b=await chromium.launch();const p=await b.newPage();
p.on('pageerror',e=>console.error('pageerr',String(e).slice(0,200)));
await p.goto('file://'+process.argv[2],{waitUntil:'load'});await p.waitForTimeout(1500);
const out=await p.evaluate(()=>{const T=window.TK;if(!T)return null;const r={};
 for(const g of T.DATA.groups){const p0=g.profiles[0];const R=T.scoreAll(g,{w:p0.w,p:p0.p||0,e:0},[]);
  r[g.id]={cats:g.cats.map(c=>c.n),prof:g.profiles.map(x=>x.n),items:g.products.map((pr,i)=>({n:pr.n,tot:+R.tot[i].toFixed(2),ca:R.ca.map(c=>+(c[i]||0).toFixed(2)),price:(T.priceOf?T.priceOf(g,i):null)}))}}
 return r});
fs.writeFileSync(process.argv[3],JSON.stringify(out));console.log(out?Object.keys(out).length:'no TK');await b.close()})();
