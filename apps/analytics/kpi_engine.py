from dataclasses import dataclass, field

import pandas as pd

from apps.analytics.column_mapping import detect_column_mapping


@dataclass
class KPIResult:
    name: str
    value: float | int | str | None
    unit: str
    source_columns: list[str] = field(default_factory=list)
    note: str = ''


def compute_kpis(dataframe: pd.DataFrame) -> list[KPIResult]:
    mapping = detect_column_mapping(list(dataframe.columns))
    results = []

    results.append(_total_rows(dataframe))

    if 'revenue' in mapping:
        results.append(_total_revenue(dataframe, mapping))
        results.append(_average_order_value(dataframe, mapping))

    if 'quantity' in mapping:
        results.append(_total_units_sold(dataframe, mapping))

    if 'customer_id' in mapping:
        results.append(_unique_customers(dataframe, mapping))

    if 'order_id' in mapping:
        results.append(_total_orders(dataframe, mapping))

    if 'profit' in mapping and 'revenue' in mapping:
        results.append(_profit_margin(dataframe, mapping))

    if 'product' in mapping and 'revenue' in mapping:
        results.append(_top_product(dataframe, mapping))

    if 'region' in mapping and 'revenue' in mapping:
        results.append(_top_region(dataframe, mapping))

    if 'date' in mapping and 'revenue' in mapping:
        results.append(_revenue_growth(dataframe, mapping))

    if 'date' in mapping and 'order_id' in mapping:
        results.append(_order_growth(dataframe, mapping))

    return results


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce')


def _total_rows(dataframe: pd.DataFrame) -> KPIResult:
    return KPIResult(name='Total Records', value=len(dataframe), unit='rows')


