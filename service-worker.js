// service-worker.js

const CACHE_NAME = "ovens-lovins-v4";  // 👈 bump this when you change frontend
const urlsToCache = [
    "/",
    "/index.html",
    "/recipe.html",
    "/grocery.html",
    "/upload.html",
    "/css/app.css",
    "/js/api.js",
    "/manifest.json",
    "/icons/icon-48.png",
    "/icons/icon-72.png",
    "/icons/icon-96.png",
    "/icons/icon-128.png",
    "/icons/icon-192.png",
    "/icons/icon-256.png",
    "/icons/icon-512.png"
];

// Install
self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
    self.skipWaiting();
});

// Activate – clear old caches
self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys
                    .filter(k => k !== CACHE_NAME)
                    .map(k => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// Fetch – cache-first for GET only
self.addEventListener("fetch", event => {
    if (event.request.method !== "GET") {
        return;
    }

    event.respondWith(
        caches.match(event.request, { ignoreSearch: true }).then(resp => {
            if (resp) return resp;
            return fetch(event.request);
        })
    );
});
