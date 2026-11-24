const SHELL='onepiece-nouveau-v1-shell-20261124';
const PHOTOS='onepiece-confirmed-photos-v5';
const FILES=['./index.html','./manifest.webmanifest','./icon-192.png','./icon-512.png'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(SHELL).then(cache=>cache.addAll(FILES)));self.skipWaiting()});
self.addEventListener('activate',event=>{event.waitUntil(Promise.all([self.clients.claim(),caches.keys().then(keys=>Promise.all(keys.filter(key=>key.startsWith('onepiece-nouveau-')&&key!==SHELL).map(k=>caches.delete(k))))]))});
const isPhoto=url=>url.protocol==='https:'&&/^(?:(?:en|fr|asia-en)\.onepiece-cardgame\.com|one-piece\.cards|optcg-api\.arjunbansal-ai\.workers\.dev|limitlesstcg\.nyc3\.cdn\.digitaloceanspaces\.com)$/.test(url.hostname);
self.addEventListener('fetch',event=>{
 if(event.request.method!=='GET')return;
 const url=new URL(event.request.url);
 if(event.request.destination==='image'&&isPhoto(url)){event.respondWith(caches.open(PHOTOS).then(async cache=>(await cache.match(event.request))||fetch(event.request)));return;}
 if(url.origin!==self.location.origin||!url.href.startsWith(self.registration.scope))return;
 if(event.request.mode==='navigate'){
  event.respondWith((async()=>{const cache=await caches.open(SHELL);try{const r=await fetch(event.request,{cache:'no-store'});if(r.ok)await cache.put('./index.html',r.clone());return r;}catch{return (await cache.match('./index.html'))||Response.error();}})());return;
 }
 if(FILES.some(f=>new URL(f,self.registration.scope).pathname===url.pathname))event.respondWith(caches.open(SHELL).then(async c=>(await c.match(event.request))||fetch(event.request)));
});
self.addEventListener('message',event=>{
 if(event.data?.type!=='CACHE_VALID_IMAGE'||typeof event.data.url!=='string')return;
 try{const url=new URL(event.data.url);if(!isPhoto(url))return;
 event.waitUntil(caches.open(PHOTOS).then(async cache=>{const req=new Request(url.href,{mode:'no-cors',credentials:'omit',referrerPolicy:'no-referrer'});if(await cache.match(req))return;const response=await fetch(req);if(response.ok||response.type==='opaque')await cache.put(req,response);}).catch(()=>{}));}catch{}
});
