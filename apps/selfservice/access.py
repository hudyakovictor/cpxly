from uuid import UUID
from django.http import Http404, HttpResponseForbidden
from .models import Membership


def membership(request):
    memberships = Membership.objects.select_related("company").filter(user=request.user)
    selected = request.session.get("capexly_company")
    try:
        selected = UUID(str(selected)) if selected else None
    except (ValueError, TypeError, AttributeError):
        selected = None
    current = memberships.filter(company_id=selected).first() if selected else None
    current = current or memberships.order_by("pk").first()
    if current:
        request.session["capexly_company"] = str(current.company_id)
    return current


def require_writer(member):
    if member is None or member.role not in {"owner", "member"}:
        return HttpResponseForbidden("Недостаточно прав для этого действия")
    return None
