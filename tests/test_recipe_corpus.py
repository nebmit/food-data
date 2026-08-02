import re
import sys
import unittest
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RECIPE_ROOT = REPOSITORY_ROOT / "recipes"
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import yaml_parser  # noqa: E402


EXPECTED_RECIPE_DIRECTORIES = {
    "Beef and Rice with Cucumber Salad",
    "Chicken Fried Rice",
    "Chili with Sweet Potato",
    "Chocolate Chip Cookies",
    "Christmas Chocolate Bark",
    "Fluffy Pancakes",
    "Garlic Parmesan Fries",
    "Gnocchi with Broccoli and Steak",
    "Gourmet Burger",
    "Green Beans on Rice",
    "Rainbow Noodles",
    "Shrimp Paella",
    "Soft Chocolate Chip Cookies",
    "Spinach and Sausage Ragu",
    "Tarte au Citron",
    "Tater Tot Casserole",
    "White Chocolate Blondies",
}
LEGACY_ROOT_KEYS = {
    "ingredients",
    "pantry",
    "instructions",
    "common_ingredients",
}


def load_recipe(directory_name):
    recipe_path = RECIPE_ROOT / directory_name / "recipe.yaml"
    return yaml.safe_load(recipe_path.read_text(encoding="utf-8"))


def ingredient_inputs(recipe):
    return [
        input_value
        for table in recipe["tables"]
        for stage in table["stages"]
        for input_value in stage.get("inputs", [])
        if "ingredient" in input_value
    ]


def named_inputs(recipe, ingredient_name):
    expected = ingredient_name.casefold()
    return [
        input_value
        for input_value in ingredient_inputs(recipe)
        if input_value["ingredient"].casefold() == expected
    ]


def all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from all_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from all_strings(nested)


class RecipeCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recipes = {
            name: load_recipe(name) for name in EXPECTED_RECIPE_DIRECTORIES
        }

    def test_exactly_the_expected_17_recipe_files_exist(self):
        recipe_files = sorted(
            path
            for path in RECIPE_ROOT.rglob("recipe.y*ml")
            if path.name in {"recipe.yaml", "recipe.yml"}
        )
        self.assertEqual(17, len(recipe_files))
        self.assertEqual(
            EXPECTED_RECIPE_DIRECTORIES,
            {path.parent.name for path in recipe_files},
        )

    def test_every_recipe_validates_as_schema_v2(self):
        for name in sorted(EXPECTED_RECIPE_DIRECTORIES):
            with self.subTest(recipe=name):
                path = RECIPE_ROOT / name / "recipe.yaml"
                status, message = yaml_parser.verify(path)
                self.assertEqual(0, status, message)

    def test_no_recipe_retains_legacy_top_level_sections(self):
        for name, recipe in self.recipes.items():
            with self.subTest(recipe=name):
                self.assertEqual(2, recipe.get("schema_version"))
                self.assertFalse(LEGACY_ROOT_KEYS & set(recipe))

    def test_green_beans_uses_100_ml_hoisin(self):
        inputs = named_inputs(self.recipes["Green Beans on Rice"], "Hoisin sauce")
        self.assertEqual(
            [(100, "ml")],
            [(entry.get("quantity"), entry.get("measurement")) for entry in inputs],
        )

    def test_chicken_fried_rice_has_two_15_ml_oil_uses(self):
        inputs = named_inputs(self.recipes["Chicken Fried Rice"], "Vegetable oil")
        self.assertEqual(
            [(15, "ml"), (15, "ml")],
            [(entry.get("quantity"), entry.get("measurement")) for entry in inputs],
        )

    def test_gnocchi_uses_15_ml_oil(self):
        inputs = named_inputs(
            self.recipes["Gnocchi with Broccoli and Steak"], "Olive oil"
        )
        self.assertEqual(
            [(15, "ml")],
            [(entry.get("quantity"), entry.get("measurement")) for entry in inputs],
        )

    def test_beef_spice_mix_uses_packet_measurement(self):
        inputs = [
            entry
            for entry in ingredient_inputs(
                self.recipes["Beef and Rice with Cucumber Salad"]
            )
            if "spice mix" in entry["ingredient"].casefold()
        ]
        self.assertEqual(1, len(inputs))
        self.assertEqual("packet", inputs[0].get("measurement"))

    def test_gourmet_burger_lettuce_uses_leaf_measurement(self):
        inputs = named_inputs(self.recipes["Gourmet Burger"], "Lettuce")
        self.assertEqual(1, len(inputs))
        self.assertEqual("leaf", inputs[0].get("measurement"))

    def test_tarte_has_split_sugar_and_both_corrected_water_uses(self):
        recipe = self.recipes["Tarte au Citron"]
        sugar_inputs = named_inputs(recipe, "Sugar")
        water_inputs = named_inputs(recipe, "Water")

        self.assertEqual(2, len(sugar_inputs))
        self.assertCountEqual(
            [(100, "grams"), (120, "grams")],
            [
                (entry.get("quantity"), entry.get("measurement"))
                for entry in sugar_inputs
            ],
        )
        self.assertCountEqual(
            [(215, "ml"), (1, "tablespoon")],
            [(entry.get("quantity"), entry.get("measurement")) for entry in water_inputs],
        )

    def test_ragu_has_qualitative_pasta_water_and_100_ml_sauce_water(self):
        water_inputs = named_inputs(
            self.recipes["Spinach and Sausage Ragu"], "Water"
        )
        amountless = [
            entry
            for entry in water_inputs
            if "quantity" not in entry and "measurement" not in entry
        ]
        measured = [
            entry
            for entry in water_inputs
            if "quantity" in entry or "measurement" in entry
        ]

        self.assertEqual(1, len(amountless))
        self.assertTrue(amountless[0].get("hint"))
        self.assertEqual(
            [(100, "ml")],
            [(entry.get("quantity"), entry.get("measurement")) for entry in measured],
        )

    def test_soft_cookies_cool_on_tray_before_transfer(self):
        recipe = self.recipes["Soft Chocolate Chip Cookies"]
        process_text = " ".join(
            text
            for table in recipe["tables"]
            for stage in table["stages"]
            for text in (stage.get("action", ""), stage.get("hint", ""))
        ).casefold()
        cooling = re.search(r"cool on (?:the )?tray", process_text)
        transfer = re.search(r"transfer", process_text)

        self.assertIsNotNone(cooling)
        self.assertIsNotNone(transfer)
        self.assertLess(cooling.start(), transfer.start())

    def test_tater_tot_has_no_literal_smart_quote_wrappers(self):
        recipe = self.recipes["Tater Tot Casserole"]
        for value in all_strings(recipe):
            with self.subTest(value=value):
                self.assertNotIn(value[0], yaml_parser.SMART_QUOTES)
                self.assertNotIn(value[-1], yaml_parser.SMART_QUOTES)


if __name__ == "__main__":
    unittest.main()
