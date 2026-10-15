from django.contrib import admin
from .models import Company, DispatchRecord, Membership, RequestEvent, ServiceRequest


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "created_at")
    search_fields = ("name",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("company", "user", "role")
    list_filter = ("role",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "company", "code", "state", "created_at")
    readonly_fields = [field.name for field in ServiceRequest._meta.fields]
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RequestEvent)
class RequestEventAdmin(admin.ModelAdmin):
    list_display = ("request", "kind", "created_at")
    readonly_fields = [field.name for field in RequestEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DispatchRecord)
class DispatchRecordAdmin(admin.ModelAdmin):
    list_display = ("request", "publish_attempts", "last_published_at", "next_attempt_at", "last_error_code")
    readonly_fields = [field.name for field in DispatchRecord._meta.fields]
    actions = None

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
