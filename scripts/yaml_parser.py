"""Validation for version 2 of the recipe YAML contract."""

import collections
import math
import re

import yaml


ALLOWED_MEASUREMENTS = {
    "grams",
    "ml",
    "unit",
    "teaspoon",
    "tablespoon",
    "clove",
    "pinch",
    "can",
    "bunch",
    "slice",
    "packet",
    "leaf",
}

ROOT_REQUIRED_KEYS = {"schema_version", "meta", "portion", "items", "tables"}
ROOT_OPTIONAL_KEYS = {"tags", "note"}
META_KEYS = {"description", "source", "cuisine"}
PORTION_KEYS = {
    "quantity",
    "descriptor",
    "active_time_minutes",
    "passive_time_minutes",
    "complexity_rating",
    "mayhem_rating",
}
ITEM_REQUIRED_KEYS = {"name"}
ITEM_OPTIONAL_KEYS = {"quantity", "sub"}
TABLE_KEYS = {"name", "stages"}
STAGE_REQUIRED_KEYS = {"id", "action"}
STAGE_OPTIONAL_KEYS = {"inputs", "hint", "setup", "duration_minutes"}
INGREDIENT_INPUT_REQUIRED_KEYS = {"ingredient"}
INGREDIENT_INPUT_OPTIONAL_KEYS = {"quantity", "measurement", "hint"}
STAGE_INPUT_REQUIRED_KEYS = {"stage"}
STAGE_INPUT_OPTIONAL_KEYS = {"part"}

STAGE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
BRACKET_REFERENCE_PATTERN = re.compile(r"\[[^\[\]\n]+\]")
CURLY_REFERENCE_PATTERN = re.compile(r"\{[^{}\n]+\}")
SMART_QUOTES = frozenset("\u2018\u2019\u201c\u201d")


def verify(file_path):
    """Validate one recipe file and return ``(status_code, message)``.

    Status 0 means valid, 1 means that the file could not be parsed, and 2
    means that parsed YAML did not conform to the recipe schema.
    """

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        return 1, f"Error parsing YAML file: {exc}"

    errors = validate(data)
    if errors:
        return 2, "\n".join(errors)
    return 0, f"File {file_path} is valid."


def validate(data):
    """Return all schema errors for already-parsed recipe data."""

    errors = []
    if not isinstance(data, dict):
        return ["The YAML document root must be a mapping"]

    _validate_exact_keys(
        data,
        "root",
        ROOT_REQUIRED_KEYS,
        ROOT_OPTIONAL_KEYS,
        errors,
    )

    if "schema_version" in data:
        value = data["schema_version"]
        if type(value) is not int or value != 2:
            errors.append("'schema_version' must be the integer 2")

    if "meta" in data:
        _validate_meta(data["meta"], errors)
    if "portion" in data:
        _validate_portion(data["portion"], errors)
    if "tags" in data:
        _validate_string_list(data["tags"], "tags", errors)
    if "items" in data:
        _validate_items(data["items"], errors)
    if "tables" in data:
        _validate_tables(data["tables"], errors)
    if "note" in data:
        _validate_string_list(data["note"], "note", errors)

    return errors


def _validate_meta(meta, errors):
    if not isinstance(meta, dict):
        errors.append("'meta' must be a mapping")
        return

    _validate_exact_keys(meta, "meta", META_KEYS, set(), errors)
    for key in ("description", "source", "cuisine"):
        if key in meta:
            _validate_string(meta[key], f"meta.{key}", errors)


def _validate_portion(portion, errors):
    if not isinstance(portion, dict):
        errors.append("'portion' must be a mapping")
        return

    _validate_exact_keys(portion, "portion", PORTION_KEYS, set(), errors)

    if "quantity" in portion:
        _validate_positive_integer(portion["quantity"], "portion.quantity", errors)
    if "descriptor" in portion:
        _validate_string(portion["descriptor"], "portion.descriptor", errors)

    for key in ("active_time_minutes", "passive_time_minutes"):
        if key not in portion:
            continue
        value = portion[key]
        if type(value) is not int or value < 0:
            errors.append(f"'portion.{key}' must be a non-negative integer")

    for key in ("complexity_rating", "mayhem_rating"):
        if key not in portion:
            continue
        value = portion[key]
        if type(value) is not int or not 1 <= value <= 5:
            errors.append(f"'portion.{key}' must be an integer between 1 and 5")


