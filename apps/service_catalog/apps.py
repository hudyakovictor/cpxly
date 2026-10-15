from django.apps import AppConfig


class ServiceCatalogConfig(AppConfig):
    name = "apps.service_catalog"
    label = "service_catalog"
    verbose_name = "Каталог услуг"
    default_auto_field = "django.db.models.BigAutoField"
