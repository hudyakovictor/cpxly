from django.urls import path
from . import views

app_name = "selfservice"
urlpatterns = [
    path("", views.landing, name="landing"),
    path("cabinet/", views.catalog, name="catalog"),
    path("cabinet/start/", views.onboarding, name="onboarding"),
    path("cabinet/services/payment-claim/", views.create_claim, name="claim"),
    path("cabinet/requests/<uuid:request_id>/", views.result, name="result"),
    path("cabinet/requests/<uuid:request_id>/status/", views.request_status, name="status"),
    path("cabinet/requests/<uuid:request_id>/download/", views.download, name="download"),
    path("cabinet/access/", views.access_settings, name="access"),
    path("cabinet/access/add/", views.grant_access, name="grant_access"),
    path("cabinet/access/<int:membership_id>/revoke/", views.revoke_access, name="revoke_access"),
    path("cabinet/switch/", views.switch_company, name="switch_company"),
]
