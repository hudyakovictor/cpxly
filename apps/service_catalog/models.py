from django.core.exceptions import ValidationError
from django.db import models
from .registry import has_handler


class ServiceCatalogEntry(models.Model):
    """Global service metadata, not company documents, requests, or task management."""
    code = models.CharField(max_length=16, unique=True, verbose_name='ID каталога')
    name = models.CharField(max_length=255, verbose_name='Название')
    kind = models.CharField(max_length=16, choices=[('service', 'Клиентская услуга'), ('bundle', 'Пакет / конвейер'), ('platform', 'Функция платформы'), ('commercial', 'Коммерческая гипотеза')], verbose_name='Тип записи')
    stage = models.CharField(max_length=20, default='placeholder', choices=[('placeholder', 'Заглушка'), ('specification', 'Спецификация'), ('development', 'В разработке'), ('disabled', 'Отключено')], verbose_name='Фактический этап')
    is_visible_to_clients = models.BooleanField(default=False, verbose_name='Показывать клиентам', help_text='Заглушки скрыты. Для включения нужен подключённый обработчик.')
    accepts_requests = models.BooleanField(default=False, verbose_name='Принимать заявки', help_text='Нельзя включить без обработчика и видимости в кабинете.')
    source_kind = models.CharField(max_length=64, blank=True, default='', verbose_name='Класс в исходном каталоге')
    source_decision = models.CharField(max_length=64, blank=True, default='', verbose_name='Приоритет F1 — не готовность')
    research_description = models.TextField(blank=True, default='', verbose_name='Описание из исследования — не обещание')
    source_blocker = models.TextField(blank=True, default='', verbose_name='Блокер из исходника — требует проверки')
    source_gate = models.TextField(blank=True, default='', verbose_name='Условие перехода из исходника')
    verification_note = models.TextField(blank=True, default='', verbose_name='Оговорки проверки')
    source_reference = models.TextField(blank=True, default='', verbose_name='Происхождение записи')
    source_conflict = models.BooleanField(default=False, verbose_name='Нужно уточнить классификацию')
    notes = models.TextField(blank=True, default='', verbose_name='Заметки администратора')

    class Meta:
        ordering = ["code"]
        verbose_name = "запись каталога"
        verbose_name_plural = "услуги и функции платформы"

    def __str__(self):
        return f"{self.code} · {self.name}"

    @property
    def handler_connected(self):
        return has_handler(self.code)

    @property
    def can_be_requested(self):
        return (
            self.kind in {"service", "bundle"}
            and self.is_visible_to_clients
            and self.accepts_requests
            and self.handler_connected
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.kind not in {"service", "bundle"} and (self.is_visible_to_clients or self.accepts_requests):
            errors["is_visible_to_clients"] = "Функции платформы и GTM не являются отдельными клиентскими услугами."
        if not self.handler_connected and (self.is_visible_to_clients or self.accepts_requests):
            errors["accepts_requests"] = "Это заглушка: сначала подключите и проверьте обработчик услуги."
        if self.accepts_requests and not self.is_visible_to_clients:
            errors["is_visible_to_clients"] = "Скрытая услуга не может принимать клиентские заявки."
        if errors:
            raise ValidationError(errors)
