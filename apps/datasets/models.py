import uuid

from django.conf import settings
from django.db import models

from apps.organizations.models import Organization


def dataset_upload_path(instance: 'Dataset', filename: str) -> str:
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    safe_name = f'{uuid.uuid4().hex}.{extension}' if extension else uuid.uuid4().hex
    return f'datasets/org_{instance.organization_id}/{safe_name}'


class Dataset(models.Model):
    class ProcessingStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    class ValidationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VALID = 'valid', 'Valid'
        INVALID = 'invalid', 'Invalid'

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='datasets',
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_datasets',
    )

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    file = models.FileField(upload_to=dataset_upload_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(help_text='Size in bytes')

    row_count = models.PositiveIntegerField(null=True, blank=True)
    column_count = models.PositiveIntegerField(null=True, blank=True)
    detected_schema = models.JSONField(null=True, blank=True)

    processing_status = models.CharField(
        max_length=32,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    validation_status = models.CharField(
        max_length=32,
        choices=ValidationStatus.choices,
        default=ValidationStatus.PENDING,
    )
    data_quality_score = models.FloatField(null=True, blank=True)
    processing_errors = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name
