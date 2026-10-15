import uuid
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from apps.service_catalog.models import ServiceCatalogEntry
from .access import membership, require_writer
from .forms import ClaimForm, CompanyForm
from .models import Company, DispatchRecord, Membership, RequestEvent, ServiceRequest
from .tasks import enqueue_case


def landing(request):
    return render(request, "capexly/landing.html")


@login_required
def onboarding(request):
    if membership(request):
        return redirect("selfservice:catalog")
    form = CompanyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if membership(request):
                return redirect("selfservice:catalog")
            company = Company.objects.create(name=form.cleaned_data["name"])
            Membership.objects.create(company=company, user=request.user, role="owner")
        request.session["capexly_company"] = str(company.pk)
        return redirect("selfservice:catalog")
    return render(request, "capexly/onboarding.html", {"form": form})


@login_required
@never_cache
def catalog(request):
    member = membership(request)
    if not member:
        return redirect("selfservice:onboarding")
    services = []
    if settings.CAPEXLY_PILOT_ENABLED:
        services = [item for item in ServiceCatalogEntry.objects.filter(code="S-03", is_visible_to_clients=True, accepts_requests=True) if item.can_be_requested]
    return render(request, "capexly/catalog.html", {"member": member, "services": services,
        "cases": ServiceRequest.objects.filter(company=member.company)[:10]})


@login_required
@never_cache
def create_claim(request):
    member = membership(request)
    denied = require_writer(member)
    if denied:
        return denied
    entry = get_object_or_404(ServiceCatalogEntry, code="S-03")
    if not settings.CAPEXLY_PILOT_ENABLED or not settings.CAPEXLY_SANDBOX_MODE or not entry.can_be_requested:
        raise Http404
    form = ClaimForm(request.POST or None, initial={"creditor": member.company.name, "idempotency_key": uuid.uuid4()})
    if not settings.CAPEXLY_EXTERNAL_AI_ENABLED:
        form.fields["use_ai"].disabled = True
        form.fields["use_ai"].help_text = "Внешний ИИ не подключён. Шаблонный черновик доступен без него."
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            Company.objects.select_for_update().get(pk=member.company_id)
            # Recheck permission under the transaction, never trust a submitted role/org.
            if not Membership.objects.filter(company=member.company, user=request.user, role__in=["owner", "member"]).exists():
                return HttpResponseForbidden()
            previous = ServiceRequest.objects.filter(company=member.company, idempotency_key=form.cleaned_data["idempotency_key"]).first()
            if previous:
                return redirect("selfservice:result", request_id=previous.pk)
            since = timezone.now() - timedelta(days=1)
            if ServiceRequest.objects.filter(company=member.company, created_at__gte=since).count() >= 20:
                form.add_error(None, "Лимит синтетического пилота: 20 заявок компании за последние сутки.")
            else:
                case, created = ServiceRequest.objects.get_or_create(company=member.company,
                    idempotency_key=form.cleaned_data["idempotency_key"], defaults={"actor": request.user,
                    "facts": form.normalized, "use_ai": form.cleaned_data["use_ai"]})
                if created:
                    DispatchRecord.objects.create(request=case)
                    RequestEvent.objects.create(request=case, kind="submitted")
                    transaction.on_commit(lambda: enqueue_case(case.pk))
                return redirect("selfservice:result", request_id=case.pk)
    return render(request, "capexly/claim_form.html", {"member": member, "form": form})


def scoped_case(request, request_id):
    member = membership(request)
    if not member:
        raise Http404
    return get_object_or_404(ServiceRequest, pk=request_id, company=member.company), member


@login_required
@never_cache
def result(request, request_id):
    case, member = scoped_case(request, request_id)
    return render(request, "capexly/result.html", {"case": case, "member": member})


@login_required
@never_cache
def request_status(request, request_id):
    case, _ = scoped_case(request, request_id)
    return JsonResponse({"state": case.state})


@login_required
@never_cache
def download(request, request_id):
    case, _ = scoped_case(request, request_id)
    if case.state != "ready" or not case.result_file:
        raise Http404
    response = FileResponse(case.result_file.open("rb"), as_attachment=True,
        filename=f"capexly-S03-{case.pk}.docx", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@never_cache
def access_settings(request):
    member = membership(request)
    if not member:
        return redirect("selfservice:onboarding")
    return render(request, "capexly/access.html", {"member": member,
        "memberships": Membership.objects.select_related("user").filter(company=member.company)})


@login_required
@require_POST
def grant_access(request):
    member = membership(request)
    if not member or member.role != "owner":
        return HttpResponseForbidden()
    role = request.POST.get("role")
    if role not in {"member", "viewer"}:
        return HttpResponseForbidden()
    email = request.POST.get("email", "").strip()
    users = get_user_model().objects.filter(email__iexact=email)
    if users.count() != 1:
        messages.error(request, "Не удалось добавить доступ. Нужна существующая учётная запись с однозначным email.")
        return redirect("selfservice:access")
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=member.company_id)
        if not Membership.objects.filter(pk=member.pk, role="owner").exists():
            return HttpResponseForbidden()
        target, created = Membership.objects.get_or_create(company=member.company, user=users.first(), defaults={"role": role})
        if not created:
            messages.info(request, "У пользователя уже есть доступ; роль автоматически не изменена.")
    return redirect("selfservice:access")


@login_required
@require_POST
def revoke_access(request, membership_id):
    member = membership(request)
    if not member or member.role != "owner":
        return HttpResponseForbidden()
    with transaction.atomic():
        Company.objects.select_for_update().get(pk=member.company_id)
        if not Membership.objects.filter(pk=member.pk, role="owner").exists():
            return HttpResponseForbidden()
        target = get_object_or_404(Membership, pk=membership_id, company=member.company)
        if target.role == "owner":
            return HttpResponseForbidden("Владельца нельзя удалить этим действием")
        target.delete()
    return redirect("selfservice:access")


@login_required
@require_POST
def switch_company(request):
    try:
        company_id = uuid.UUID(request.POST.get("company_id", ""))
    except (ValueError, TypeError, AttributeError):
        raise Http404 from None
    selected = get_object_or_404(Membership, user=request.user, company_id=company_id)
    request.session["capexly_company"] = str(selected.company_id)
    return redirect("selfservice:catalog")
