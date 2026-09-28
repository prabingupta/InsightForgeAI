import pandas as pd
from django.test import SimpleTestCase

from apps.analytics.breakdowns import compute_breakdowns


def breakdowns_by_title(dataframe: pd.DataFrame) -> dict:
    return {b.title: b for b in compute_breakdowns(dataframe)}


class BreakdownTests(SimpleTestCase):
    def test_revenue_by_product_is_sorted_descending(self):
        dataframe = pd.DataFrame({
            'product': ['A', 'B', 'A'], 'revenue': [100.0, 200.0, 300.0],
        })
        product = breakdowns_by_title(dataframe)['Revenue by Product']
        self.assertEqual(product.labels, ['A', 'B'])
        self.assertEqual(product.values, [400.0, 200.0])

    def test_ties_are_sorted_alphabetically(self):
        dataframe = pd.DataFrame({
            'product': ['B', 'A'], 'revenue': [100.0, 100.0],
        })
        product = breakdowns_by_title(dataframe)['Revenue by Product']
        self.assertEqual(product.labels, ['A', 'B'])

    def test_no_breakdowns_without_revenue_column(self):
        self.assertEqual(compute_breakdowns(pd.DataFrame({'product': ['A']})), [])

    def test_only_available_dimensions_are_returned(self):
        self.assertEqual(compute_breakdowns(pd.DataFrame({'revenue': [1.0, 2.0]})), [])

    def test_categories_are_limited_to_top_ten_with_note(self):
        dataframe = pd.DataFrame({
            'product': [f'P{i:02d}' for i in range(12)],
            'revenue': [float(i + 1) for i in range(12)],
        })
        product = breakdowns_by_title(dataframe)['Revenue by Product']
        self.assertEqual(len(product.labels), 10)
        self.assertEqual(product.labels[0], 'P11')
        self.assertIn('top 10 of 12', product.note)

    def test_invalid_revenue_rows_are_excluded_and_reported(self):
        dataframe = pd.DataFrame({
            'product': ['A', 'B', 'A'], 'revenue': ['100', 'abc', '50'],
        })
        product = breakdowns_by_title(dataframe)['Revenue by Product']
        self.assertEqual(product.labels, ['A'])
        self.assertEqual(product.values, [150.0])
        self.assertIn('1 row(s)', product.note)

    def test_rows_with_missing_labels_are_excluded_and_reported(self):
        dataframe = pd.DataFrame({
            'region': ['North', None, 'North'], 'revenue': [100.0, 500.0, 50.0],
        })
        region = breakdowns_by_title(dataframe)['Revenue by Region']
        self.assertEqual(region.labels, ['North'])
        self.assertEqual(region.values, [150.0])
        self.assertIn('1 row(s)', region.note)

    def test_top_customers_breakdown(self):
        dataframe = pd.DataFrame({
            'customer_id': ['C1', 'C2', 'C1'], 'revenue': [100.0, 500.0, 50.0],
        })
        customers = breakdowns_by_title(dataframe)['Top Customers by Revenue']
        self.assertEqual(customers.labels, ['C2', 'C1'])
        self.assertEqual(customers.values, [500.0, 150.0])

    def test_monthly_revenue_is_chronological(self):
        dataframe = pd.DataFrame({
            'date': ['2026-02-10', '2026-01-05', '2026-02-20'],
            'revenue': [300.0, 100.0, 100.0],
        })
        monthly = breakdowns_by_title(dataframe)['Monthly Revenue']
        self.assertEqual(monthly.labels, ['2026-01', '2026-02'])
        self.assertEqual(monthly.values, [100.0, 400.0])

    def test_monthly_gap_is_reported_not_filled_with_zero(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', '2026-03-05'], 'revenue': [100.0, 200.0],
        })
        monthly = breakdowns_by_title(dataframe)['Monthly Revenue']
        self.assertEqual(monthly.labels, ['2026-01', '2026-03'])
        self.assertIn('no data', monthly.note)

    def test_monthly_revenue_excludes_invalid_dates(self):
        dataframe = pd.DataFrame({
            'date': ['2026-01-05', 'not a date'], 'revenue': [100.0, 50.0],
        })
        monthly = breakdowns_by_title(dataframe)['Monthly Revenue']
        self.assertEqual(monthly.values, [100.0])
        self.assertIn('1 row(s)', monthly.note)

    def test_empty_dataset_does_not_crash(self):
        dataframe = pd.DataFrame(columns=['date', 'product', 'revenue'])
        breakdowns = breakdowns_by_title(dataframe)
        self.assertEqual(breakdowns['Revenue by Product'].labels, [])
        self.assertEqual(breakdowns['Monthly Revenue'].labels, [])
