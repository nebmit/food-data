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
}


def verify(file_path):
    with open(file_path, "r") as file:
        try:
            data = yaml.safe_load(file)
        except yaml.YAMLError as exc:
            return 1, f"Error parsing YAML file: {exc}"

    errors = []

    # --- meta (required) ---
    if "meta" not in data:
        errors.append("Missing required section: 'meta'")
    else:
        meta = data["meta"]
        if not isinstance(meta, dict):
            errors.append("'meta' must be a mapping")
        else:
            for key in ("description", "source", "cuisine"):
                if key not in meta:
                    errors.append(f"Missing required key 'meta.{key}'")
                elif not isinstance(meta[key], str):
                    errors.append(f"'meta.{key}' must be a string")

    # --- portion (required) ---
    if "portion" not in data:
        errors.append("Missing required section: 'portion'")
    else:
        portion = data["portion"]
        if not isinstance(portion, dict):
            errors.append("'portion' must be a mapping")
        else:
            int_keys = [
                "quantity",
                "active_time_minutes",
                "passive_time_minutes",
                "complexity_rating",
                "mayhem_rating",
            ]
            for key in int_keys + ["descriptor"]:
                if key not in portion:
                    errors.append(f"Missing required key 'portion.{key}'")
            for key in int_keys:
                if key in portion and not isinstance(portion[key], int):
                    errors.append(f"'portion.{key}' must be an integer")
            if "descriptor" in portion and not isinstance(portion["descriptor"], str):
                errors.append("'portion.descriptor' must be a string")
            for key in ("complexity_rating", "mayhem_rating"):
                if key in portion and isinstance(portion[key], int):
                    if not 1 <= portion[key] <= 5:
                        errors.append(f"'portion.{key}' must be between 1 and 5")

    # --- ingredients (required) ---
    ingredient_names = set()
    if "ingredients" not in data:
        errors.append("Missing required section: 'ingredients'")
    else:
        ingredients = data["ingredients"]
        if not isinstance(ingredients, list) or len(ingredients) == 0:
            errors.append("'ingredients' must be a non-empty list")
        else:
            for i, ing in enumerate(ingredients):
                _validate_ingredient(ing, f"ingredients[{i}]", errors, ingredient_names)

    # --- pantry (optional, replaces common_ingredients) ---
    pantry_names = set()
    if "pantry" in data:
        pantry = data["pantry"]
        if not isinstance(pantry, list):
            errors.append("'pantry' must be a list")
        else:
            for i, ing in enumerate(pantry):
                _validate_ingredient(ing, f"pantry[{i}]", errors, pantry_names)

    # --- items (required) ---
    if "items" not in data:
        errors.append("Missing required section: 'items'")
    else:
        items = data["items"]
        if not isinstance(items, list) or len(items) == 0:
            errors.append("'items' must be a non-empty list")
        else:
            for i, item in enumerate(items):
                prefix = f"items[{i}]"
                if not isinstance(item, dict):
                    errors.append(f"'{prefix}' must be a mapping")
                    continue
                if "name" not in item:
                    errors.append(f"'{prefix}' missing 'name'")
                elif not isinstance(item["name"], str):
                    errors.append(f"'{prefix}.name' must be a string")
                if "quantity" not in item:
                    errors.append(f"'{prefix}' missing 'quantity'")
                elif not isinstance(item["quantity"], (int, float)):
                    errors.append(f"'{prefix}.quantity' must be a number")

    # --- instructions (required) ---
    if "instructions" not in data:
        errors.append("Missing required section: 'instructions'")
    else:
        instructions = data["instructions"]
        if not isinstance(instructions, list) or len(instructions) == 0:
            errors.append("'instructions' must be a non-empty list")
        else:
            all_known_names = ingredient_names | pantry_names
            for i, step in enumerate(instructions):
                if not isinstance(step, str):
                    errors.append(f"instructions[{i}] must be a string")
                    continue
                # Validate bracket references
                refs = re.findall(r"\[([^\]]+)\]", step)
                for ref in refs:
                    if ref.lower() not in all_known_names:
                        errors.append(
                            f"instructions[{i}]: ingredient reference [{ref}] "
                            f"not found in ingredients or pantry"
                        )
                # Warn about old-style {proportion:name} references
                old_refs = re.findall(r"\{[^}]+\}", step)
                if old_refs:
                    errors.append(
                        f"instructions[{i}]: found old-style curly-brace reference "
                        f"{old_refs[0]}. Use [name] bracket syntax instead."
                    )

    # --- tags (optional) ---
    if "tags" in data:
        tags = data["tags"]
        if not isinstance(tags, list):
            errors.append("'tags' must be a list")
        else:
            for i, tag in enumerate(tags):
                if not isinstance(tag, str):
                    errors.append(f"tags[{i}] must be a string")

    # --- note (optional) ---
    if "note" in data:
        note = data["note"]
        if not isinstance(note, list):
            errors.append("'note' must be a list")
        else:
            for i, n in enumerate(note):
                if not isinstance(n, str):
                    errors.append(f"note[{i}] must be a string")

    # --- reject old-style keys ---
    if "common_ingredients" in data:
        errors.append(
            "'common_ingredients' is deprecated. Use 'pantry' instead."
        )

    if errors:
        return 2, "\n".join(errors)
    return 0, f"File {file_path} is valid."


def _validate_ingredient(ing, prefix, errors, name_set):
    """Validate a single ingredient/pantry entry and collect its name."""
    if not isinstance(ing, dict):
        errors.append(f"'{prefix}' must be a mapping")
        return
    if "name" not in ing:
        errors.append(f"'{prefix}' missing 'name'")
    elif not isinstance(ing["name"], str):
        errors.append(f"'{prefix}.name' must be a string")
    else:
        name_set.add(ing["name"].lower())
    if "quantity" not in ing:
        errors.append(f"'{prefix}' missing 'quantity'")
    elif not isinstance(ing["quantity"], (int, float)):
        errors.append(f"'{prefix}.quantity' must be a number")
    if "measurement" not in ing:
        errors.append(f"'{prefix}' missing 'measurement'")
    elif not isinstance(ing["measurement"], str):
        errors.append(f"'{prefix}.measurement' must be a string")
    elif ing["measurement"] not in ALLOWED_MEASUREMENTS:
        errors.append(
            f"'{prefix}.measurement' value '{ing['measurement']}' is not allowed. "
            f"Use one of: {', '.join(sorted(ALLOWED_MEASUREMENTS))}"
        )
    # Optional fields
    for opt_key in ("prep", "sub"):
        if opt_key in ing and not isinstance(ing[opt_key], str):
            errors.append(f"'{prefix}.{opt_key}' must be a string")
