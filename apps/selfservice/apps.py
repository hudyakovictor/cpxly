from django.apps import AppConfig


class SelfServiceConfig(AppConfig):
    name = "apps.selfservice"
    label = "selfservice"
    verbose_name = "Клиентский сервис"
    default_auto_field = "django.db.models.BigAutoField"
