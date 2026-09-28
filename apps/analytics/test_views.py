from django.urls import reverse

from apps.core.factories import (
    TemporaryMediaTestCase,
    add_member,
    create_dataset,
    create_organization,
    create_user,
)
from apps.datasets.models import Dataset
from apps.organizations.models import Membership


class DatasetAnalyticsAccessTests(TemporaryMediaTestCase):
    def setUp(self) -> None:
        self.owner_a = create_user('owner_a')
        self.owner_b = create_user('owner_b')
        self.org_a = create_organization('Acme', self.owner_a)
        self.org_b = create_organization('Globex', self.owner_b)
        self.viewer = create_user('viewer')
        add_member(self.viewer, self.org_a, Membership.Role.VIEWER)
        self.dataset_a = create_dataset(self.org_a, self.owner_a)
        self.dataset_b = create_dataset(self.org_b, self.owner_b)

    def analytics_url(self, org_slug: str, dataset_pk: int) -> str:
        return reverse(
            'analytics:dataset_analytics',
            kwargs={'org_slug': org_slug, 'pk': dataset_pk},
        )

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.analytics_url('acme', self.dataset_a.pk))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_user_outside_organization_gets_403(self):
        self.client.force_login(self.owner_b)
        response = self.client.get(self.analytics_url('acme', self.dataset_a.pk))
        self.assertEqual(response.status_code, 403)

    def test_member_sees_kpis(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.analytics_url('acme', self.dataset_a.pk))
        self.assertContains(response, 'Total Revenue')
        self.assertContains(response, '300.0')

    def test_dataset_from_another_organization_returns_404(self):
        self.client.force_login(self.owner_a)
        response = self.client.get(self.analytics_url('acme', self.dataset_b.pk))
        self.assertEqual(response.status_code, 404)

    def test_unprocessed_dataset_shows_message_instead_of_kpis(self):
        pending = create_dataset(
            self.org_a, self.owner_a, name='Pending',
            status=Dataset.ProcessingStatus.PENDING,
        )
        self.client.force_login(self.owner_a)
        response = self.client.get(self.analytics_url('acme', pending.pk))
        self.assertContains(response, 'not been processed')
        self.assertNotContains(response, 'Total Revenue')

    def test_unknown_organization_returns_404(self):
        self.client.force_login(self.owner_a)
        response = self.client.get(self.analytics_url('does-not-exist', 1))
        self.assertEqual(response.status_code, 404)


class DatasetAnalyticsBreakdownTests(TemporaryMediaTestCase):
    def test_breakdown_section_is_shown_for_member(self):
        owner = create_user('owner_a')
        organization = create_organization('Acme', owner)
        dataset = create_dataset(
            organization, owner, content='product,revenue\nA,100\nB,200\n'
        )
        self.client.force_login(owner)
        response = self.client.get(reverse(
            'analytics:dataset_analytics',
            kwargs={'org_slug': 'acme', 'pk': dataset.pk},
        ))
        self.assertContains(response, 'Revenue by Product')
