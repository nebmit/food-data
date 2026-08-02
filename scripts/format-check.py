import os
import sys

import yaml

import yaml_parser


RECIPE_FILENAMES = ("recipe.yaml", "recipe.yml")

# Word endings and modifiers that make two ingredient names look like the same
# shopping item written twice.
PLURAL_SUFFIXES = ("es", "s")


def find_recipe_files():
    """Yield every recipe file below the working directory, in a stable order."""

    for root, dirs, files in os.walk("."):
        dirs.sort()
        for file in sorted(files):
            if file in RECIPE_FILENAMES:
                yield os.path.join(root, file)


def collect_all_ingredients():
    """Collect unique ingredient names and the recipes that use them.

    Returns ``(names, unreadable)`` where ``names`` maps a case-folded name to
    its display form and using recipes.
    """

    names = {}  # case-folded name -> { name, recipes[] }
    unreadable = []

    for file_path in find_recipe_files():
        recipe_name = os.path.basename(os.path.dirname(file_path))
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = yaml.safe_load(file)
        except (OSError, yaml.YAMLError) as exc:
            unreadable.append((file_path, exc))
            continue
        if not isinstance(data, dict):
            unreadable.append((file_path, "root is not a mapping"))
            continue

        recipe_ingredients = {}
        for table in data.get("tables", []) or []:
            if not isinstance(table, dict):
                continue
            for stage in table.get("stages", []) or []:
                if not isinstance(stage, dict):
                    continue
                for stage_input in stage.get("inputs", []) or []:
                    if not isinstance(stage_input, dict):
                        continue
                    ingredient = stage_input.get("ingredient")
                    if not isinstance(ingredient, str):
                        continue
                    ingredient = ingredient.strip()
                    if ingredient:
                        recipe_ingredients.setdefault(ingredient.casefold(), ingredient)

        for key, ingredient in recipe_ingredients.items():
            if key not in names:
                names[key] = {"name": ingredient, "recipes": []}
            names[key]["recipes"].append(recipe_name)

    return names, unreadable


def singular(word):
    for suffix in PLURAL_SUFFIXES:
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def name_key(name):
    """Reduce a name to the words that decide what you put in the basket."""

    return frozenset(singular(word) for word in name.casefold().split())


def find_similar_names(names):
    """Group names that look like the same shopping item written differently."""

    keys = {key: name_key(entry["name"]) for key, entry in names.items()}
    groups = []
    for key, entry in sorted(names.items()):
        related = [
            names[other]["name"]
            for other, other_words in keys.items()
            if other != key and keys[key] <= other_words
        ]
        if related:
            groups.append((entry["name"], sorted(related)))
    return groups


def list_ingredients():
    names, unreadable = collect_all_ingredients()

    print(f"\n{len(names)} ingredients across all recipes:\n")
    for key in sorted(names.keys()):
        entry = names[key]
        count = len(entry["recipes"])
        print(f"  {entry['name']}  ({count} recipe{'s' if count != 1 else ''})")

    groups = find_similar_names(names)
    if groups:
        print("\nCheck whether these are the same item; if so, reuse one name:\n")
        for name, related in groups:
            print(f"  {name}  ->  {', '.join(related)}")

    if unreadable:
        print("\nCould not read:\n")
        for file_path, reason in unreadable:
            print(f"  {file_path}: {reason}")
    print()


def main():
    if "--list" in sys.argv:
        list_ingredients()
        return

    num_files = 0
    num_errors = 0

    for file_path in find_recipe_files():
        num_files += 1
        status, error = yaml_parser.verify(file_path)
        if status != 0:
            print(
                f"File {file_path} does not follow the specified format. "
                f"Error {status}:\n{error}\n"
            )
            num_errors += 1

    if num_errors > 0:
        print(f"Found {num_errors} errors in {num_files} files. Exiting.")
        exit(1)
    else:
        print(f"Found {num_files} files. All files follow the specified format.")


if __name__ == "__main__":
    main()
