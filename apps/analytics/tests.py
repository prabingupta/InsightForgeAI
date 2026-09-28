import pandas as pd
from django.test import SimpleTestCase

from apps.analytics.column_mapping import detect_column_mapping
from apps.analytics.kpi_engine import compute_kpis


def kpis_by_name(dataframe: pd.DataFrame) -> dict:
    return {kpi.name: kpi for kpi in compute_kpis(dataframe)}


def make_sales_dataframe() -> pd.DataFrame:
    return pd.DataFrame({
        'order_id': ['O1', 'O2', 'O3'],
        'customer_id': ['C1', 'C2', 'C1'],
        'product': ['A', 'B', 'A'],
        'region': ['North', 'South', 'North'],
        'revenue': [100.0, 200.0, 300.0],
        'quantity': [1, 2, 3],
        'profit': [10.0, 20.0, 30.0],
    })


class ColumnMappingTests(SimpleTestCase):
    def test_detects_columns_with_varied_naming(self):
        mapping = detect_column_mapping(
            ['Order Date', 'Customer_ID', 'Product Name', 'Qty', 'Net_Profit']
        )
        self.assertEqual(mapping['date'], 'Order Date')
        self.assertEqual(mapping['customer_id'], 'Customer_ID')
        self.assertEqual(mapping['product'], 'Product Name')
        self.assertEqual(mapping['quantity'], 'Qty')
        self.assertEqual(mapping['profit'], 'Net_Profit')

    def test_unrecognized_columns_produce_empty_mapping(self):
        self.assertEqual(detect_column_mapping(['foo', 'bar']), {})

    def test_fields_not_present_are_not_invented(self):
        mapping = detect_column_mapping(['revenue'])
        self.assertNotIn('customer_id', mapping)
        self.assertNotIn('profit', mapping)


class KPIEngineTests(SimpleTestCase):
    def test_computes_expected_values(self):
        kpis = kpis_by_name(make_sales_dataframe())
        self.assertEqual(kpis['Total Records'].value, 3)
        self.assertEqual(kpis['Total Revenue'].value, 600.0)
        self.assertEqual(kpis['Average Order Value'].value, 200.0)
        self.assertEqual(kpis['Total Units Sold'].value, 6)
        self.assertEqual(kpis['Unique Customers'].value, 2)
        self.assertEqual(kpis['Total Orders'].value, 3)
        self.assertEqual(kpis['Profit Margin'].value, 10.0)
        self.assertEqual(kpis['Top Product'].value, 'A')
        self.assertEqual(kpis['Top Region'].value, 'North')

    def test_only_total_records_when_no_business_columns_exist(self):
        kpis = kpis_by_name(pd.DataFrame({'foo': [1, 2]}))
        self.assertEqual(list(kpis.keys()), ['Total Records'])
        self.assertEqual(kpis['Total Records'].value, 2)

    def test_kpis_needing_missing_columns_are_skipped(self):
        dataframe = pd.DataFrame({'revenue': [10.0, 20.0]})
        kpis = kpis_by_name(dataframe)
        self.assertIn('Total Revenue', kpis)
        self.assertNotIn('Profit Margin', kpis)
        self.assertNotIn('Unique Customers', kpis)
        self.assertNotIn('Top Product', kpis)

    def test_profit_margin_with_zero_revenue_does_not_divide_by_zero(self):
        dataframe = pd.DataFrame({'revenue': [0, 0], 'profit': [5, 5]})
        margin = kpis_by_name(dataframe)['Profit Margin']
        self.assertIsNone(margin.value)
        self.assertIn('zero', margin.note)

    def test_non_numeric_revenue_values_are_ignored_and_reported(self):
        dataframe = pd.DataFrame({'revenue': ['100', 'abc', '50']})
        revenue = kpis_by_name(dataframe)['Total Revenue']
        self.assertEqual(revenue.value, 150.0)
        self.assertIn('1 non-numeric', revenue.note)

    def test_missing_revenue_values_are_skipped(self):
        dataframe = pd.DataFrame({'revenue': [100.0, None, 300.0]})
        kpis = kpis_by_name(dataframe)
        self.assertEqual(kpis['Total Revenue'].value, 400.0)
        self.assertEqual(kpis['Average Order Value'].value, 200.0)

    def test_empty_dataset_does_not_crash(self):
        columns = [
            'order_id', 'customer_id', 'product', 'region',
            'revenue', 'quantity', 'profit',
        ]
        kpis = kpis_by_name(pd.DataFrame(columns=columns))
        self.assertEqual(kpis['Total Records'].value, 0)
        self.assertEqual(kpis['Total Revenue'].value, 0.0)
        self.assertIsNone(kpis['Average Order Value'].value)
        self.assertIsNone(kpis['Profit Margin'].value)
        self.assertIsNone(kpis['Top Product'].value)
        self.assertIsNone(kpis['Top Region'].value)

    def test_single_row_dataset(self):
        dataframe = pd.DataFrame({'revenue': [250.0], 'quantity': [5]})
        kpis = kpis_by_name(dataframe)
        self.assertEqual(kpis['Total Revenue'].value, 250.0)
        self.assertEqual(kpis['Average Order Value'].value, 250.0)
        self.assertEqual(kpis['Total Units Sold'].value, 5)

    def test_negative_revenue_is_included_not_hidden(self):
        dataframe = pd.DataFrame({'revenue': [100.0, -30.0]})
        self.assertEqual(kpis_by_name(dataframe)['Total Revenue'].value, 70.0)


