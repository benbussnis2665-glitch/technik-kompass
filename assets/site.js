/* Technik Kompass – kleine Helfer für die statische Seite (ohne Bibliotheken) */
(function(){
"use strict";
var RED=window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches;
var $=function(s,r){return (r||document).querySelector(s)},$$=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};

/* ---------- 3D-Drehen: Sprite mit N Bildern nebeneinander ---------- */
function Spin(el){
  var N=+el.dataset.frames||30,src=el.dataset.sprite,sp=document.createElement("i"),f=0,loaded=false,loading=false,auto=null;
  sp.className="sp";el.appendChild(sp);
  sp.style.backgroundSize=(N*100)+"% 100%";
  function show(k){f=((Math.round(k)%N)+N)%N;sp.style.backgroundPosition=(N>1?f/(N-1)*100:0)+"% 0";if(loaded)el.classList.toggle("live",f!==0)}
  function load(cb){if(loaded){cb&&cb();return}if(loading)return;loading=true;var im=new Image();im.onload=function(){loaded=true;sp.style.backgroundImage="url('"+src+"')";show(0);cb&&cb()};im.src=src}
  function stopAuto(){if(auto){cancelAnimationFrame(auto);auto=null}}
  function intro(){if(RED||el.dataset.auto==="0")return;load(function(){var t0=null,dur=+(el.dataset.dur||3600);
    function step(t){if(t0===null)t0=t;var p=Math.min(1,(t-t0)/dur);var e=p<.5?2*p*p:1-Math.pow(-2*p+2,2)/2;show(e*N);if(p<1)auto=requestAnimationFrame(step);else{auto=null;show(0);if(el.dataset.loop==="1")setTimeout(intro,2600)}}
    auto=requestAnimationFrame(step)})}
  /* Ziehen */
  var down=false,x0=0,f0=0,moved=false;
  el.addEventListener("pointerdown",function(e){if(e.pointerType==="mouse"&&e.button!==0)return;down=true;moved=false;x0=e.clientX;f0=f;stopAuto();load();el.classList.add("drag");try{el.setPointerCapture(e.pointerId)}catch(_){}});
  el.addEventListener("pointermove",function(e){if(!down)return;var dx=e.clientX-x0;if(Math.abs(dx)>3)moved=true;var w=el.clientWidth||300;show(f0-dx/w*N*0.9)});
  function up(){if(!down)return;down=false;el.classList.remove("drag")}
  el.addEventListener("pointerup",up);el.addEventListener("pointercancel",up);el.addEventListener("lostpointercapture",up);
  el.addEventListener("click",function(e){if(moved){e.preventDefault();e.stopPropagation()}},true);
  el.addEventListener("keydown",function(e){if(e.key==="ArrowLeft"||e.key==="ArrowRight"){e.preventDefault();stopAuto();load(function(){show(f+(e.key==="ArrowLeft"?1:-1))})}});
  /* Beim Sichtbarwerden einmal drehen */
  if("IntersectionObserver" in window){var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){io.disconnect();setTimeout(intro,250)}})},{threshold:.5});io.observe(el)}
}
$$(".spin[data-sprite]").forEach(Spin);

/* ---------- Zeichnungen: leichte 3D-Neigung beim Darüberfahren ---------- */
if(!RED)$$(".stage").forEach(function(st){var im=$(":scope>img",st);if(!im)return;
  st.addEventListener("pointermove",function(e){var r=st.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;
    im.style.transform="perspective(900px) rotateY("+(x*18).toFixed(1)+"deg) rotateX("+(-y*14).toFixed(1)+"deg) scale(1.03)"});
  st.addEventListener("pointerleave",function(){im.style.transform=""})});