def _validate_string_list(value, path, errors):
    if not isinstance(value, list):
        errors.append(f"'{path}' must be a list")
        return

    for index, entry in enumerate(value):
        _validate_string(entry, f"{path}[{index}]", errors)


def _validate_items(items, errors):
    if not isinstance(items, list) or not items:
        errors.append("'items' must be a non-empty list")
        return

    for index, item in enumerate(items):
        path = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"'{path}' must be a mapping")
            continue

        _validate_exact_keys(
            item,
            path,
            ITEM_REQUIRED_KEYS,
            ITEM_OPTIONAL_KEYS,
            errors,
        )
        if "name" in item:
            _validate_string(item["name"], f"{path}.name", errors)
        if "quantity" in item:
            _validate_positive_number(item["quantity"], f"{path}.quantity", errors)
        if "sub" in item:
            _validate_string(item["sub"], f"{path}.sub", errors)


class _StageGraph:
    """Stage bookkeeping shared by the table walk and the final graph checks.

    Only stages already encountered in document order are entered here. That
    makes self-references and all forward references invalid by construction.
    ``complete`` drops to False once a structural problem makes the whole-graph
    checks meaningless, so they stay quiet instead of piling onto the real error.
    """

    def __init__(self):
        self.seen = {}  # stage id -> (table index, stage index)
        self.table_results = {}  # table index -> final stage id
        self.setup_ids = set()
        self.order = []  # stage ids in document order
        self.consumers = collections.Counter()  # stage id -> times used as food
        self.references = []  # (input path, stage id, names a part)
        self.complete = True


def _validate_tables(tables, errors):
    if not isinstance(tables, list) or not tables:
        errors.append("'tables' must be a non-empty list")
        return

    graph = _StageGraph()

    for table_index, table in enumerate(tables):
        table_path = f"tables[{table_index}]"
        if not isinstance(table, dict):
            errors.append(f"'{table_path}' must be a mapping")
            graph.complete = False
            continue

        _validate_exact_keys(table, table_path, TABLE_KEYS, set(), errors)
        if "name" in table:
            _validate_string(table["name"], f"{table_path}.name", errors)

        if "stages" not in table:
            graph.complete = False
            continue
        stages = table["stages"]
        if not isinstance(stages, list) or not stages:
            errors.append(f"'{table_path}.stages' must be a non-empty list")
            graph.complete = False
            continue

        for stage_index, stage in enumerate(stages):
            _validate_stage(
                stage,
                f"{table_path}.stages[{stage_index}]",
                table_index,
                stage_index,
                graph,
                errors,
            )

        final_stage = stages[-1]
        if isinstance(final_stage, dict):
            final_id = final_stage.get("id")
            if isinstance(final_id, str) and STAGE_ID_PATTERN.fullmatch(final_id):
                if final_id in graph.setup_ids:
                    errors.append(
                        f"'{table_path}.stages[{len(stages) - 1}]' is the table "
                        "result and must not be a setup stage"
                    )
                else:
                    graph.table_results[table_index] = final_id

    _validate_stage_graph(graph, errors)


