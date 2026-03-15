const CACHE_NAME = "pipewire-eq-v1";
const staticAssets = [
  "/",
  "/static/css/main.css",
  "/static/css/round.min.css",
  "/static/js/main.js",
  "/static/js/theme-toggler.min.js",
];

self.addEventListener("install", async (event) => {
  console.log("[ServiceWorker] Installing...");
  const cache = await caches.open(CACHE_NAME);
  cache.addAll(staticAssets);
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
  
  // API calls must ALWAYS go to server - never cache API responses
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
  
  // Cache-first strategy for static assets
  if (request.method === "GET") {
    event.respondWith(
      caches.match(request).then((cacheResponse) => {
        // Return cached response if available
        if (cacheResponse) {
          return cacheResponse;
        }
        
        // Fetch from network if not in cache
        return fetch(request).then((response) => {
          // Cache successful responses
          if (response.status === 200) {
            const responseToCache = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(request, responseToCache);
            });
          }
          return response;
        }).catch((error) => {
          console.error("[ServiceWorker] Fetch failed:", error);
          // Fallback to cached version or offline page
          return caches.match("/") || new Response("Offline");
        });
      })
    );
  }
});
