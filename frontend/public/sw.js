// Turuncu Randevu — service worker (network-first + offline fallback).
const CACHE_NAME = 'turuncu-randevu-v8';
const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/apple-touch-icon.png',
  '/offline.html',
  '/css/theme.css',
  '/js/shared/theme.js',
  '/js/shared/tailwind-config.js',
  '/js/shared/api.js',
  '/js/shared/auth.js',
  '/js/shared/toast.js',
  '/js/shared/shell.js',
  '/js/shared/topnav.js',
  '/js/shared/datepicker.js',
  '/js/shared/confirm-modal.js',
  '/js/shared/pwa-install.js',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => Promise.allSettled(APP_SHELL.map((u) => cache.add(u)))),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))),
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.pathname.startsWith('/api/')) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached || caches.match('/offline.html'))),
  );
});
