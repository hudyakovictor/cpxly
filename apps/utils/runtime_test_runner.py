from unittest import TestSuite
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.test.runner import DiscoverRunner


class PreparedDatabaseRunner(DiscoverRunner):
    """Only for explicitly provisioned disposable CI DB; never creates its schema."""

    def build_suite(self, *args, **kwargs):
        suite = super().build_suite(*args, **kwargs)
        def individual_tests(node):
            if isinstance(node, TestSuite):
                for child in node:
                    yield from individual_tests(child)
            else:
                yield node

        for test in individual_tests(suite):
            if isinstance(test, TransactionTestCase) and not isinstance(test, TestCase):
                raise ImproperlyConfigured("TransactionTestCase needs a reviewed runtime-role harness")
        return suite

    def setup_databases(self, **kwargs):
        if self.parallel != 1:
            raise ImproperlyConfigured("Prepared runtime tests cannot use parallel databases")
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            if cursor.fetchone()[0] != "capexly_runtime":
                raise ImproperlyConfigured("Runtime tests must use capexly_runtime")
        return []

    def teardown_databases(self, old_config, **kwargs):
        # No CREATE/DROP DB and no migrations by runtime; CI disposes project.
        pass
