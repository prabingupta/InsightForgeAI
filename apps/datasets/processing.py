import pandas as pd
from django.utils import timezone

from apps.datasets.models import Dataset


def process_dataset(dataset: Dataset) -> None:
    dataset.processing_status = Dataset.ProcessingStatus.PROCESSING
    dataset.save(update_fields=['processing_status'])

    try:
        dataframe = _read_dataframe(dataset)
        _apply_profile(dataset, dataframe)
        dataset.processing_status = Dataset.ProcessingStatus.COMPLETED
        dataset.validation_status = Dataset.ValidationStatus.VALID
        dataset.processing_errors = ''
    except Exception as exc:
        dataset.processing_status = Dataset.ProcessingStatus.FAILED
        dataset.validation_status = Dataset.ValidationStatus.INVALID
        dataset.processing_errors = str(exc)

    dataset.updated_at = timezone.now()
    dataset.save()


def _read_dataframe(dataset: Dataset) -> pd.DataFrame:
    dataset.file.seek(0)
    filename = dataset.original_filename.lower()

    if filename.endswith('.csv'):
        return pd.read_csv(dataset.file)
    if filename.endswith('.xlsx'):
        return pd.read_excel(dataset.file, engine='openpyxl')
    if filename.endswith('.xls'):
        return pd.read_excel(dataset.file, engine='xlrd')

    raise ValueError(f'Unsupported file extension for parsing: {filename}')


def _apply_profile(dataset: Dataset, dataframe: pd.DataFrame) -> None:
    row_count = len(dataframe)
    column_count = len(dataframe.columns)

    schema = []
    total_cells = row_count * column_count if column_count else 0
    missing_cells = 0

    for column in dataframe.columns:
        series = dataframe[column]
        missing_count = int(series.isna().sum())
        missing_cells += missing_count
        schema.append({
            'column': str(column),
            'dtype': str(series.dtype),
            'missing_count': missing_count,
            'missing_percentage': round((missing_count / row_count) * 100, 2) if row_count else 0,
            'unique_count': int(series.nunique()),
        })

    duplicate_row_count = int(dataframe.duplicated().sum())

    completeness_ratio = 1 - (missing_cells / total_cells) if total_cells else 0
    duplicate_penalty = (duplicate_row_count / row_count) if row_count else 0
    quality_score = max(0.0, round((completeness_ratio - duplicate_penalty) * 100, 2))

    dataset.row_count = row_count
    dataset.column_count = column_count
    dataset.detected_schema = {
        'columns': schema,
        'duplicate_row_count': duplicate_row_count,
    }
    dataset.data_quality_score = quality_score
