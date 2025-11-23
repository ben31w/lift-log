from unittest import TestCase

import src.sql_utility as su
import src.ui.tab_training_arcs as arcs

class TestFunctions(TestCase):
    def test_format_sets_string_for_cell_two_wts(self):
        self.assertEqual(
            "2x8 @ 135\n6,5 @ 145",
            arcs.format_sets_string_for_cell("2x8@135,6,5@145"),
        )

    def test_format_sets_string_for_cell_two_wts_with_spaces(self):
        self.assertEqual(
            "2x8 @ 135\n6,5 @ 145",
            arcs.format_sets_string_for_cell("2x8@135, 6, 5@145"),
        )

    def test_format_sets_string_for_cell_one_wt_with_spaces(self):
        self.assertEqual(
            "10,9,5 @ 155",
            arcs.format_sets_string_for_cell("10, 9, 5 @ 155"),
        )