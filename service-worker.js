// service-worker.js

const CACHE_NAME = "ovens-lovins-v1";
const urlsToCache = [
    "/",
    "/index.html",
    "/upload.html",
    "/recipe.html",
    "/grocery.html",
    "/css/app.css",
    "/js/api.js",
    "/manifest.json"
];

self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
    );
    self.skipWaiting();
});

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

self.addEventListener("fetch", event => {
    // Don't mess with POST/PUT/etc. – let API calls go through normally
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