def _validate_stage(stage, path, table_index, stage_index, graph, errors):
    if not isinstance(stage, dict):
        errors.append(f"'{path}' must be a mapping")
        graph.complete = False
        return

    _validate_exact_keys(stage, path, STAGE_REQUIRED_KEYS, STAGE_OPTIONAL_KEYS, errors)

    stage_id = stage.get("id")
    valid_stage_id = _validate_stage_id(stage_id, f"{path}.id", errors)

    if "action" in stage:
        _validate_string(stage["action"], f"{path}.action", errors)
    if "hint" in stage:
        _validate_string(stage["hint"], f"{path}.hint", errors)
    if "duration_minutes" in stage:
        _validate_positive_integer(
            stage["duration_minutes"], f"{path}.duration_minutes", errors
        )

    is_setup = False
    if "setup" in stage:
        if stage["setup"] is not True:
            errors.append(f"'{path}.setup' must be the boolean true when present")
        else:
            is_setup = True
            if stage.get("inputs"):
                errors.append(f"'{path}' is a setup stage and must not take inputs")

    # Inputs are checked before the stage is registered, so a stage cannot
    # reference itself.
    if "inputs" in stage:
        _validate_inputs(stage["inputs"], f"{path}.inputs", table_index, graph, errors)

    if not valid_stage_id:
        graph.complete = False
        return

    if stage_id in graph.seen:
        first_table, first_stage = graph.seen[stage_id]
        errors.append(
            f"'{path}.id' duplicates stage id '{stage_id}' first used "
            f"at tables[{first_table}].stages[{first_stage}]"
        )
        graph.complete = False
        return

    graph.seen[stage_id] = (table_index, stage_index)
    graph.order.append(stage_id)
    if is_setup:
        graph.setup_ids.add(stage_id)


def _validate_stage_graph(graph, errors):
    """Check the rules that only hold once every stage has been seen."""

    for path, reference, names_part in graph.references:
        if graph.consumers[reference] > 1 and not names_part:
            errors.append(
                f"'{path}' must name a 'part' because stage '{reference}' feeds "
                "more than one later stage"
            )

    if not graph.complete or not graph.order:
        return

    unused = [
        stage_id
        for stage_id in graph.order
        if stage_id not in graph.setup_ids and not graph.consumers[stage_id]
    ]
    if len(unused) != 1:
        rendered = ", ".join(repr(stage_id) for stage_id in unused) or "none"
        errors.append(
            "'tables' must contain exactly one unused stage holding the finished "
            f"dish; found: {rendered}"
        )
        return

    if unused[0] != graph.order[-1]:
        errors.append(
            f"'tables' finished dish '{unused[0]}' must be the last stage of the "
            "last table"
        )


def _validate_inputs(inputs, path, table_index, graph, errors):
    if not isinstance(inputs, list):
        errors.append(f"'{path}' must be a list")
        return

    # An empty list is valid for a setup action, as is omitting `inputs`.
    seen_ingredient = False
    for input_index, input_value in enumerate(inputs):
        input_path = f"{path}[{input_index}]"
        if not isinstance(input_value, dict):
            errors.append(f"'{input_path}' must be a mapping")
            continue

        has_ingredient = "ingredient" in input_value
        has_stage = "stage" in input_value
        if has_ingredient == has_stage:
            errors.append(
                f"'{input_path}' must contain exactly one of 'ingredient' or 'stage'"
            )
            allowed_keys = (
                INGREDIENT_INPUT_REQUIRED_KEYS
                | INGREDIENT_INPUT_OPTIONAL_KEYS
                | STAGE_INPUT_REQUIRED_KEYS
                | STAGE_INPUT_OPTIONAL_KEYS
            )
            _validate_unknown_keys(input_value, input_path, allowed_keys, errors)
            continue

        if has_ingredient:
            seen_ingredient = True
            _validate_ingredient_input(input_value, input_path, errors)
            continue

        # Row order is visible in a rendered table, so prepared inputs lead.
        if seen_ingredient:
            errors.append(
                f"'{input_path}' must be listed before the ingredient inputs"
            )
        _validate_stage_input(input_value, input_path, table_index, graph, errors)


