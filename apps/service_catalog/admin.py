from django.contrib import admin
from .models import ServiceCatalogEntry


@admin.register(ServiceCatalogEntry)
class ServiceCatalogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "kind", "source_decision", "stage",
        "handler_connected_display", "can_be_requested_display", "source_conflict",
    )
    list_filter = ("kind", "stage", "source_decision", "source_conflict")
    search_fields = ("code", "name", "research_description", "notes")
    ordering = ("code",)
    list_per_page = 60
    actions = None
    readonly_fields = (
        "handler_connected_display", "can_be_requested_display", "source_kind",
        "source_decision", "research_description", "source_blocker", "source_gate",
        "verification_note", "source_reference", "source_conflict",
    )
    fieldsets = (
        ("Каталог", {"fields": ("code", "name", "kind", "stage", "notes")}),
        ("Подключение — заглушки выключены", {
            "fields": ("handler_connected_display", "can_be_requested_display", "is_visible_to_clients", "accepts_requests"),
        }),
        ("Исследование F1 — не подтверждение готовности", {
            "fields": ("source_kind", "source_decision", "research_description", "source_blocker", "source_gate", "verification_note", "source_reference", "source_conflict"),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return (*fields, "code") if obj else fields

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description="Обработчик подключён")
    def handler_connected_display(self, obj):
        return obj.handler_connected

    @admin.display(boolean=True, description="Можно заказать")
    def can_be_requested_display(self, obj):
        return obj.can_be_requested
