import copy
import math
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "scripts"))

import yaml_parser  # noqa: E402


def valid_recipe():
    return {
        "schema_version": 2,
        "meta": {
            "description": "A compact test recipe.",
            "source": "Original",
            "cuisine": "Test",
        },
        "portion": {
            "quantity": 2,
            "descriptor": "servings",
            "active_time_minutes": 5,
            "passive_time_minutes": 0,
            "complexity_rating": 1,
            "mayhem_rating": 1,
        },
        "items": [{"name": "Bowl", "quantity": 1}],
        "tables": [
            {
                "name": "Assembly",
                "stages": [
                    {
                        "id": "mix_dough",
                        "inputs": [
                            {
                                "ingredient": "Flour",
                                "quantity": 100,
                                "measurement": "grams",
                            }
                        ],
                        "action": "Mix",
                    }
                ],
            }
        ],
    }


class RecipeValidatorTests(unittest.TestCase):
    def assert_valid(self, recipe):
        self.assertEqual([], yaml_parser.validate(recipe))

    def assert_invalid(self, recipe, message):
        errors = yaml_parser.validate(recipe)
        self.assertTrue(errors, "expected recipe to be invalid")
        self.assertIn(message, "\n".join(errors))

    def test_valid_minimal_recipe_and_input_free_setup_stages(self):
        recipe = valid_recipe()
        recipe["tags"] = ["Vegetarian"]
        recipe["note"] = ["Serve immediately."]
        recipe["items"][0]["sub"] = "or mixing bowl"
        recipe["tables"][0]["stages"].insert(
            0,
            {
                "id": "preheat_oven",
                "setup": True,
                "action": "Preheat oven",
                "hint": "180°C",
            },
        )
        recipe["tables"][0]["stages"].insert(
            1,
            {
                "id": "line_tray",
                "setup": True,
                "inputs": [],
                "action": "Line tray",
            },
        )

        self.assert_valid(recipe)

    def test_valid_linear_flow_and_repeated_per_use_ingredient(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"] = [
            {
                "id": "first_fry",
                "inputs": [
                    {
                        "ingredient": "Oil",
                        "quantity": 15,
                        "measurement": "ml",
                    }
                ],
                "action": "Fry vegetables",
            },
            {
                "id": "second_fry",
                "inputs": [
                    {"stage": "first_fry"},
                    {
                        "ingredient": "Oil",
                        "quantity": 15,
                        "measurement": "ml",
                    },
                ],
                "action": "Fry rice",
                "hint": "2 min",
            },
        ]

        self.assert_valid(recipe)

    def test_valid_component_merge_and_reused_stage_output(self):
        recipe = valid_recipe()
        recipe["tables"] = [
            {
                "name": "Base",
                "stages": [
                    {
                        "id": "prepare_base",
                        "inputs": [
                            {
                                "ingredient": "Dough",
                                "quantity": 1,
                                "measurement": "unit",
                            }
                        ],
                        "action": "Prepare",
                    },
                    {
                        "id": "shape_base",
                        "inputs": [{"stage": "prepare_base", "part": "half"}],
                        "action": "Shape half",
                    },
                    {
                        "id": "finish_base",
                        "inputs": [
                            {"stage": "prepare_base", "part": "remaining half"},
                            {"stage": "shape_base"},
                        ],
                        "action": "Finish",
                    },
                ],
            },
            {
                "name": "Sauce",
                "stages": [
                    {
                        "id": "make_sauce",
                        "inputs": [
                            {"ingredient": "Salt", "hint": "to taste"}
                        ],
                        "action": "Mix",
                    }
                ],
            },
            {
                "name": "Assembly",
                "stages": [
                    {
                        "id": "assemble_dish",
                        "inputs": [
                            {"stage": "finish_base"},
                            {"stage": "make_sauce"},
                        ],
                        "action": "Assemble",
                    }
                ],
            },
        ]

        self.assert_valid(recipe)

    def test_all_measurements_are_valid(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"][0]["inputs"] = [
            {
                "ingredient": f"Ingredient {index}",
                "quantity": 1,
                "measurement": measurement,
            }
            for index, measurement in enumerate(sorted(yaml_parser.ALLOWED_MEASUREMENTS))
        ]

        self.assertEqual(12, len(yaml_parser.ALLOWED_MEASUREMENTS))
        self.assert_valid(recipe)

    def test_root_must_be_mapping(self):
        for value in (None, [], "recipe"):
            with self.subTest(value=value):
                self.assert_invalid(value, "root must be a mapping")

    def test_parse_failure_returns_status_one(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "recipe.yaml"
            path.write_text("tables: [", encoding="utf-8")
            status, message = yaml_parser.verify(path)

        self.assertEqual(1, status)
        self.assertIn("Error parsing YAML file", message)

    def test_root_keys_are_exact_and_schema_version_is_required(self):
        recipe = valid_recipe()
        recipe["ingredients"] = []
        recipe["pantry"] = []
        recipe["instructions"] = []
        self.assert_invalid(recipe, "unknown key(s)")

        recipe = valid_recipe()
        del recipe["schema_version"]
        self.assert_invalid(recipe, "missing required key 'schema_version'")

        for version in (1, 2.0, True, "2"):
            with self.subTest(version=version):
                recipe = valid_recipe()
                recipe["schema_version"] = version
                self.assert_invalid(recipe, "must be the integer 2")

    def test_required_container_types_and_non_empty_collections(self):
        cases = (
            ("meta", [], "'meta' must be a mapping"),
            ("portion", [], "'portion' must be a mapping"),
            ("items", {}, "'items' must be a non-empty list"),
            ("items", [], "'items' must be a non-empty list"),
            ("tables", {}, "'tables' must be a non-empty list"),
            ("tables", [], "'tables' must be a non-empty list"),
            ("tags", {}, "'tags' must be a list"),
            ("note", {}, "'note' must be a list"),
        )
        for key, value, message in cases:
            with self.subTest(key=key, value=value):
                recipe = valid_recipe()
                recipe[key] = value
                self.assert_invalid(recipe, message)

    def test_nested_keys_are_exact(self):
        mutations = []

        def add_extra(path):
            def mutate(recipe):
                target = recipe
                for segment in path:
                    target = target[segment]
                target["extra"] = True

            return mutate

        mutations.extend(
            [
                add_extra(["meta"]),
                add_extra(["portion"]),
                add_extra(["items", 0]),
                add_extra(["tables", 0]),
                add_extra(["tables", 0, "stages", 0]),
                add_extra(["tables", 0, "stages", 0, "inputs", 0]),
            ]
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                recipe = valid_recipe()
                mutate(recipe)
                self.assert_invalid(recipe, "unknown key(s)")

    def test_required_nested_keys_are_enforced(self):
        paths = (
            ["meta", "description"],
            ["portion", "quantity"],
            ["items", 0, "name"],
            ["tables", 0, "name"],
            ["tables", 0, "stages", 0, "id"],
            ["tables", 0, "stages", 0, "action"],
        )
        for path in paths:
            with self.subTest(path=path):
                recipe = valid_recipe()
                target = recipe
                for segment in path[:-1]:
                    target = target[segment]
                del target[path[-1]]
                self.assert_invalid(recipe, "missing required key")

    def test_strings_must_be_non_empty_and_already_trimmed(self):
        for value in ("", " ", " padded", "padded ", 3):
            with self.subTest(value=value):
                recipe = valid_recipe()
                recipe["meta"]["description"] = value
                self.assert_invalid(recipe, "non-empty, trimmed string")

    def test_literal_smart_quote_wrappers_are_rejected(self):
        for value in (
            "\u201cMix well.\u201d",
            "\u2018Mix well.\u2019",
            "\u201cMix well.",
            "Mix well.\u201d",
        ):
            with self.subTest(value=value):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"][0]["action"] = value
                self.assert_invalid(recipe, "literal smart-quote wrappers")

    def test_legacy_instruction_markup_is_rejected(self):
        for value, message in (
            ("Mix [Flour]", "legacy bracket reference"),
            ("Mix {half:Flour}", "legacy proportion/reference syntax"),
        ):
            with self.subTest(value=value):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"][0]["action"] = value
                self.assert_invalid(recipe, message)

    def test_portion_numbers_reject_booleans_and_invalid_ranges(self):
        cases = (
            ("quantity", 0, "positive integer"),
            ("quantity", True, "positive integer"),
            ("quantity", 1.5, "positive integer"),
            ("active_time_minutes", -1, "non-negative integer"),
            ("active_time_minutes", True, "non-negative integer"),
            ("passive_time_minutes", 1.5, "non-negative integer"),
            ("complexity_rating", 0, "integer between 1 and 5"),
            ("complexity_rating", True, "integer between 1 and 5"),
            ("mayhem_rating", 6, "integer between 1 and 5"),
        )
        for key, value, message in cases:
            with self.subTest(key=key, value=value):
                recipe = valid_recipe()
                recipe["portion"][key] = value
                self.assert_invalid(recipe, message)

    def test_item_quantity_and_optional_sub_are_validated(self):
        recipe = valid_recipe()
        recipe["items"][0]["quantity"] = 1.5
        self.assert_valid(recipe)

        for value in (0, -1, True, math.inf, math.nan):
            with self.subTest(quantity=value):
                recipe = valid_recipe()
                recipe["items"][0]["quantity"] = value
                self.assert_invalid(recipe, "positive finite number")

        recipe = valid_recipe()
        recipe["items"][0]["sub"] = " "
        self.assert_invalid(recipe, "non-empty, trimmed string")

    def test_tables_and_stages_must_be_non_empty_lists(self):
        for value in (None, {}, []):
            with self.subTest(table_stages=value):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"] = value
                self.assert_invalid(recipe, "must be a non-empty list")

        recipe = valid_recipe()
        recipe["tables"][0]["stages"] = ["Mix"]
        self.assert_invalid(recipe, "must be a mapping")

    def test_stage_ids_are_global_unique_snake_case(self):
        for stage_id in ("MixDough", "mix-dough", "mix__dough", "_mix", "2_mix"):
            with self.subTest(stage_id=stage_id):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"][0]["id"] = stage_id
                self.assert_invalid(recipe, "snake_case identifier")

        recipe = valid_recipe()
        recipe["tables"].append(
            {
                "name": "Second",
                "stages": [{"id": "mix_dough", "action": "Repeat"}],
            }
        )
        self.assert_invalid(recipe, "duplicates stage id 'mix_dough'")

    def test_stage_references_must_point_backward(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"] = [
            {
                "id": "first",
                "inputs": [{"stage": "second"}],
                "action": "Start",
            },
            {"id": "second", "inputs": [{"stage": "first"}], "action": "End"},
        ]
        self.assert_invalid(recipe, "must reference an earlier stage")

        recipe = valid_recipe()
        recipe["tables"][0]["stages"][0]["inputs"] = [{"stage": "mix_dough"}]
        self.assert_invalid(recipe, "must reference an earlier stage")

    def test_cross_table_reference_must_target_earlier_table_final_stage(self):
        recipe = valid_recipe()
        recipe["tables"] = [
            {
                "name": "Component",
                "stages": [
                    {"id": "component_start", "action": "Start"},
                    {
                        "id": "component_result",
                        "inputs": [{"stage": "component_start"}],
                        "action": "Finish",
                    },
                ],
            },
            {
                "name": "Assembly",
                "stages": [
                    {
                        "id": "assemble",
                        "inputs": [{"stage": "component_start"}],
                        "action": "Assemble",
                    }
                ],
            },
        ]
        self.assert_invalid(recipe, "must target the final stage")

    def test_inputs_require_exactly_one_variant(self):
        for input_value in (
            {},
            {"ingredient": "Flour", "stage": "mix_dough"},
        ):
            with self.subTest(input_value=input_value):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"][0]["inputs"] = [input_value]
                self.assert_invalid(recipe, "exactly one of 'ingredient' or 'stage'")

    def test_stage_reference_input_rejects_extra_fields(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"].append(
            {
                "id": "rest_dough",
                "inputs": [{"stage": "mix_dough", "hint": "5 min"}],
                "action": "Rest",
            }
        )
        self.assert_invalid(recipe, "unknown key(s): 'hint'")

    def test_quantity_and_measurement_must_be_paired(self):
        for removed in ("quantity", "measurement"):
            with self.subTest(removed=removed):
                recipe = valid_recipe()
                del recipe["tables"][0]["stages"][0]["inputs"][0][removed]
                self.assert_invalid(recipe, "must provide 'quantity' and 'measurement' together")

    def test_amountless_ingredient_requires_hint(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"][0]["inputs"] = [
            {"ingredient": "Salt", "hint": "to taste"}
        ]
        self.assert_valid(recipe)

        for input_value in (
            {"ingredient": "Salt"},
            {"ingredient": "Salt", "hint": ""},
        ):
            with self.subTest(input_value=input_value):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"][0]["inputs"] = [input_value]
                self.assert_invalid(recipe, "hint")

    def test_ingredient_quantity_is_positive_finite_number_not_boolean(self):
        for value in (0, -1, True, math.inf, -math.inf, math.nan, "1"):
            with self.subTest(quantity=value):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"][0]["inputs"][0]["quantity"] = value
                self.assert_invalid(recipe, "positive finite number")

    def test_measurement_enum_is_closed(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"][0]["inputs"][0]["measurement"] = "cups"
        self.assert_invalid(recipe, "is not allowed")

    def test_item_quantity_is_optional(self):
        recipe = valid_recipe()
        del recipe["items"][0]["quantity"]
        self.assert_valid(recipe)

    def test_part_is_only_allowed_on_stage_inputs(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"].append(
            {
                "id": "rest_dough",
                "inputs": [{"stage": "mix_dough", "part": "half"}],
                "action": "Rest",
            }
        )
        self.assert_valid(recipe)

        recipe = valid_recipe()
        recipe["tables"][0]["stages"][0]["inputs"][0]["part"] = "half"
        self.assert_invalid(recipe, "unknown key(s): 'part'")

        recipe = valid_recipe()
        recipe["tables"][0]["stages"].append(
            {
                "id": "rest_dough",
                "inputs": [{"stage": "mix_dough", "part": " "}],
                "action": "Rest",
            }
        )
        self.assert_invalid(recipe, "non-empty, trimmed string")

    def test_stage_feeding_two_later_stages_requires_part_on_every_reference(self):
        def split_recipe(first_part, second_part):
            recipe = valid_recipe()
            first = {"stage": "mix_dough"}
            second = {"stage": "mix_dough"}
            if first_part:
                first["part"] = first_part
            if second_part:
                second["part"] = second_part
            recipe["tables"][0]["stages"].extend(
                [
                    {"id": "bake_half", "inputs": [first], "action": "Bake"},
                    {
                        "id": "combine_dough",
                        "inputs": [{"stage": "bake_half"}, second],
                        "action": "Combine",
                    },
                ]
            )
            return recipe

        self.assert_valid(split_recipe("baked half", "raw half"))

        for first_part, second_part in (
            (None, None),
            ("baked half", None),
            (None, "raw half"),
        ):
            with self.subTest(first=first_part, second=second_part):
                self.assert_invalid(
                    split_recipe(first_part, second_part),
                    "feeds more than one later stage",
                )

    def test_setup_flag_must_be_true_and_take_no_inputs(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"].insert(
            0, {"id": "preheat_oven", "setup": True, "action": "Preheat oven"}
        )
        self.assert_valid(recipe)

        for value in (False, "true", 1):
            with self.subTest(value=value):
                recipe = valid_recipe()
                recipe["tables"][0]["stages"].insert(
                    0,
                    {"id": "preheat_oven", "setup": value, "action": "Preheat oven"},
                )
                self.assert_invalid(recipe, "must be the boolean true when present")

        recipe = valid_recipe()
        recipe["tables"][0]["stages"].insert(
            0,
            {
                "id": "preheat_oven",
                "setup": True,
                "inputs": [{"ingredient": "Salt", "hint": "to taste"}],
                "action": "Preheat oven",
            },
        )
        self.assert_invalid(recipe, "setup stage and must not take inputs")

    def test_setup_stage_cannot_be_referenced_as_food_or_end_a_table(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"].insert(
            0, {"id": "preheat_oven", "setup": True, "action": "Preheat oven"}
        )
        recipe["tables"][0]["stages"][1]["inputs"].insert(0, {"stage": "preheat_oven"})
        self.assert_invalid(recipe, "must not reference setup stage 'preheat_oven'")

        recipe = valid_recipe()
        recipe["tables"][0]["stages"].append(
            {"id": "preheat_oven", "setup": True, "action": "Preheat oven"}
        )
        self.assert_invalid(recipe, "must not be a setup stage")

    def test_prepared_inputs_must_precede_ingredient_inputs(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"].append(
            {
                "id": "finish_dough",
                "inputs": [
                    {"ingredient": "Salt", "hint": "to taste"},
                    {"stage": "mix_dough"},
                ],
                "action": "Finish",
            }
        )
        self.assert_invalid(recipe, "must be listed before the ingredient inputs")

    def test_recipe_must_end_in_exactly_one_unused_stage(self):
        recipe = valid_recipe()
        recipe["tables"][0]["stages"].append(
            {
                "id": "second_dough",
                "inputs": [{"ingredient": "Salt", "hint": "to taste"}],
                "action": "Mix",
            }
        )
        self.assert_invalid(recipe, "exactly one unused stage holding the finished dish")

        recipe = valid_recipe()
        recipe["tables"][0]["stages"][0] = {
            "id": "preheat_oven",
            "setup": True,
            "action": "Preheat oven",
        }
        self.assert_invalid(recipe, "found: none")

    def test_finished_dish_must_be_the_last_stage_of_the_last_table(self):
        recipe = valid_recipe()
        recipe["tables"].append(
            {
                "name": "Setup",
                "stages": [
                    {"id": "preheat_oven", "setup": True, "action": "Preheat oven"}
                ],
            }
        )
        self.assert_invalid(recipe, "must be the last stage of the last table")


if __name__ == "__main__":
    unittest.main()
