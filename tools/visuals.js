/* Erzeugt die Gerätebilder für die statische Seite aus der Original-Seite (src/original.html).
   - Handys: 3D-Standbild (WebP) + Dreh-Sprite (WebP, 30 Bilder nebeneinander) aus dem eigenen WebGL-Renderer (TK3D)
   - alle anderen Geräte: SVG-Zeichnung aus art()
   - Kategorien: Titel-Illustration aus TKArt (als WebP)
   Ausgabe: assets/gen/… und assets/gen/manifest.json (Schlüssel: Gruppen-ID + "|" + Gerätename).
   Aufruf: node tools/visuals.js   (braucht Playwright mit Chromium) */
const {chromium}=require('playwright');const fs=require('fs');const path=require('path');const crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..');const OUT=path.join(ROOT,'assets/gen');
const FR=30,SW=440,SH=550;           /* Dreh-Sprite: 30 Bilder à 440×550 */
const slug=s=>{s=s.toLowerCase();for(const [a,b] of [["ä","ae"],["ö","oe"],["ü","ue"],["ß","ss"],["+"," plus "],["&"," und "]])s=s.split(a).join(b);return s.replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"")};
(async()=>{
  for(const d of ['p','s','c'])fs.mkdirSync(path.join(OUT,d),{recursive:true});
  const html=fs.readFileSync(path.join(ROOT,'src/original.html'),'utf8')
    .replace(';/* ==== 30-p3d.js ==== */',';window.__TKX={art};/* ==== 30-p3d.js ==== */');
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  const pg=await b.newPage({viewport:{width:1200,height:900},colorScheme:'light'});
  pg.on('pageerror',e=>console.log('Seitenfehler:',String(e).slice(0,200)));
  await pg.route('http://tk.local/',r=>r.fulfill({contentType:'text/html',body:html}));
  await pg.goto('http://tk.local/');await pg.waitForFunction(()=>window.TK&&window.__TKX&&window.TKArt);
  await pg.evaluate(()=>{document.documentElement.dataset.theme='light'});
  const groups=await pg.evaluate(()=>TK.DATA.groups.map(g=>({id:g.id,icon:g.icon,sect:g.sect,n:g.products.map(p=>p.n)})));
  const gl=await pg.evaluate(()=>!!(window.TK3D&&TK3D.supported));
  if(!gl)console.log('Achtung: kein WebGL, Handys bekommen nur 2D-Zeichnungen');
  const man={products:{},sections:{}};const wr=(rel,buf)=>{fs.writeFileSync(path.join(OUT,rel),buf);return 'gen/'+rel};
  const b64=s=>Buffer.from(s.split(',')[1],'base64');
  for(const g of groups){
    for(let i=0;i<g.n.length;i++){
      const key=g.id+'|'+g.n[i];const base=g.id+'-'+slug(g.n[i]);
      if(g.icon==='phone'&&gl){
        const r=await pg.evaluate(async([gid,i,FR,SW,SH])=>{const g=TK.GR[gid];
          const st=await TK3D.renderStill(g,i,0,{width:640,height:800,dark:false,scale:.8});
          const sp=document.createElement('canvas');sp.width=SW*FR;sp.height=SH;const x=sp.getContext('2d');
          await TK3D.turntable(g,i,0,{frames:FR,width:SW,height:SH,dark:false,scale:.8},(c,k)=>{x.drawImage(c,k*SW,0)});
          return {still:st.toDataURL('image/webp',.86),spin:sp.toDataURL('image/webp',.8)}},[g.id,i,FR,SW,SH]);
        man.products[key]={img:wr('p/'+base+'.webp',b64(r.still)),spin:wr('p/'+base+'-3d.webp',b64(r.spin)),frames:FR,w:SW,h:SH,kind:'3d'};
      }else{
        /* SVG-Zeichnung; Verweise auf gemeinsame Verläufe (url(#…)) werden als eigene <defs> mitgenommen */
        const s=await pg.evaluate(([gid,i])=>{let s=__TKX.art(TK.GR[gid],i,400);if(!s.startsWith('<svg'))return s;
          const ids=[...new Set((s.match(/url\(#[^)]+\)/g)||[]).map(x=>x.slice(5,-1)))];
          const defs=ids.map(id=>{const el=document.getElementById(id);return el?el.outerHTML:''}).join('');
          if(defs)s=s.replace(/^(<svg[^>]*>)/,'$1<defs>'+defs+'</defs>');return s},[g.id,i]);
        if(!s.startsWith('<svg')){continue}
        const svg=s.replace('<svg class="art" width="400" height="400"','<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"');
        man.products[key]={img:wr('p/'+base+'.svg',svg),kind:'svg'};
      }
    }
    process.stdout.write(g.id+' ');
  }
  /* Kategorie-Illustrationen: Szene mit CSS-Variablen der Seite als Bild abfotografieren */
  const ids=await pg.evaluate(()=>TKArt.ids);
  await pg.addStyleTag({content:'html,body{background:transparent!important}body>*:not(#__shot){visibility:hidden!important}'});
  for(const id of ids){
    await pg.evaluate(id=>{let h=document.getElementById('__shot');if(!h){h=document.createElement('div');h.id='__shot';h.style.cssText='position:fixed;left:0;top:0;width:960px;height:600px;z-index:99999;background:transparent';document.body.appendChild(h)}
      h.innerHTML=TKArt.svg(id);const s=h.firstElementChild;s.style.cssText='width:960px;height:600px;display:block';s.classList.remove('art-play')},id);
    await pg.waitForTimeout(60);
    const png=await pg.locator('#__shot').screenshot({omitBackground:true,animations:'disabled'});
    const webp=await pg.evaluate(async b=>{const im=new Image();im.src='data:image/png;base64,'+b;await im.decode();const c=document.createElement('canvas');c.width=im.width;c.height=im.height;c.getContext('2d').drawImage(im,0,0);return c.toDataURL('image/webp',.85)},png.toString('base64'));
    man.sections[id]=wr('s/'+id+'.webp',b64(webp));
  }
  await pg.evaluate(()=>{const h=document.getElementById('__shot');if(h)h.remove()});
  man.source=crypto.createHash('sha1').update(html).digest('hex').slice(0,12);
  fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify(man,null,0));
  console.log('\nfertig:',Object.keys(man.products).length,'Geräte,',Object.keys(man.sections).length,'Kategorie-Bilder');
  await b.close()})();
