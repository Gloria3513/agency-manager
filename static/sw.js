"""
Service Worker for PWA
오프라인 지원 및 캐싱
"""

CACHE_NAME = 'agency-manager-v1'
urls_to_cache = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/manifest.json'
]

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(urls_to_cache))
    )
})

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                return response || fetch(event.request)
            })
    )
})

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((cacheName) => cacheName !== CACHE_NAME)
                    .map((cacheName) => caches.delete(cacheName))
            )
        })
    )
})
