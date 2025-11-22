from unittest import TestCase

import src.sql_utility as su
import src.ui.tab_training_arcs as arcs

class TestFunctions(TestCase):
    def test_format_sets_string_for_cell(self):
        self.assertEqual(
            arcs.format_sets_string_for_cell("2x8@135,6,5@145"),
            "2x8 @ 135\n6,5 @ 145"
        )

    def test_format_sets_string_for_cell_with_spaces(self):
        self.assertEqual(
            arcs.format_sets_string_for_cell("2x8@135, 6, 5@145"),
            "2x8 @ 135\n6,5 @ 145"
        )