from django.test import TestCase
from django.urls import reverse

from apps.core.factories import TEST_PASSWORD, create_user


class AuthFlowTests(TestCase):
    def setUp(self) -> None:
        create_user('alice')

    def test_login_redirects_to_organizations(self):
        response = self.client.post(
            reverse('accounts:login'), {'username': 'alice', 'password': TEST_PASSWORD}
        )
        self.assertRedirects(response, reverse('organizations:list'))

    def test_wrong_password_shows_an_error_message(self):
        response = self.client.post(
            reverse('accounts:login'), {'username': 'alice', 'password': 'wrong-password'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'correct username and password')

    def test_register_logs_the_user_in_and_redirects(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'S3cure-pass-98765',
            'password2': 'S3cure-pass-98765',
        })
        self.assertRedirects(response, reverse('organizations:list'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_root_redirects_to_organizations(self):
        response = self.client.get('/')
        self.assertRedirects(
            response, reverse('organizations:list'), fetch_redirect_response=False
        )

    def test_organizations_list_requires_login(self):
        response = self.client.get(reverse('organizations:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
