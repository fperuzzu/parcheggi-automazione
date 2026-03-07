const CACHE = "parking-it-v1";
const SHELL = [
  "/parcheggi-automazione/",
  "/parcheggi-automazione/manifest.json",
];

// Installa: metti in cache solo la shell
self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL))
  );
  self.skipWaiting();
});

// Attiva: pulisci cache vecchie
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first, fallback alla cache per la shell
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);

  // Richieste cross-origin (iframe Streamlit) — lascia passare sempre
  if (url.origin !== self.location.origin) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Shell: network-first con fallback cache
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
