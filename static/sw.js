const CACHE_NAME = 'digitaldarling-v2';

// Only pre-cache truly static assets — never server-rendered HTML pages.
// Pre-caching auth-gated HTML during SW install causes Chrome on Android to
// flag the app as incompatible (install fails because the pages return 3xx or
// require cookies that aren't available during the install event).
const PRE_CACHE_ASSETS = [
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

// ── Install: cache only static assets ─────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRE_CACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// ── Activate: purge old caches ─────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// ── Fetch ──────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  // Never intercept non-GET or cross-origin requests
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin) {
    // External resources (Google Fonts, CDN) — network only, no caching
    return;
  }

  // Static assets (/static/) — Cache First
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((res) => {
          if (res.ok) {
            caches.open(CACHE_NAME).then((c) => c.put(event.request, res.clone()));
          }
          return res;
        });
      })
    );
    return;
  }

  // Auth routes — always Network First, never cache
  if (url.pathname.startsWith('/auth/')) {
    event.respondWith(fetch(event.request));
    return;
  }

  // All other pages — Network First with cache fallback
  // (keeps content fresh; falls back to cached version if offline)
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        if (res.ok) {
          caches.open(CACHE_NAME).then((c) => c.put(event.request, res.clone()));
        }
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});