/* ---------- Suche ---------- */
var IDX=null,idxP=null;
function loadIdx(){if(IDX)return Promise.resolve(IDX);if(!idxP)idxP=fetch("/assets/search.json").then(function(r){return r.json()}).then(function(d){IDX=d.map(function(x){x.k=norm(x.n+" "+x.g+" "+(x.b||""));return x});return IDX});return idxP}
function norm(s){return String(s).toLowerCase().replace(/ä/g,"a").replace(/ö/g,"o").replace(/ü/g,"u").replace(/ß/g,"ss").replace(/[^a-z0-9]+/g," ").trim()}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function tier(v){return v>=85?1:v>=70?2:v>=55?3:4}
$$(".srch").forEach(function(box){
  var inp=$("input",box),res=$(".srch-res",box),sel=-1,items=[];
  function close(){box.classList.remove("open");sel=-1}
  function render(q){var n=norm(q);if(!n){close();return}
    var ws=n.split(" ");items=IDX.filter(function(x){return ws.every(function(w){return x.k.indexOf(w)>=0})});
    items.sort(function(a,b){var sa=norm(a.n).indexOf(n)===0?1:0,sb=norm(b.n).indexOf(n)===0?1:0;return sb-sa||b.s-a.s});
    items=items.slice(0,8);sel=-1;
    res.innerHTML=items.length?items.map(function(x,i){return '<a class="sr-i" role="option" id="sr'+i+'" href="'+x.u+'"><span class="th">'+(x.i?'<img src="'+x.i+'" alt="" loading="lazy">':'')+'</span><span><b>'+esc(x.n)+'</b><small>'+esc(x.g)+' · Platz '+x.r+'</small></span><span class="sc sm t'+tier(x.s)+'">'+Math.round(x.s)+'</span></a>'}).join("")
      :'<div class="sr-none">Nichts gefunden. Versuch es mit einer Marke, zum Beispiel „Samsung“ oder „Sony“.</div>';
    box.classList.add("open")}
  inp.addEventListener("focus",function(){loadIdx()});
  inp.addEventListener("input",function(){var q=inp.value;loadIdx().then(function(){if(inp.value===q)render(q)})});
  inp.addEventListener("keydown",function(e){var a=$$(".sr-i",res);
    if(e.key==="ArrowDown"||e.key==="ArrowUp"){if(!a.length)return;e.preventDefault();sel=(sel+(e.key==="ArrowDown"?1:-1)+a.length)%a.length;a.forEach(function(x,i){x.setAttribute("aria-selected",i===sel)});a[sel].scrollIntoView({block:"nearest"})}
    else if(e.key==="Enter"){var t=a[sel>=0?sel:0];if(t){e.preventDefault();location.href=t.href}}
    else if(e.key==="Escape"){inp.value="";close();inp.blur();document.querySelector("header.top").classList.remove("s-open")}});
  document.addEventListener("click",function(e){if(!box.contains(e.target)&&!e.target.closest(".s-btn"))close()});
});
var sb=$(".s-btn");if(sb)sb.addEventListener("click",function(){var h=$("header.top");h.classList.toggle("s-open");if(h.classList.contains("s-open")){var i=$(".srch input",h);i.focus()}});
document.addEventListener("keydown",function(e){if(e.key==="/"&&!/input|textarea|select/i.test((document.activeElement||{}).tagName||"")){var i=$(".srch input");if(i){e.preventDefault();if(getComputedStyle($(".srch")).display==="none")$("header.top").classList.add("s-open");i.focus()}}});

/* ---------- Rangliste sortieren und filtern ---------- */
$$("[data-rank]").forEach(function(wrap){
  var list=$(".rl",wrap),rows=$$(".rr",list),cnt=$("[data-cnt]",wrap),by="score",max=Infinity;
  function apply(){var vis=0;
    var s=rows.slice().sort(function(a,b){var pa=+a.dataset.p||1e9,pb=+b.dataset.p||1e9;
      if(by==="price")return pa-pb;if(by==="value")return (+b.dataset.v||0)-(+a.dataset.v||0);return (+a.dataset.r)-(+b.dataset.r)});
    s.forEach(function(r){var p=+r.dataset.p;var ok=max===Infinity||(p&&p<=max);r.hidden=!ok;if(ok)vis++;list.appendChild(r)});
    var em=$(".empty",wrap);if(em)em.hidden=vis>0;if(cnt)cnt.textContent=vis+" von "+rows.length}
  $$(".seg button",wrap).forEach(function(b){b.addEventListener("click",function(){by=b.dataset.sort;$$(".seg button",wrap).forEach(function(x){x.setAttribute("aria-pressed",x===b)});apply()})});
  var sl=$("select",wrap);if(sl)sl.addEventListener("change",function(){max=sl.value?+sl.value:Infinity;apply()});
});

/* ---------- Sprungleiste: aktiven Abschnitt markieren ---------- */
var jl=$$(".jump a");if(jl.length&&"IntersectionObserver" in window){var on=function(id){jl.forEach(function(a){a.classList.toggle("on",a.getAttribute("href")==="#"+id)})};
  var jo=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting)on(e.target.id)})},{rootMargin:"-30% 0px -60% 0px"});
  jl.forEach(function(a){var t=document.getElementById(a.getAttribute("href").slice(1));if(t)jo.observe(t)})}

/* ---------- Nach oben + Kaufleiste (Handy) ---------- */
var tt=$(".totop"),buy=$(".buybox"),sbar=$(".sticky-buy");
if(sbar)document.body.classList.add("has-sb");
function onScroll(){var y=window.scrollY||0;if(tt)tt.classList.toggle("on",y>900);
  if(sbar&&buy){var r=buy.getBoundingClientRect();sbar.classList.toggle("on",r.bottom<0)}}
window.addEventListener("scroll",onScroll,{passive:true});onScroll();
if(tt)tt.addEventListener("click",function(){window.scrollTo({top:0,behavior:RED?"auto":"smooth"})});
})();
