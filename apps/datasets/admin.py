from django.contrib import admin

from apps.datasets.models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'organization', 'owner', 'processing_status',
        'validation_status', 'row_count', 'created_at',
    )
    list_filter = ('processing_status', 'validation_status', 'organization')
