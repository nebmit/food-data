"""Invariants that hold for every recipe in the corpus.

These checks are deliberately glob-driven: adding a recipe must never require
editing this file. They cover the writing conventions the schema validator
does not encode, plus a gate that every recipe still validates.
"""

import sys
import unittest
from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RECIPE_ROOT = REPOSITORY_ROOT / "recipes"
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import yaml_parser  # noqa: E402


LEGACY_ROOT_KEYS = {"ingredients", "pantry", "instructions", "common_ingredients"}

# Words that stay lowercase inside a Title Case directory name.
TITLE_CASE_MINOR_WORDS = {"a", "and", "au", "de", "in", "la", "on", "the", "with"}

# Hints start lowercase because they continue the action. Add a term here only
# when a hint genuinely has to open with a proper noun.
HINT_PROPER_NOUNS = frozenset()


def recipe_paths():
    return sorted(RECIPE_ROOT.glob("*/recipe.yaml"))


def load(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def all_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from all_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from all_strings(nested)


def stages(recipe):
    for table in recipe["tables"]:
        for stage in table["stages"]:
            yield stage


def ingredient_inputs(recipe):
    for stage in stages(recipe):
        for stage_input in stage.get("inputs", []):
            if "ingredient" in stage_input:
                yield stage_input


class RecipeCorpusInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = recipe_paths()
        cls.recipes = {path.parent.name: load(path) for path in cls.paths}

    def test_corpus_is_not_empty(self):
        self.assertTrue(self.paths, "no recipes found under recipes/")

    def test_every_recipe_directory_holds_exactly_one_recipe_file(self):
        # A misnamed file would be skipped silently by the format check.
        for directory in sorted(path for path in RECIPE_ROOT.iterdir() if path.is_dir()):
            with self.subTest(directory=directory.name):
                found = sorted(path.name for path in directory.glob("recipe.y*ml"))
                self.assertEqual(["recipe.yaml"], found)

    def test_every_recipe_validates(self):
        for path in self.paths:
            with self.subTest(recipe=path.parent.name):
                status, message = yaml_parser.verify(path)
                self.assertEqual(0, status, message)

    def test_no_recipe_retains_legacy_top_level_sections(self):
        for name, recipe in self.recipes.items():
            with self.subTest(recipe=name):
                self.assertEqual(2, recipe.get("schema_version"))
                self.assertFalse(LEGACY_ROOT_KEYS & set(recipe))

    def test_no_string_is_wrapped_in_smart_quotes(self):
        for name, recipe in self.recipes.items():
            for value in all_strings(recipe):
                with self.subTest(recipe=name, value=value):
                    self.assertNotIn(value[0], yaml_parser.SMART_QUOTES)
                    self.assertNotIn(value[-1], yaml_parser.SMART_QUOTES)

    def test_directory_names_are_title_case(self):
        for path in self.paths:
            name = path.parent.name
            with self.subTest(recipe=name):
                words = name.split()
                self.assertTrue(words[0][:1].isupper(), name)
                for word in words[1:]:
                    if word.lower() in TITLE_CASE_MINOR_WORDS:
                        self.assertTrue(word.islower(), name)
                    else:
                        self.assertTrue(word[:1].isupper(), name)

    def test_ingredient_item_and_table_names_are_sentence_case(self):
        for name, recipe in self.recipes.items():
            named = (
                [entry["ingredient"] for entry in ingredient_inputs(recipe)]
                + [item["name"] for item in recipe["items"]]
                + [table["name"] for table in recipe["tables"]]
            )
            for value in named:
                with self.subTest(recipe=name, value=value):
                    self.assertTrue(value[:1].isupper(), value)
                    for word in value.split()[1:]:
                        self.assertFalse(word[:1].isupper(), value)

    def test_actions_start_with_a_capitalised_verb(self):
        for name, recipe in self.recipes.items():
            for stage in stages(recipe):
                with self.subTest(recipe=name, stage=stage["id"]):
                    self.assertTrue(stage["action"][:1].isupper(), stage["action"])

    def test_hints_start_lowercase(self):
        for name, recipe in self.recipes.items():
            hints = [stage["hint"] for stage in stages(recipe) if "hint" in stage]
            hints += [
                entry["hint"] for entry in ingredient_inputs(recipe) if "hint" in entry
            ]
            for hint in hints:
                with self.subTest(recipe=name, hint=hint):
                    if hint.split()[0] in HINT_PROPER_NOUNS:
                        continue
                    self.assertFalse(hint[:1].isupper(), hint)


if __name__ == "__main__":
    unittest.main()
