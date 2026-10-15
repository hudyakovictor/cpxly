"""Integration tests prepared for PostgreSQL; NOT executed in the agent sandbox."""
import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from apps.service_catalog.models import ServiceCatalogEntry
from apps.selfservice.models import Company, DispatchRecord, Membership, ServiceRequest

class CompanyAccessTests(TestCase):
    def setUp(self):
        User=get_user_model()
        self.a=User.objects.create_user(email="a@example.test",password="test-only-password",username="a")
        self.b=User.objects.create_user(email="b@example.test",password="test-only-password",username="b")
        self.ca=Company.objects.create(name="Synthetic A")
        self.cb=Company.objects.create(name="Synthetic B")
        self.ma=Membership.objects.create(company=self.ca,user=self.a,role="owner")
        Membership.objects.create(company=self.cb,user=self.b,role="owner")
        self.case=ServiceRequest.objects.create(company=self.ca,actor=self.a,idempotency_key=uuid.uuid4())
    def test_anonymous_redirect(self):
        self.assertEqual(self.client.get("/cabinet/").status_code,302)
    def test_other_company_hidden(self):
        self.client.force_login(self.b)
        for suffix in ["", "status/", "download/"]:
            self.assertEqual(self.client.get(f"/cabinet/requests/{self.case.pk}/{suffix}").status_code,404)
    def test_viewer_cannot_add_access(self):
        self.ma.role="viewer"; self.ma.save()
        self.client.force_login(self.a)
        self.assertEqual(self.client.post("/cabinet/access/add/",{"email":self.b.email,"role":"member"}).status_code,403)
    def test_owner_cannot_be_revoked(self):
        self.client.force_login(self.a)
        self.assertEqual(self.client.post(f"/cabinet/access/{self.ma.pk}/revoke/").status_code,403)
    def test_invalid_company_id(self):
        self.client.force_login(self.a)
        self.assertEqual(self.client.post("/cabinet/switch/",{"company_id":"invalid"}).status_code,404)
    def test_revoked_membership_hides_request(self):
        self.client.force_login(self.a); self.ma.delete()
        self.assertEqual(self.client.get(f"/cabinet/requests/{self.case.pk}/status/").status_code,404)

    @override_settings(CAPEXLY_PILOT_ENABLED=True, CAPEXLY_SANDBOX_MODE=True)
    def test_viewer_cannot_submit(self):
        self.ma.role="viewer"; self.ma.save(); self.client.force_login(self.a)
        self.assertEqual(self.client.post("/cabinet/services/payment-claim/",{}).status_code,403)

    @override_settings(CAPEXLY_PILOT_ENABLED=True, CAPEXLY_SANDBOX_MODE=True, CAPEXLY_EXTERNAL_AI_ENABLED=False)
    def test_idempotency_one_submission(self):
        item=ServiceCatalogEntry.objects.get(code="S-03")
        item.is_visible_to_clients=True;item.accepts_requests=True;item.save()
        self.client.force_login(self.a)
        from .test_engine import sample
        data=sample();data["idempotency_key"]=str(uuid.uuid4())
        with patch("apps.selfservice.views.enqueue_case") as queue:
            with self.captureOnCommitCallbacks(execute=True):
                first=self.client.post("/cabinet/services/payment-claim/",data)
            with self.captureOnCommitCallbacks(execute=True):
                second=self.client.post("/cabinet/services/payment-claim/",data)
            self.assertEqual(first.status_code,302)
            self.assertEqual(first.url,second.url)
            queue.assert_called_once()
        self.assertEqual(ServiceRequest.objects.filter(company=self.ca,idempotency_key=data["idempotency_key"]).count(),1)
        self.assertEqual(DispatchRecord.objects.filter(request__company=self.ca,request__idempotency_key=data["idempotency_key"]).count(),1)

    def test_catalog_template_renders(self):
        self.client.force_login(self.a)
        response=self.client.get("/cabinet/")
        self.assertEqual(response.status_code,200)
        self.assertContains(response,"Что подготовим сегодня?")

    def test_csrf_required_for_access_mutation(self):
        from django.test import Client
        client=Client(enforce_csrf_checks=True);client.force_login(self.a)
        self.assertEqual(client.post("/cabinet/access/add/",{"email":self.b.email,"role":"member"}).status_code,403)
