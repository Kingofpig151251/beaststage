/* 百獸台 service worker
   策略：
   - 導航（HTML）／頁面：network-first → 有網一定攞最新版，離線先用快取
   - 圖片、音效：cache-first（檔名不變、內容少變）
   - /api/*：唔攔，永遠直上網絡（題庫唯一真相源在雲端）
*/
const CACHE = "beast-v1";
const SHELL = [
  "/", "/edit",
  "/manifest.json",
  "/icon-192.png", "/icon-512.png", "/apple-touch-icon.png",
  "/art/team/turtle.webp", "/art/team/fox.webp", "/art/team/whale.webp", "/art/team/octopus.webp",
  "/art/team/bee.webp", "/art/team/flamingo.webp", "/art/team/dolphin.webp", "/art/team/bear.webp",
  "/sfx/dingdong.mp3", "/sfx/whoosh.mp3", "/sfx/countdown.mp3", "/sfx/whistle.mp3",
  "/sfx/settle.mp3", "/sfx/champion.mp3", "/sfx/tick.mp3", "/sfx/drums.mp3",
  "/sfx/snare.mp3", "/sfx/tap.mp3"
];

self.addEventListener("install", e => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    await Promise.all(SHELL.map(u => c.add(u).catch(() => {})));
    self.skipWaiting();
  })());
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    self.clients.claim();
  })());
});

async function networkFirst(req, timeout = 2500) {
  const c = await caches.open(CACHE);
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeout);
    const res = await fetch(req, { signal: ctrl.signal });
    clearTimeout(t);
    if (res && res.ok) c.put(req, res.clone());
    return res;
  } catch (e) {
    const hit = await c.match(req, { ignoreSearch: true });
    return hit || Response.error();
  }
}

async function cacheFirst(req) {
  const c = await caches.open(CACHE);
  const hit = await c.match(req, { ignoreSearch: true });
  if (hit) return hit;
  const res = await fetch(req);
  if (res && res.ok) c.put(req, res.clone());
  return res;
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return;          // 題庫／API 一律走網絡
  if (req.mode === "navigate") { e.respondWith(networkFirst(req)); return; }
  e.respondWith(cacheFirst(req));
});
