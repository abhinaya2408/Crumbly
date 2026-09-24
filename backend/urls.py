"""
backend/urls.py — top-level URL routing.

This wires up three things:
  1. The existing frontend HTML pages, served as plain Django
     templates at the SAME filenames the original ZIP used
     (so every <a href="customize.html"> link keeps working
     unmodified).
  2. The frontend's css/ and js/ folders, served at /css/ and /js/
     (again, matching the original relative paths in the HTML).
  3. The Django REST Framework API under /api/, plus /admin/ and
     uploaded media under /media/.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

admin.site.site_header = "Crumbly Admin"
admin.site.site_title = "Crumbly Admin"
admin.site.index_title = "Crumbly — College Bakery Ordering System"

# ---- Frontend pages (same filenames as the original ZIP) ----
frontend_pages = [
    path("", TemplateView.as_view(template_name="index.html"), name="home"),
    path("index.html", TemplateView.as_view(template_name="index.html")),
    path("student-login.html", TemplateView.as_view(template_name="student-login.html")),
    path("student-register.html", TemplateView.as_view(template_name="student-register.html")),
    path("student-profile.html", TemplateView.as_view(template_name="student-profile.html")),
    path("bakery-login.html", TemplateView.as_view(template_name="bakery-login.html")),
    path("customize.html", TemplateView.as_view(template_name="customize.html")),
    path("order-confirmation.html", TemplateView.as_view(template_name="order-confirmation.html")),
    path("order-details.html", TemplateView.as_view(template_name="order-details.html")),
    path("my-orders.html", TemplateView.as_view(template_name="my-orders.html")),
    path("notifications.html", TemplateView.as_view(template_name="notifications.html")),
    path("owner-dashboard.html", TemplateView.as_view(template_name="owner-dashboard.html")),
    path("owner-order-details.html", TemplateView.as_view(template_name="owner-order-details.html")),
    path("owner-pickup-slots.html", TemplateView.as_view(template_name="owner-pickup-slots.html")),
    path("owner-inventory.html", TemplateView.as_view(template_name="owner-inventory.html")),
    path("owner-analytics.html", TemplateView.as_view(template_name="owner-analytics.html")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("bakery.urls")),
    *frontend_pages,
]

# ---- Serve frontend/css and frontend/js at /css/ and /js/, and
#      uploaded media at /media/. django.contrib.staticfiles already
#      serves STATICFILES_DIRS while DEBUG=True through /static/, but
#      the original project references "css/..." and "js/..." with NO
#      /static/ prefix, so we add two extra static() mappings that
#      point at the exact same folders. This keeps every existing
#      <link>/<script> tag in the HTML working without any edits. ----
urlpatterns += static("/css/", document_root=settings.BASE_DIR / "frontend" / "css")
urlpatterns += static("/js/", document_root=settings.BASE_DIR / "frontend" / "js")
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
