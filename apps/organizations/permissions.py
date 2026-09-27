from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from apps.organizations.models import Membership, Organization


def get_membership(user, organization: Organization) -> Membership | None:
    return Membership.objects.filter(user=user, organization=organization).first()


def require_membership(user, organization: Organization) -> Membership:
    membership = get_membership(user, organization)
    if membership is None:
        raise PermissionDenied('You do not have access to this organization.')
    return membership


def require_role(user, organization: Organization, allowed_roles: list[str]) -> Membership:
    membership = require_membership(user, organization)
    if membership.role not in allowed_roles:
        raise PermissionDenied('You do not have permission to perform this action.')
    return membership
