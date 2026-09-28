from dataclasses import dataclass

import pandas as pd
from django.utils import timezone

from apps.datasets.models import Dataset

NUMERIC_COLUMN_THRESHOLD = 0.8


@dataclass
class DataProfile:
    row_count: int
    column_count: int
    columns: list[dict]
    duplicate_row_count: int
    invalid_cell_count: int
    quality_score: float


def process_dataset(dataset: Dataset) -> None:
    dataset.processing_status = Dataset.ProcessingStatus.PROCESSING
    dataset.save(update_fields=['processing_status'])

    try:
        dataframe = read_dataset_dataframe(dataset)
        _apply_profile(dataset, profile_dataframe(dataframe))
        dataset.processing_status = Dataset.ProcessingStatus.COMPLETED
        dataset.validation_status = Dataset.ValidationStatus.VALID
        dataset.processing_errors = ''
    except Exception as exc:
        dataset.processing_status = Dataset.ProcessingStatus.FAILED
        dataset.validation_status = Dataset.ValidationStatus.INVALID
        dataset.processing_errors = str(exc)

    dataset.updated_at = timezone.now()
    dataset.save()


def read_dataset_dataframe(dataset: Dataset) -> pd.DataFrame:
    dataset.file.seek(0)
    filename = dataset.original_filename.lower()

    if filename.endswith('.csv'):
        return pd.read_csv(dataset.file)
    if filename.endswith('.xlsx'):
        return pd.read_excel(dataset.file, engine='openpyxl')
    if filename.endswith('.xls'):
        return pd.read_excel(dataset.file, engine='xlrd')

    raise ValueError(f'Unsupported file extension for parsing: {filename}')


def profile_dataframe(dataframe: pd.DataFrame) -> DataProfile:
    row_count = len(dataframe)
    column_count = len(dataframe.columns)
    total_cells = row_count * column_count

    columns = []
    missing_cells = 0
    invalid_cells = 0

    for column in dataframe.columns:
        series = dataframe[column]
        missing_count = int(series.isna().sum())
        invalid_count = _count_invalid_values(series)
        missing_cells += missing_count
        invalid_cells += invalid_count
        columns.append({
            'column': str(column),
            'dtype': str(series.dtype),
            'missing_count': missing_count,
            'missing_percentage': _percentage(missing_count, row_count),
            'invalid_count': invalid_count,
            'invalid_percentage': _percentage(invalid_count, row_count),
            'unique_count': int(series.nunique()),
        })

    duplicate_row_count = int(dataframe.duplicated().sum())

    validity_ratio = 1 - (missing_cells + invalid_cells) / total_cells if total_cells else 0
    duplicate_penalty = duplicate_row_count / row_count if row_count else 0
    quality_score = max(0.0, round((validity_ratio - duplicate_penalty) * 100, 2))

    return DataProfile(
        row_count=row_count,
        column_count=column_count,
        columns=columns,
        duplicate_row_count=duplicate_row_count,
        invalid_cell_count=invalid_cells,
        quality_score=quality_score,
    )


def _percentage(count: int, total: int) -> float:
    return round(count / total * 100, 2) if total else 0


def _count_invalid_values(series: pd.Series) -> int:
    if not (pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series)):
        return 0

    present = series.dropna()
    if present.empty:
        return 0

    valid_count = int(pd.to_numeric(present, errors='coerce').notna().sum())
    invalid_count = len(present) - valid_count
    if invalid_count == 0 or valid_count / len(present) < NUMERIC_COLUMN_THRESHOLD:
        return 0
    return invalid_count


def _apply_profile(dataset: Dataset, profile: DataProfile) -> None:
    dataset.row_count = profile.row_count
    dataset.column_count = profile.column_count
    dataset.detected_schema = {
        'columns': profile.columns,
        'duplicate_row_count': profile.duplicate_row_count,
        'invalid_cell_count': profile.invalid_cell_count,
    }
    dataset.data_quality_score = profile.quality_score
