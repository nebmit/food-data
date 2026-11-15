# YAML Recipe Style Guide

Every recipe is stored as `recipes/<Recipe Name>/recipe.yaml` and uses schema version 2. The cooking method is an ordered collection of named tables inspired by Cooking for Engineers: ingredient inputs enter on the left and prepared stages flow into later actions.

## Naming and writing style

1. Use Title Case for recipe directory names.
2. Use sentence capitalization for ingredient, equipment, and table names. An ingredient name must be the product someone buys; put preparation and substitutions in `hint`.
3. Reuse existing ingredient names so grocery lists aggregate correctly. Run `python scripts/format-check.py --list` before adding a new name; it also reports names that look like duplicates of an existing one. Reuse the existing kind of measurement too: an ingredient that is weighed in one recipe must not be counted in another, because `200 g` and `1 ×` of the same thing cannot be summed.
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
  course: "Dessert"
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
- "Baking"

items:
- name: Oven
- name: Stand mixer
  quantity: 2
  sub: "or hand mixer"
```

Ratings range from 1 to 5. Times are non-negative whole minutes, and portion quantities are positive whole numbers. An equipment `quantity` is optional and defaults to one.

`meta.course` is required and is the first level of the browse drilldown. It takes exactly one of `Breakfast`, `Starter`, `Main`, `Side`, `Dessert`, `Snack`, or `Drink`. `tags` hold what course and cuisine do not: dietary labels and character such as `Vegetarian`, `Gluten-free`, `Baking`, or `No-bake`. Do not repeat the course or the cuisine as a tag.

`active_time_minutes` is hands-on work; `passive_time_minutes` is everything that runs without you, such as baking, simmering, chilling, and cooling. When trays or batches are cooked one after another, count every round.

## Tables and stages

Use one table for each independently prepared component and a final table when components are assembled. A simple recipe may use a single table. Tables and stages are written in canonical presentation order; the last stage in a table is its result.

Each stage requires a recipe-global `snake_case` ID and a short imperative `action`. A stage is a **merge, not a micro-step**: everything that goes into the pot together belongs to one stage. Splitting "beat in the egg" and "add the vanilla" into two stages makes the table taller without making it clearer. Prepared inputs are listed before ingredient inputs, because that order is what a reader sees in the rendered table.

A stage that runs for a definite length of time also carries `duration_minutes`, a positive whole number of minutes. It is the machine-readable figure a cook's timer is set to; the `hint` keeps the prose and the sensory cue alongside it.

```yaml
tables:
- name: Dough
  stages:
  - id: preheat_oven
    setup: true
    action: Preheat oven
    hint: "200°C"

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
  - id: bake_cookies
    inputs:
    - stage: mix_cookie_dough
    action: Bake
    hint: "10 min; until edges are golden and centres remain soft"
    duration_minutes: 10
```

Every recipe ends in exactly one unused stage holding the finished dish, and it must be the last stage of the last table. Any other stage that nothing consumes is a wiring mistake.

### Setup stages

An action with no food inputs — preheating an oven, lining a tray — is marked `setup: true`. Setup stages take no `inputs`, are never referenced as food, and may not end a table, since a table's last stage is its result. Every other stage takes at least one input.

Document order is the order cook mode walks through, so put a setup stage where the cook has to start it, not where its result is needed: an oven is preheated at the top of the first table, before the dough is made. Do not reference a setup action merely to express timing.

A setup stage has no inputs to say what it acts on, so its `action` names the object: `Preheat oven`, `Line tray`, never a bare `Preheat`. The `hint` carries only the setting (`"200°C"`).

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

`part` is also allowed on a single reference when it names a reserved portion. Once a `part` says which piece flows where, drop the phrase that used to say it from the `hint`. A `part` names a piece of the food (`"whites"`, `"green parts"`); it is not a place to describe what happens in the pan.

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
- Separate the parts of a hint with semicolons, write times as `min` or `hours`, and put a space between a number and its unit (`2 cm`).
- A hint that states a time is always paired with `duration_minutes`, which repeats that time as a single whole number — the upper end of a range, so the timer never rings early. `"medium heat; 10–15 min; until thickened"` takes `duration_minutes: 15`. Leave it off only when the stage has no set time (`"until fragrant"`).
- When the time repeats — per side, per tray, per batch — say so in the hint and give `duration_minutes` the time of one round: `"about 4 min per side"` takes `duration_minutes: 4`. The cook restarts the timer for each round.
- Keep counts that depend on the yield out of hints, because scaling the recipe does not rewrite prose: `"one patty per bun"`, not `"4 patties"`.
- Keep equipment in top-level `items`; `sub` is allowed for an equipment substitute.
- Keep dietary variants, serving ideas, storage advice, and optional enhancements in top-level `note` rather than adding unused ingredient inputs.
- Use standard YAML quotes. Typographic quote characters must not wrap scalar values.

Run both checks before committing recipe changes:

```text
python -m unittest discover -s tests
python scripts/format-check.py
```
