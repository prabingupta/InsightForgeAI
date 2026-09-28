from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.core.factories import (
    SAMPLE_CSV,
    TemporaryMediaTestCase,
    add_member,
    create_dataset,
    create_organization,
    create_user,
)
from apps.datasets.models import Dataset
from apps.organizations.models import Membership


class DatasetViewTests(TemporaryMediaTestCase):
    def setUp(self) -> None:
        self.owner_a = create_user('owner_a')
        self.owner_b = create_user('owner_b')
        self.org_a = create_organization('Acme', self.owner_a)
        self.org_b = create_organization('Globex', self.owner_b)
        self.viewer = create_user('viewer')
        add_member(self.viewer, self.org_a, Membership.Role.VIEWER)
        self.analyst = create_user('analyst')
        add_member(self.analyst, self.org_a, Membership.Role.ANALYST)
        self.dataset_a = create_dataset(self.org_a, self.owner_a, name='Acme Sales')
        self.dataset_b = create_dataset(self.org_b, self.owner_b, name='Globex Secrets')
        self.list_url = reverse('datasets:list', kwargs={'org_slug': 'acme'})
        self.upload_url = reverse('datasets:upload', kwargs={'org_slug': 'acme'})

    def detail_url(self, org_slug: str, dataset_pk: int) -> str:
        return reverse(
            'datasets:detail', kwargs={'org_slug': org_slug, 'pk': dataset_pk}
        )

    def post_upload(self, filename: str, content: bytes):
        uploaded = SimpleUploadedFile(filename, content)
        return self.client.post(
            self.upload_url,
            {'name': 'Upload test', 'description': '', 'file': uploaded},
        )

    def test_anonymous_upload_page_redirects_to_login(self):
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_viewer_cannot_open_upload_page(self):
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.upload_url).status_code, 403)

    def test_viewer_cannot_post_upload(self):
        self.client.force_login(self.viewer)
        response = self.post_upload('data.csv', SAMPLE_CSV.encode())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Dataset.objects.filter(name='Upload test').exists())

    def test_analyst_can_open_upload_page(self):
        self.client.force_login(self.analyst)
        self.assertEqual(self.client.get(self.upload_url).status_code, 200)

    def test_outsider_cannot_list_datasets(self):
        self.client.force_login(self.owner_b)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_outsider_cannot_view_dataset_detail(self):
        self.client.force_login(self.owner_b)
        response = self.client.get(self.detail_url('acme', self.dataset_a.pk))
        self.assertEqual(response.status_code, 403)

    def test_dataset_list_only_shows_own_organization(self):
        self.client.force_login(self.owner_a)
        response = self.client.get(self.list_url)
        self.assertContains(response, 'Acme Sales')
        self.assertNotContains(response, 'Globex Secrets')

    def test_detail_of_another_organizations_dataset_returns_404(self):
        self.client.force_login(self.owner_a)
        response = self.client.get(self.detail_url('acme', self.dataset_b.pk))
        self.assertEqual(response.status_code, 404)

    def test_valid_csv_upload_is_stored_and_processed(self):
        self.client.force_login(self.analyst)
        response = self.post_upload('data.csv', SAMPLE_CSV.encode())
        self.assertEqual(response.status_code, 302)
        dataset = Dataset.objects.get(name='Upload test')
        self.assertEqual(dataset.organization, self.org_a)
        self.assertEqual(dataset.owner, self.analyst)
        self.assertEqual(dataset.original_filename, 'data.csv')
        self.assertEqual(dataset.processing_status, Dataset.ProcessingStatus.COMPLETED)
        self.assertEqual(dataset.row_count, 2)
        self.assertEqual(dataset.column_count, 2)

    def test_disguised_xlsx_upload_is_rejected(self):
        self.client.force_login(self.analyst)
        response = self.post_upload('fake.xlsx', b'plain text pretending to be excel')
        self.assertContains(response, 'does not match the expected format')
        self.assertFalse(Dataset.objects.filter(name='Upload test').exists())

    def test_oversized_upload_is_rejected(self):
        self.client.force_login(self.analyst)
        with self.settings(MAX_DATASET_UPLOAD_SIZE_BYTES=10):
            response = self.post_upload('data.csv', SAMPLE_CSV.encode())
        self.assertContains(response, 'too large')
        self.assertFalse(Dataset.objects.filter(name='Upload test').exists())

    def test_upload_with_invalid_value_lowers_quality_score(self):
        self.client.force_login(self.analyst)
        content = b'revenue,name\n1,a\n2,b\n3,c\n4,d\n5,e\nx,f\n'
        self.post_upload('data.csv', content)
        dataset = Dataset.objects.get(name='Upload test')
        self.assertEqual(dataset.data_quality_score, 91.67)
        self.assertEqual(dataset.detected_schema['invalid_cell_count'], 1)
