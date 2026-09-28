from apps.organizations.models import Organization


def sidebar_organizations(request) -> dict:
    if not request.user.is_authenticated:
        return {'sidebar_organizations': []}
    organizations = Organization.objects.filter(
        memberships__user=request.user
    ).order_by('name')
    return {'sidebar_organizations': organizations}
