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
    code = '''/* Vishakha One online-first service worker v16.43 */
self.addEventListener('install', event => { self.skipWaiting(); });
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
self.addEventListener('fetch', event => {
  // All requests go to the network. Never cache authenticated HTML, APIs, media, or documents.
});
'''
    response = HttpResponse(code, content_type="text/javascript; charset=utf-8")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-store"
    return response


@require_GET
def readiness(request):
    """Public diagnostics page. Does not reveal internal server configuration."""
    from django.shortcuts import render
    return render(request, "portal/pwa_readiness.html", {"heading": "Install Vishakha One"})
