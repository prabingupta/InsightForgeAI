from django.test import TestCase
from django.urls import reverse

from apps.core.factories import create_organization, create_user


class LayoutTests(TestCase):
    def setUp(self) -> None:
        self.owner = create_user('owner_a')
        other = create_user('owner_b')
        create_organization('Acme', self.owner)
        create_organization('Globex', other)
        self.detail_url = reverse('organizations:detail', kwargs={'slug': 'acme'})

    def test_organization_page_has_sidebar_with_organization_links(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.detail_url)
        self.assertContains(response, 'app-sidebar')
        self.assertContains(response, reverse('datasets:list', kwargs={'org_slug': 'acme'}))

    def test_sidebar_does_not_leak_other_organizations(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.detail_url)
        self.assertNotContains(response, 'Globex')

    def test_navbar_shows_the_logged_in_username(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('organizations:list'))
        self.assertContains(response, 'owner_a')

    def test_login_page_has_no_sidebar(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertNotContains(response, 'app-sidebar')
