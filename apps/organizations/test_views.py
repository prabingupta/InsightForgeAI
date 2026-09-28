from django.test import TestCase
from django.urls import reverse

from apps.core.factories import add_member, create_organization, create_user
from apps.organizations.models import Membership


class InviteMemberRoleTests(TestCase):
    def setUp(self) -> None:
        self.owner = create_user('owner_a')
        self.admin = create_user('admin_a')
        self.target = create_user('target')
        self.organization = create_organization('Acme', self.owner)
        add_member(self.admin, self.organization, Membership.Role.ADMIN)
        self.invite_url = reverse('organizations:invite', kwargs={'slug': 'acme'})

    def test_invite_form_does_not_offer_the_owner_role(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('organizations:detail', kwargs={'slug': 'acme'}))
        self.assertNotContains(response, '<option value="owner">')

    def test_owner_role_cannot_be_granted_by_invite(self):
        self.client.force_login(self.admin)
        self.client.post(self.invite_url, {'username': 'target', 'role': 'owner'})
        self.assertFalse(
            Membership.objects.filter(user=self.target, organization=self.organization).exists()
        )

    def test_valid_invite_still_works(self):
        self.client.force_login(self.owner)
        self.client.post(self.invite_url, {'username': 'target', 'role': 'analyst'})
        membership = Membership.objects.get(user=self.target, organization=self.organization)
        self.assertEqual(membership.role, Membership.Role.ANALYST)

    def test_viewer_cannot_invite(self):
        viewer = create_user('viewer_a')
        add_member(viewer, self.organization, Membership.Role.VIEWER)
        self.client.force_login(viewer)
        response = self.client.post(self.invite_url, {'username': 'target', 'role': 'viewer'})
        self.assertEqual(response.status_code, 403)
