import pandas as pd
from django.test import SimpleTestCase

from apps.datasets.processing import profile_dataframe


class ProfileDataframeTests(SimpleTestCase):
    def test_clean_dataset_scores_100(self):
        profile = profile_dataframe(pd.DataFrame({'revenue': [1.0, 2.0], 'name': ['a', 'b']}))
        self.assertEqual(profile.quality_score, 100.0)
        self.assertEqual(profile.invalid_cell_count, 0)

    def test_non_numeric_value_in_numeric_column_is_invalid(self):
        dataframe = pd.DataFrame({
            'revenue': ['1', '2', '3', '4', '5', 'x'],
            'name': list('abcdef'),
        })
        profile = profile_dataframe(dataframe)
        revenue, name = profile.columns
        self.assertEqual(profile.invalid_cell_count, 1)
        self.assertEqual(revenue['invalid_count'], 1)
        self.assertEqual(revenue['invalid_percentage'], 16.67)
        self.assertEqual(name['invalid_count'], 0)
        self.assertEqual(profile.quality_score, 91.67)

    def test_text_column_is_not_flagged(self):
        profile = profile_dataframe(pd.DataFrame({'product': ['A', 'B', 'C', 'D']}))
        self.assertEqual(profile.invalid_cell_count, 0)

    def test_mixed_identifier_column_is_not_flagged(self):
        profile = profile_dataframe(pd.DataFrame({'code': ['123', 'A45', '678', 'B90']}))
        self.assertEqual(profile.invalid_cell_count, 0)

    def test_numeric_strings_are_not_invalid(self):
        profile = profile_dataframe(pd.DataFrame({'zip': ['12345', '23456', '34567']}))
        self.assertEqual(profile.invalid_cell_count, 0)

    def test_missing_values_are_not_counted_as_invalid(self):
        profile = profile_dataframe(pd.DataFrame({'revenue': ['1', '2', None, '4', '5', '6']}))
        self.assertEqual(profile.columns[0]['missing_count'], 1)
        self.assertEqual(profile.invalid_cell_count, 0)
        self.assertEqual(profile.quality_score, 83.33)

    def test_real_numeric_column_with_gaps_only_counts_missing(self):
        profile = profile_dataframe(pd.DataFrame({'revenue': [1.0, 2.0, None]}))
        self.assertEqual(profile.invalid_cell_count, 0)
        self.assertEqual(profile.quality_score, 66.67)

    def test_duplicate_rows_reduce_the_score(self):
        dataframe = pd.DataFrame({'a': [1, 1, 2, 3], 'b': ['x', 'x', 'y', 'z']})
        profile = profile_dataframe(dataframe)
        self.assertEqual(profile.duplicate_row_count, 1)
        self.assertEqual(profile.quality_score, 75.0)

    def test_empty_dataset_does_not_crash(self):
        profile = profile_dataframe(pd.DataFrame(columns=['a', 'b']))
        self.assertEqual(profile.row_count, 0)
        self.assertEqual(profile.column_count, 2)
        self.assertEqual(profile.quality_score, 0.0)
        self.assertEqual([c['invalid_count'] for c in profile.columns], [0, 0])
