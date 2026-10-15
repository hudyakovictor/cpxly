from unittest import skipUnless
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.test import TestCase
from apps.users.models import CustomUser


@skipUnless(getattr(settings, "RUN_RUNTIME_ACCESS_TESTS", False), "Requires isolated runtime-role CI DB")
class RuntimeRoleTests(TestCase):
    def test_dml_works(self):
        user = CustomUser.objects.create_user(username="runtime-synthetic@example.test")
        user.first_name = "synthetic"
        user.save(update_fields=["first_name"])
        self.assertEqual(CustomUser.objects.get(pk=user.pk).first_name, "synthetic")
        user.delete()

    def test_role_attributes(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_user, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole "
                "FROM pg_roles WHERE rolname = current_user"
            )
            self.assertEqual(cursor.fetchone(), ("capexly_runtime", False, False, False, False))

    def assert_denied(self, sql):
        with self.assertRaises(DatabaseError) as failure:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql)
        self.assertEqual(getattr(failure.exception.__cause__, "sqlstate", None), "42501")

    def test_ddl_and_role_escalation_denied(self):
        self.assert_denied("CREATE TABLE public.runtime_should_not_exist (id integer)")
        self.assert_denied("ALTER TABLE users_customuser ADD COLUMN runtime_should_not_exist integer")
        self.assert_denied("ALTER TABLE users_customuser DISABLE ROW LEVEL SECURITY")
        self.assert_denied("SET ROLE capexly_migrator")
        self.assert_denied("CREATE POLICY runtime_should_not_exist ON users_customuser USING (true)")
