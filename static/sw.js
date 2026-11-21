/* Service worker: caches static assets so the app works offline. */

const CACHE_NAME = "workflow-v1";

// Assets cached on install (the green theme, logo, and vendor files)
const PRECACHE = [
    "/static/vendor/bootstrap.min.css",
    "/static/vendor/bootstrap.bundle.min.js",
    "/static/css/style.css",
    "/static/js/script.js",
    "/static/img/JERGA.jpg",
    "/static/manifest.json",
    "/offline",
];

// Install: pre-cache the core assets
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
    );
    self.skipWaiting();
});

// Activate: remove old caches from previous versions
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

// Fetch: serve cached files when offline
self.addEventListener("fetch", (event) => {
    const request = event.request;

    // Only handle GET requests in the same origin
    if (request.method !== "GET" || !request.url.startsWith(self.location.origin)) {
        return;
    }

    // Page navigations: try network first, fall back to cache/offline page
    if (request.mode === "navigate") {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Keep a copy of pages for offline use
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
                    return response;
                })
                .catch(() =>
                    caches.match(request).then((cached) => cached || caches.match("/offline"))
                )
        );
        return;
    }

    // Static assets: cache first, then network
    event.respondWith(
        caches.match(request).then((cached) => {
            if (cached) return cached;
            return fetch(request).then((response) => {
                const copy = response.clone();
                caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
                return response;
            });
        })
    );
});
