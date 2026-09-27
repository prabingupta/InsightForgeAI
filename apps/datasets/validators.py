import os

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

CSV_MIME_TYPES = {'text/csv', 'text/plain', 'application/csv'}
XLSX_MIME_TYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
XLS_MIME_TYPES = {'application/vnd.ms-excel'}

XLSX_MAGIC_BYTES = b'PK\x03\x04'
XLS_MAGIC_BYTES = b'\xd0\xcf\x11\xe0'


def validate_dataset_file(uploaded_file) -> None:
    _validate_extension(uploaded_file.name)
    _validate_size(uploaded_file.size)
    _validate_content(uploaded_file)


def _validate_extension(filename: str) -> None:
    _, extension = os.path.splitext(filename.lower())
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f'File type "{extension}" is not supported. '
            f'Allowed types: {", ".join(sorted(ALLOWED_EXTENSIONS))}.'
        )


def _validate_size(size: int) -> None:
    if size > settings.MAX_DATASET_UPLOAD_SIZE_BYTES:
        raise ValidationError(
            f'File is too large. Maximum size is '
            f'{settings.MAX_DATASET_UPLOAD_SIZE_MB} MB.'
        )
    if size == 0:
        raise ValidationError('File is empty.')


def _validate_content(uploaded_file) -> None:
    _, extension = os.path.splitext(uploaded_file.name.lower())
    uploaded_file.seek(0)
    header = uploaded_file.read(8)
    uploaded_file.seek(0)

    if extension == '.xlsx' and not header.startswith(XLSX_MAGIC_BYTES):
        raise ValidationError(
            'File claims to be .xlsx but its content does not match the expected format.'
        )
    if extension == '.xls' and not header.startswith(XLS_MAGIC_BYTES):
        raise ValidationError(
            'File claims to be .xls but its content does not match the expected format.'
        )
    if extension == '.csv':
        try:
            header.decode('utf-8')
        except UnicodeDecodeError:
            raise ValidationError(
                'File claims to be .csv but contains binary content, not plain text.'
            )
