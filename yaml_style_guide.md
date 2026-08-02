# YAML Recipe Style Guide

Every recipe is stored as `recipes/<Recipe Name>/recipe.yaml` and uses schema version 2. The cooking method is an ordered collection of named tables inspired by Cooking for Engineers: ingredient inputs enter on the left and prepared stages flow into later actions.

## Naming and writing style

1. Use Title Case for recipe directory names.
2. Use sentence capitalization for ingredient, equipment, and table names. An ingredient name must be the product someone buys; put preparation and substitutions in `hint`.
3. Reuse existing ingredient names so grocery lists aggregate correctly. Run `python scripts/format-check.py --list` before adding a new name; it also reports names that look like duplicates of an existing one.
4. Use metric measurements where practical and the singular measurement values listed below.
5. Start actions with a capitalised imperative verb and keep stages chronological.
6. Put timing, heat, Celsius temperature, sensory cues, dimensions, and cautions in the action `hint`. Hints start lowercase because they continue the action.
7. Name stage IDs after the action, not its result: `preheat_oven` and `cool_cookies`, not `oven_ready` or `cooled_cookies`. IDs only need to be unique inside one recipe, so they do not need a recipe-name prefix.

Use `ingredient: Butter` with `hint: "softened; or margarine"`, not separate ingredient names such as `Softened butter`. Do not use legacy `[ingredient]` or `{proportion:name}` references.

## Top-level structure

Every recipe requires `schema_version`, `meta`, `portion`, `items`, and a non-empty `tables` list. `tags` and `note` are optional.

```yaml
schema_version: 2

meta:
  description: "Classic cookies with crisp edges and chewy centres."
  source: "Original"
  cuisine: "American"

portion:
  quantity: 12
  descriptor: "cookies"
  active_time_minutes: 20
  passive_time_minutes: 10
  complexity_rating: 2
  mayhem_rating: 2

tags:
- "Vegetarian"
- "Dessert"

items:
- name: Oven
- name: Stand mixer
  quantity: 2
  sub: "or hand mixer"
```

Ratings range from 1 to 5. Times are non-negative whole minutes, and portion quantities are positive whole numbers. An equipment `quantity` is optional and defaults to one.

## Tables and stages

Use one table for each independently prepared component and a final table when components are assembled. A simple recipe may use a single table. Tables and stages are written in canonical presentation order; the last stage in a table is its result.

Each stage requires a recipe-global `snake_case` ID and a short imperative `action`. A stage is a **merge, not a micro-step**: everything that goes into the pot together belongs to one stage. Splitting "beat in the egg" and "add the vanilla" into two stages makes the table taller without making it clearer. Prepared inputs are listed before ingredient inputs, because that order is what a reader sees in the rendered table.

```yaml
tables:
- name: Dough
  stages:
  - id: whisk_dry_mixture
    inputs:
    - ingredient: Flour
      quantity: 270
      measurement: grams
    - ingredient: Baking powder
      quantity: 1
      measurement: teaspoon
    action: Whisk together

  - id: mix_cookie_dough
    inputs:
    - stage: whisk_dry_mixture
    - ingredient: Butter
      quantity: 170
      measurement: grams
      hint: "softened"
    - ingredient: Sugar
      quantity: 100
      measurement: grams
    action: Mix
    hint: "until just combined"

- name: Bake
  stages:
  - id: preheat_oven
    setup: true
    action: Preheat oven
    hint: "200°C"

  - id: bake_cookies
    inputs:
    - stage: mix_cookie_dough
    action: Bake
    hint: "10 min; until edges are golden and centres remain soft"
```

Every recipe ends in exactly one unused stage holding the finished dish, and it must be the last stage of the last table. Any other stage that nothing consumes is a wiring mistake.

### Setup stages

An action with no food inputs — preheating an oven, lining a tray — is marked `setup: true`. Setup stages take no `inputs`, are never referenced as food, and may not end a table, since a table's last stage is its result. Document order already supplies chronology, so do not reference a setup action merely to express timing.

### Stage references

Stage references describe prepared food flowing into a later action. They must point backward. A stage may reference any earlier stage in its own table; across tables it may reference only the final stage of an earlier table.

A stage that feeds more than one later stage — separated eggs, a reserved garnish, a protein removed from the pan — must name a `part` on **every** reference to it, so each branch says what it carries instead of leaving it to prose:

```yaml
- id: separate_eggs
  inputs:
  - ingredient: Egg
    quantity: 8
    measurement: unit
  action: Separate

- id: whip_egg_whites
  inputs:
  - stage: separate_eggs
    part: "whites"
  action: Beat
  hint: "to stiff peaks"
```

`part` is also allowed on a single reference when it names a reserved portion. Once a `part` says which piece flows where, drop the phrase that used to say it from the `hint`.

Do not store row numbers, column numbers, or cell spans.

## Ingredient inputs and amounts

Put an ingredient at the stage where it is consumed. If it is measured twice, repeat it with the exact amount at each use; consumers can aggregate matching names and measurements.

```yaml
- ingredient: Olive oil
  quantity: 15
  measurement: ml
  hint: "for frying"
```

`quantity` and `measurement` must either both be present or both be absent. Quantities are positive numbers. When an amount is genuinely qualitative, omit both fields and explain it with a non-empty hint:

```yaml
- ingredient: Salt
  hint: "to taste"
```

There is no pantry classification in schema v2. Water, salt, oil, and other staples are ordinary ingredient inputs.

### Allowed measurements

| Value | Use for |
|---|---|
| `grams` | Dry or solid ingredients by weight |
| `ml` | Liquids by volume |
| `unit` | Whole items |
| `teaspoon` | Small measured volumes |
| `tablespoon` | Medium measured volumes |
| `clove` | Garlic cloves |
| `pinch` | Very small dry amounts |
| `can` | Tinned or canned goods |
| `bunch` | Fresh herbs sold in bunches |
| `slice` | Pre-sliced ingredients |
| `packet` | Packaged sachets or packets |
| `leaf` | Individually counted leaves |

## Hints, equipment, and notes

- Ingredient hints contain preparation, substitution, or qualitative amount information: `"coarsely chopped; or chocolate chips"`.
- Action hints contain compact execution details: `"medium heat; 10–15 min; until thickened"`.
- Keep equipment in top-level `items`; `sub` is allowed for an equipment substitute.
- Keep dietary variants, serving ideas, storage advice, and optional enhancements in top-level `note` rather than adding unused ingredient inputs.
- Use standard YAML quotes. Typographic quote characters must not wrap scalar values.

Run both checks before committing recipe changes:

```text
python -m unittest discover -s tests
python scripts/format-check.py
```
