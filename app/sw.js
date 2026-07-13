// sw.js — Cache de l'esquelet estàtic de l'app perquè funcioni offline.
// IMPORTANT: data/scores.json mai es serveix des de cache aquí — es vol
// sempre la versió més fresca (ja ho gestiona app.js amb cache: "no-store").

const CACHE_NAME = "stock-analyzer-shell-v1";
const SHELL_FILES = ["./", "index.html", "styles.css", "app.js", "manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Dades: sempre xarxa, mai cache (necessitem el scores.json d'avui)
  if (url.pathname.includes("/data/")) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Esquelet de l'app: cache-first amb fallback a xarxa
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});

// ---------- Web Push ----------

self.addEventListener("push", (event) => {
  let payload = { title: "Stock Analyzer", body: "Tens novetats al rànquing." };
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (e) {
      payload.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(payload.title || "Stock Analyzer", {
      body: payload.body || "",
      icon: "icons/icon-192.png",
      badge: "icons/icon-192.png",
      data: { url: payload.url || "./" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "./";
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