def _validate_ingredient_input(input_value, path, errors):
    _validate_exact_keys(
        input_value,
        path,
        INGREDIENT_INPUT_REQUIRED_KEYS,
        INGREDIENT_INPUT_OPTIONAL_KEYS,
        errors,
    )
    _validate_string(input_value["ingredient"], f"{path}.ingredient", errors)

    has_quantity = "quantity" in input_value
    has_measurement = "measurement" in input_value
    if has_quantity != has_measurement:
        errors.append(
            f"'{path}' must provide 'quantity' and 'measurement' together"
        )

    if has_quantity:
        _validate_positive_number(input_value["quantity"], f"{path}.quantity", errors)
    if has_measurement:
        measurement = input_value["measurement"]
        if _validate_string(measurement, f"{path}.measurement", errors):
            if measurement not in ALLOWED_MEASUREMENTS:
                allowed = ", ".join(sorted(ALLOWED_MEASUREMENTS))
                errors.append(
                    f"'{path}.measurement' value '{measurement}' is not allowed. "
                    f"Use one of: {allowed}"
                )

    if "hint" in input_value:
        _validate_string(input_value["hint"], f"{path}.hint", errors)
    elif not has_quantity and not has_measurement:
        errors.append(f"'{path}' must include a non-empty 'hint' when amountless")


def _validate_stage_input(input_value, path, table_index, graph, errors):
    _validate_exact_keys(
        input_value,
        path,
        STAGE_INPUT_REQUIRED_KEYS,
        STAGE_INPUT_OPTIONAL_KEYS,
        errors,
    )
    names_part = "part" in input_value
    if names_part:
        _validate_string(input_value["part"], f"{path}.part", errors)

    reference = input_value["stage"]
    if not _validate_stage_id(reference, f"{path}.stage", errors):
        return

    if reference not in graph.seen:
        errors.append(
            f"'{path}.stage' must reference an earlier stage; '{reference}' "
            "has not been defined yet"
        )
        return

    if reference in graph.setup_ids:
        errors.append(
            f"'{path}.stage' must not reference setup stage '{reference}' as food"
        )
        return

    graph.consumers[reference] += 1
    graph.references.append((path, reference, names_part))

    referenced_table, _ = graph.seen[reference]
    if referenced_table == table_index:
        return

    if graph.table_results.get(referenced_table) != reference:
        errors.append(
            f"'{path}.stage' cross-table reference '{reference}' must target "
            "the final stage of its earlier table"
        )


def _validate_stage_id(value, path, errors):
    if not _validate_string(value, path, errors):
        return False
    if not STAGE_ID_PATTERN.fullmatch(value):
        errors.append(f"'{path}' must be a snake_case identifier")
        return False
    return True


def _validate_exact_keys(value, path, required, optional, errors):
    actual = set(value)
    for key in sorted(required - actual):
        errors.append(f"'{path}' missing required key '{key}'")
    _validate_unknown_keys(value, path, required | optional, errors)


def _validate_unknown_keys(value, path, allowed, errors):
    unknown = set(value) - allowed
    if unknown:
        rendered = ", ".join(repr(key) for key in sorted(unknown, key=str))
        errors.append(f"'{path}' contains unknown key(s): {rendered}")


def _validate_string(value, path, errors):
    if not isinstance(value, str) or not value or value != value.strip():
        errors.append(f"'{path}' must be a non-empty, trimmed string")
        return False

    valid = True
    if value[0] in SMART_QUOTES or value[-1] in SMART_QUOTES:
        errors.append(f"'{path}' must not use literal smart-quote wrappers")
        valid = False
    if BRACKET_REFERENCE_PATTERN.search(value):
        errors.append(f"'{path}' contains a legacy bracket reference")
        valid = False
    if CURLY_REFERENCE_PATTERN.search(value):
        errors.append(f"'{path}' contains legacy proportion/reference syntax")
        valid = False
    return valid


def _validate_positive_number(value, path, errors):
    if type(value) is int:
        valid = value > 0
    elif type(value) is float:
        valid = math.isfinite(value) and value > 0
    else:
        valid = False
    if not valid:
        errors.append(f"'{path}' must be a positive finite number")


def _validate_positive_integer(value, path, errors):
    if type(value) is not int or value <= 0:
        errors.append(f"'{path}' must be a positive integer")
