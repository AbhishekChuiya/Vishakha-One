"""Public PWA metadata. No user content is cached by the service worker."""
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static
from django.views.decorators.http import require_GET


@require_GET
def manifest(request):
    data = {
        "id": "/",
        "name": "Vishakha One",
        "short_name": "Vishakha One",
        "description": "Vishakha employee services and company information",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#10263f",
        "icons": [
            {"src": static("pwa/icon-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": static("pwa/icon-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": static("pwa/icon-maskable-192.png"), "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
            {"src": static("pwa/icon-maskable-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    response = JsonResponse(data, content_type="application/manifest+json")
    response["Cache-Control"] = "no-cache"
    return response


@require_GET
def service_worker(request):
    # Intentionally no CacheStorage: avoids offline copies of employee information.
    icon = static("pwa/icon-192.png")
    code = '''/* Vishakha One online-first service worker v17.0 (push enabled) */
self.addEventListener('install', event => { self.skipWaiting(); });
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', event => {
  // All requests go to the network. Never cache authenticated HTML, APIs, media, or documents.
});
self.addEventListener('push', event => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch (e) { data = {body: event.data ? event.data.text() : ''}; }
  const title = data.title || 'Vishakha One';
  event.waitUntil(self.registration.showNotification(title, {
    body: data.body || '', icon: '__ICON__', badge: '__ICON__', tag: data.tag || undefined,
    data: {url: data.url || '/'}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target = new URL((event.notification.data && event.notification.data.url) || '/', self.location.origin).href;
  event.waitUntil(self.clients.matchAll({type: 'window', includeUncontrolled: true}).then(list => {
    for (const client of list) {
      if (new URL(client.url).origin === self.location.origin && 'focus' in client) {
        return client.focus().then(c => (c && 'navigate' in c) ? c.navigate(target) : c);
      }
    }
    return self.clients.openWindow(target);
  }));
});
'''.replace('__ICON__', icon)
    response = HttpResponse(code, content_type="text/javascript; charset=utf-8")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def readiness(request):
    """Public diagnostics page. Does not reveal internal server configuration."""
    from django.shortcuts import render
    return render(request, "portal/pwa_readiness.html", {"heading": "Install Vishakha One"})