def _total_revenue(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    column = mapping['revenue']
    values = _safe_numeric(dataframe[column])
    total = values.sum(skipna=True)
    invalid_count = int(values.isna().sum())
    note = f'{invalid_count} non-numeric value(s) ignored.' if invalid_count else ''
    return KPIResult(
        name='Total Revenue', value=round(float(total), 2), unit='currency',
        source_columns=[column], note=note,
    )


def _average_order_value(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    column = mapping['revenue']
    values = _safe_numeric(dataframe[column]).dropna()
    if len(values) == 0:
        return KPIResult(name='Average Order Value', value=None, unit='currency',
                          source_columns=[column], note='No valid revenue values found.')
    excluded = len(dataframe) - len(values)
    note = (
        f'Averaged over {len(values)} of {len(dataframe)} rows; '
        'rows without a valid revenue value were excluded.'
        if excluded else ''
    )
    return KPIResult(
        name='Average Order Value', value=round(float(values.mean()), 2), unit='currency',
        source_columns=[column], note=note,
    )


def _total_units_sold(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    column = mapping['quantity']
    values = _safe_numeric(dataframe[column])
    return KPIResult(
        name='Total Units Sold', value=int(values.sum(skipna=True)), unit='units',
        source_columns=[column],
    )


def _unique_customers(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    column = mapping['customer_id']
    return KPIResult(
        name='Unique Customers', value=int(dataframe[column].nunique()), unit='customers',
        source_columns=[column],
    )


def _total_orders(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    column = mapping['order_id']
    return KPIResult(
        name='Total Orders', value=int(dataframe[column].nunique()), unit='orders',
        source_columns=[column],
    )


def _profit_margin(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    revenue_column = mapping['revenue']
    profit_column = mapping['profit']
    revenue = _safe_numeric(dataframe[revenue_column])
    profit = _safe_numeric(dataframe[profit_column])
    comparable = revenue.notna() & profit.notna()
    revenue_total = revenue[comparable].sum()
    profit_total = profit[comparable].sum()
    excluded = int((~comparable).sum())
    note = (
        f'{excluded} row(s) without both a valid revenue and profit value were excluded.'
        if excluded else ''
    )

    if revenue_total == 0:
        return KPIResult(
            name='Profit Margin', value=None, unit='percentage',
            source_columns=[revenue_column, profit_column],
            note='Cannot calculate margin: total revenue is zero.',
        )

    margin = (profit_total / revenue_total) * 100
    return KPIResult(
        name='Profit Margin', value=round(float(margin), 2), unit='percentage',
        source_columns=[revenue_column, profit_column], note=note,
    )


def _top_product(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    product_column = mapping['product']
    revenue_column = mapping['revenue']
    grouped = dataframe.groupby(product_column)[revenue_column].apply(
        lambda s: _safe_numeric(s).sum(skipna=True)
    )
    if grouped.empty:
        return KPIResult(name='Top Product', value=None, unit='product',
                          source_columns=[product_column, revenue_column])
    top = grouped.idxmax()
    return KPIResult(
        name='Top Product', value=str(top), unit='product',
        source_columns=[product_column, revenue_column],
        note=f'By total revenue: {round(float(grouped.max()), 2)}',
    )


def _top_region(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    region_column = mapping['region']
    revenue_column = mapping['revenue']
    grouped = dataframe.groupby(region_column)[revenue_column].apply(
        lambda s: _safe_numeric(s).sum(skipna=True)
    )
    if grouped.empty:
        return KPIResult(name='Top Region', value=None, unit='region',
                          source_columns=[region_column, revenue_column])
    top = grouped.idxmax()
    return KPIResult(
        name='Top Region', value=str(top), unit='region',
        source_columns=[region_column, revenue_column],
        note=f'By total revenue: {round(float(grouped.max()), 2)}',
    )


def parse_dates(dataframe: pd.DataFrame, mapping: dict) -> tuple[pd.Series, int]:
    column = dataframe[mapping['date']]
    if pd.api.types.is_numeric_dtype(column):
        parsed = pd.Series(pd.NaT, index=dataframe.index, dtype='datetime64[ns]')
    else:
        parsed = pd.to_datetime(column, errors='coerce')
    return parsed, int(parsed.isna().sum())


def _revenue_growth(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    dates, invalid_dates = parse_dates(dataframe, mapping)
    valid = dates.notna()
    revenue = _safe_numeric(dataframe[mapping['revenue']])
    monthly = revenue[valid].groupby(dates[valid].dt.to_period('M')).sum().sort_index()
    return _growth_result(
        'Revenue Growth', monthly, [mapping['date'], mapping['revenue']], invalid_dates
    )


def _order_growth(dataframe: pd.DataFrame, mapping: dict) -> KPIResult:
    dates, invalid_dates = parse_dates(dataframe, mapping)
    valid = dates.notna()
    orders = dataframe.loc[valid, mapping['order_id']]
    monthly = orders.groupby(dates[valid].dt.to_period('M')).nunique().sort_index()
    return _growth_result(
        'Order Growth', monthly, [mapping['date'], mapping['order_id']], invalid_dates
    )


def _growth_result(
    name: str, monthly: pd.Series, source_columns: list[str], invalid_dates: int
) -> KPIResult:
    notes = []
    if invalid_dates:
        notes.append(f'{invalid_dates} row(s) with missing or invalid dates were excluded.')

    def result(value: float | None, message: str) -> KPIResult:
        if message:
            notes.append(message)
        return KPIResult(
            name=name, value=value, unit='percentage',
            source_columns=source_columns, note=' '.join(notes),
        )

    if len(monthly) < 2:
        return result(None, 'Needs data from at least two months.')

    previous_period, current_period = monthly.index[-2], monthly.index[-1]
    gap = (current_period.year * 12 + current_period.month) - (
        previous_period.year * 12 + previous_period.month
    )
    if gap != 1:
        return result(None, 'The two most recent months in the data are not consecutive.')

    previous_value = float(monthly.iloc[-2])
    current_value = float(monthly.iloc[-1])
    if previous_value == 0:
        return result(None, f'Previous month ({previous_period}) is zero, so growth is undefined.')

    growth = (current_value - previous_value) / abs(previous_value) * 100
    return result(
        round(growth, 2),
        f'{current_period} vs {previous_period}. The latest month may be incomplete.',
    )
