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

// Install
self.addEventListener("install", event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(urlsToCache);
        })
    );
    self.skipWaiting();
});

// Activate
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

// Fetch
self.addEventListener("fetch", event => {
    event.respondWith(
        caches.match(event.request).then(resp => {
            return (
                resp ||
                fetch(event.request).then(fetchResp => {
                    return fetchResp;
                })
            );
        })
    );
});
