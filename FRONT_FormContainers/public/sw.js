/* eslint-disable no-restricted-globals */
const CACHE_VERSION = "v1";
const CACHE_NAME = `formcontainers-${CACHE_VERSION}`;
const STATIC_ASSETS = [
  "/",
  "/offline",
  "/favicon.ico",
  "/icons/icon-96x96.png",
  "/icons/icon-180x180.png",
  "/icons/icon-192x192.png",
  "/icons/icon-512x512.png",
  "/icons/icon-maskable-512x512.png",
  "/screenshots/screenshot-wide-1280x720.png",
  "/screenshots/screenshot-mobile-750x1334.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("formcontainers-") && key !== CACHE_NAME)
            .map((key) => caches.delete(key)),
        ),
      ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;

  if (request.method !== "GET") {
    return;
  }

  const requestURL = new URL(request.url);

  // Solo gestionamos peticiones dentro del mismo origen
  if (requestURL.origin !== self.location.origin) {
    return;
  }

  // Dejamos pasar APIs o recursos dinamicos sensibles sin cachear
  if (requestURL.pathname.startsWith("/api")) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          return response;
        })
        .catch(async () => {
          const cachedResponse = await caches.match(request);
          if (cachedResponse) {
            return cachedResponse;
          }

          return caches.match("/offline");
        }),
    );
    return;
  }

  event.respondWith(
    caches.match(request).then(
      (cachedResponse) =>
        cachedResponse ||
        fetch(request)
          .then((response) => {
            if (
              response &&
              response.status === 200 &&
              response.type === "basic" &&
              !requestURL.pathname.startsWith("/_next/")
            ) {
              const responseClone = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
            }
            return response;
          })
          .catch(() => cachedResponse),
    ),
  );
});
