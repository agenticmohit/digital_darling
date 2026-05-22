const CACHE_NAME = 'digitaldarling-v1';
const PRE_CACHE_ASSETS = [
  '/',
  '/decode',
  '/history',
  '/profile',
  '/pricing',
  '/static/manifest.json'
];

// Install service worker and pre-cache main pages
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRE_CACHE_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate service worker and clear old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Intercept fetch requests
self.addEventListener('fetch', (event) => {
  // Only skip/process GET requests. POST requests (like /decode, /auth/login) must hit the network directly.
  if (event.request.method !== 'GET') {
    return;
  }

  const url = new URL(event.request.url);

  // Strategy 1: Static assets (images, manifest, fonts) -> Cache First
  if (url.pathname.startsWith('/static/') || url.hostname.includes('fonts.gstatic.com')) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(event.request).then((networkResponse) => {
          return caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, networkResponse.clone());
            return networkResponse;
          });
        });
      })
    );
    return;
  }

  // Strategy 2: HTMX requests or /auth/ routes -> Network First (with cache fallback)
  const isHtmx = event.request.headers.get('HX-Request') !== null;
  const isAuth = url.pathname.startsWith('/auth/');
  
  if (isHtmx || isAuth) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          // If response is valid, cache it
          if (networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseClone);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // Network failed, serve from cache if available
          return caches.match(event.request);
        })
    );
    return;
  }

  // Strategy 3: Everything else (Standard HTML page navigation) -> Stale While Revalidate
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return networkResponse;
      });
      return cachedResponse || fetchPromise;
    })
  );
});
