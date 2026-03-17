const CACHE_NAME = "pipewire-eq-v1";
const staticAssets = [
  "/",
  "/static/fonts/assistant-v19-latin-regular.woff2",
  "/static/fonts/material-icons-round.woff2",
  "/static/css/main.min.css",
  "/static/css/round.min.css",
  "/static/js/main.min.js",
  "/static/js/theme-toggler.min.js",
  "/static/js/change-language.min.js",
  "/static/img/music_note.svg"
];

self.addEventListener("install", (event) => {
  console.log("[ServiceWorker] Installing...");
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      for (const url of staticAssets) {
        try {
          await cache.add(url);
          console.log(`[ServiceWorker] Cached: ${url}`);
        } catch (error) {
          console.error(`[ServiceWorker] Failed to cache: ${url}`, error);
        }
      }
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  console.log("[ServiceWorker] Activating...");
  // Clean up old caches when service worker is activated
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            console.log("[ServiceWorker] Deleting old cache:", cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;

  if (request.url.includes("/api/")) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({ error: "Offline - API not available" }),
          { status: 503, headers: { "Content-Type": "application/json" } }
        );
      })
    );
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => {
        return caches.match("/"); 
      })
    );
    return;
  }

  if (request.method === "GET") {
    event.respondWith(
      caches.match(request).then((cacheResponse) => {
        return cacheResponse || fetch(request).then((response) => {
          if (response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, responseToCache));
          }
          return response;
        });
      }).catch(() => {
          return caches.match("/static/img/music_note.svg");
      })
    );
  }
});
