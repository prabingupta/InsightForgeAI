import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.datasets.models import Dataset
from apps.organizations.models import Membership, Organization

SAMPLE_CSV = 'revenue,quantity\n100,1\n200,2\n'
TEST_PASSWORD = 'test-pass-12345'


def create_user(username: str) -> User:
    return User.objects.create_user(username=username, password=TEST_PASSWORD)


def create_organization(name: str, owner: User) -> Organization:
    organization = Organization.objects.create(name=name, owner=owner)
    Membership.objects.create(
        user=owner, organization=organization, role=Membership.Role.OWNER
    )
    return organization


def add_member(user: User, organization: Organization, role: str) -> Membership:
    return Membership.objects.create(user=user, organization=organization, role=role)


def create_dataset(
    organization: Organization,
    owner: User,
    name: str = 'Sales',
    content: str = SAMPLE_CSV,
    status: str = Dataset.ProcessingStatus.COMPLETED,
) -> Dataset:
    uploaded = SimpleUploadedFile('sales.csv', content.encode(), content_type='text/csv')
    return Dataset.objects.create(
        organization=organization,
        owner=owner,
        name=name,
        file=uploaded,
        original_filename='sales.csv',
        file_size=len(content),
        processing_status=status,
    )


class TemporaryMediaTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._media_root = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