class GrowthKPITests(SimpleTestCase):
    def test_revenue_and_order_growth_between_two_months(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', '2026-01-20', '2026-02-10'],
            'order_id': ['O1', 'O2', 'O3'],
            'revenue': [100.0, 100.0, 300.0],
        })
        kpis = kpis_by_name(dataframe)
        self.assertEqual(kpis['Revenue Growth'].value, 50.0)
        self.assertEqual(kpis['Order Growth'].value, -50.0)
        self.assertIn('2026-02 vs 2026-01', kpis['Revenue Growth'].note)

    def test_single_month_gives_no_growth(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', '2026-01-20'], 'revenue': [100.0, 200.0],
        })
        growth = kpis_by_name(dataframe)['Revenue Growth']
        self.assertIsNone(growth.value)
        self.assertIn('two months', growth.note)

    def test_non_adjacent_months_are_not_compared(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', '2026-03-05'], 'revenue': [100.0, 200.0],
        })
        growth = kpis_by_name(dataframe)['Revenue Growth']
        self.assertIsNone(growth.value)
        self.assertIn('consecutive', growth.note)

    def test_zero_previous_month_revenue_gives_no_growth(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', '2026-02-05'], 'revenue': [0.0, 100.0],
        })
        growth = kpis_by_name(dataframe)['Revenue Growth']
        self.assertIsNone(growth.value)
        self.assertIn('zero', growth.note)

    def test_invalid_dates_are_excluded_and_reported(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', 'not a date', '2026-02-10'],
            'revenue': [100.0, 50.0, 300.0],
        })
        growth = kpis_by_name(dataframe)['Revenue Growth']
        self.assertEqual(growth.value, 200.0)
        self.assertIn('1 row(s)', growth.note)

    def test_no_growth_kpis_without_date_column(self):
        kpis = kpis_by_name(pd.DataFrame({'revenue': [1.0, 2.0]}))
        self.assertNotIn('Revenue Growth', kpis)
        self.assertNotIn('Order Growth', kpis)

    def test_numeric_date_column_is_not_treated_as_dates(self):
        dataframe = pd.DataFrame({'date': [1, 2], 'revenue': [10.0, 20.0]})
        growth = kpis_by_name(dataframe)['Revenue Growth']
        self.assertIsNone(growth.value)

    def test_order_growth_requires_order_id(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', '2026-02-05'], 'revenue': [1.0, 2.0],
        })
        kpis = kpis_by_name(dataframe)
        self.assertIn('Revenue Growth', kpis)
        self.assertNotIn('Order Growth', kpis)


class ProfitMarginConsistencyTests(SimpleTestCase):
    def test_profit_margin_ignores_rows_with_invalid_revenue(self):
        dataframe = pd.DataFrame({
            'revenue': ['100', 'abc', '100'],
            'profit': [10, 50, 10],
        })
        margin = kpis_by_name(dataframe)['Profit Margin']
        self.assertEqual(margin.value, 10.0)
        self.assertIn('1 row(s)', margin.note)


class AverageOrderValueNoteTests(SimpleTestCase):
    def test_note_explains_excluded_rows(self):
        dataframe = pd.DataFrame({'revenue': ['100', 'abc', '300']})
        aov = kpis_by_name(dataframe)['Average Order Value']
        self.assertEqual(aov.value, 200.0)
        self.assertIn('2 of 3 rows', aov.note)

    def test_no_note_when_all_rows_are_valid(self):
        aov = kpis_by_name(pd.DataFrame({'revenue': [100.0, 300.0]}))['Average Order Value']
        self.assertEqual(aov.note, '')

    def test_non_numeric_note_wording(self):
        revenue = kpis_by_name(pd.DataFrame({'revenue': ['100', 'abc']}))['Total Revenue']
        self.assertIn('1 non-numeric value(s) ignored', revenue.note)
