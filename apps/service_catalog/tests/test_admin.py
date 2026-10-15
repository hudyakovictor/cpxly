from django.test import TestCase
from django.urls import reverse
from apps.users.models import CustomUser


class CatalogAdminPermissionTests(TestCase):
    def test_customer_is_not_given_admin_access(self):
        user = CustomUser.objects.create_user(username="catalog-customer@example.test")
        self.client.force_login(user)
        response = self.client.get(reverse("admin:service_catalog_servicecatalogentry_changelist"))
        self.assertEqual(response.status_code, 302)

    def test_staff_without_model_permission_is_denied(self):
        user = CustomUser.objects.create_user(username="catalog-staff@example.test", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(reverse("admin:service_catalog_servicecatalogentry_changelist"))
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_view_catalog(self):
        user = CustomUser.objects.create_user(
            username="catalog-admin@example.test", is_staff=True, is_superuser=True,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("admin:service_catalog_servicecatalogentry_changelist"))
        self.assertEqual(response.status_code, 200)
