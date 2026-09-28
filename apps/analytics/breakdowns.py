from dataclasses import dataclass, field

import pandas as pd

from apps.analytics.column_mapping import detect_column_mapping
from apps.analytics.kpi_engine import parse_dates

TOP_N = 10

DIMENSION_TITLES = {
    'product': 'Revenue by Product',
    'region': 'Revenue by Region',
    'category': 'Revenue by Category',
    'customer_id': 'Top Customers by Revenue',
}


@dataclass
class Breakdown:
    title: str
    labels: list[str]
    values: list[float]
    source_columns: list[str] = field(default_factory=list)
    note: str = ''

    @property
    def rows(self) -> list[tuple[str, float]]:
        return list(zip(self.labels, self.values))


def compute_breakdowns(dataframe: pd.DataFrame) -> list[Breakdown]:
    mapping = detect_column_mapping(list(dataframe.columns))
    if 'revenue' not in mapping:
        return []

    results = [
        _revenue_by_dimension(dataframe, mapping, key, title)
        for key, title in DIMENSION_TITLES.items()
        if key in mapping
    ]
    if 'date' in mapping:
        results.append(_monthly_revenue(dataframe, mapping))
    return results


def _revenue_by_dimension(
    dataframe: pd.DataFrame, mapping: dict, key: str, title: str
) -> Breakdown:
    dimension_column = mapping[key]
    revenue_column = mapping['revenue']
    revenue = pd.to_numeric(dataframe[revenue_column], errors='coerce')
    usable = revenue.notna() & dataframe[dimension_column].notna()
    excluded = int((~usable).sum())

    labels = dataframe.loc[usable, dimension_column].astype(str)
    grouped = revenue[usable].groupby(labels).sum()
    grouped = grouped.sort_index().sort_values(ascending=False, kind='stable')

    notes = []
    if excluded:
        notes.append(
            f'{excluded} row(s) with a missing label or invalid revenue were excluded.'
        )
    if len(grouped) > TOP_N:
        notes.append(f'Showing the top {TOP_N} of {len(grouped)}.')
        grouped = grouped.head(TOP_N)

    return Breakdown(
        title=title,
        labels=[str(label) for label in grouped.index],
        values=[round(float(value), 2) for value in grouped.values],
        source_columns=[dimension_column, revenue_column],
        note=' '.join(notes),
    )


def _monthly_revenue(dataframe: pd.DataFrame, mapping: dict) -> Breakdown:
    date_column = mapping['date']
    revenue_column = mapping['revenue']
    dates, _ = parse_dates(dataframe, mapping)
    revenue = pd.to_numeric(dataframe[revenue_column], errors='coerce')
    usable = dates.notna() & revenue.notna()
    excluded = int((~usable).sum())

    monthly = revenue[usable].groupby(dates[usable].dt.to_period('M')).sum().sort_index()

    notes = []
    if excluded:
        notes.append(f'{excluded} row(s) with a missing date or invalid revenue were excluded.')
    if len(monthly) > 1:
        expected_months = pd.period_range(monthly.index.min(), monthly.index.max(), freq='M')
        if len(expected_months) != len(monthly):
            notes.append('Some months have no data and are not shown.')

    return Breakdown(
        title='Monthly Revenue',
        labels=[str(period) for period in monthly.index],
        values=[round(float(value), 2) for value in monthly.values],
        source_columns=[date_column, revenue_column],
        note=' '.join(notes),
    )
