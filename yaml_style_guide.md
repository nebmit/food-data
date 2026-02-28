# YAML Recipe Style Guide

This document outlines the formatting and structure requirements for recipe files written in YAML format.

Each recipe must be saved as a `recipe.yaml` file within its respective directory under `recipes/`.

---

## Writing Style Guidelines

### Naming and Capitalization

1. **Recipe directory names**: Use Title Case (capitalize each main word)
2. **Ingredient names**: Capitalize the first letter only. Keep names short and clean — put preparation state in the `prep` field, not the name.
3. **Measurements**: Use lowercase, always singular form (`grams`, `ml`, `teaspoon`)
4. **Tags**: Capitalize the first letter only

### Instructions Style

1. **Use imperative voice**: Start with action verbs ("Mix" instead of "You should mix")
2. **Be specific with temperatures**: Use Celsius
3. **Use precise timing**: "Bake for 20–25 minutes" rather than "Bake until done"
4. **Include sensory cues alongside timing**: "Bake for 20 minutes until golden brown"
5. **Order chronologically**: Write steps in the exact order they should be performed
6. **One main action per instruction**: Split complex steps into multiple instructions
7. **Be concise**: Avoid unnecessary words or explanations
8. **Write naturally**: Instructions should read like clear cooking directions, not code

### Notes

1. **Include substitutions**: Note possible ingredient alternatives
2. **Highlight dietary information**: Mention if a recipe is vegetarian, vegan, gluten-free, etc.
3. **Add helpful tips**: Include practical advice for best results

### Measurements and Quantities

1. **Use metric system** as primary measurement (`grams`, `ml`)
2. **Keep ingredient names clean**: Put form/preparation in the `prep` field — use `Butter` with `prep: "room temperature"`, not `Butter, room temperature` as the name
3. **One ingredient per entry**: Never combine two ingredients in one entry (e.g. don't list "Mint & dill" — list them separately)

---

## Allowed Measurements

Use only the following measurement values. Always use singular form:

| Value         | Use for                                      |
|---------------|----------------------------------------------|
| `grams`       | Dry/solid ingredients by weight              |
| `ml`          | Liquids by volume                            |
| `unit`        | Whole items (eggs, onions, lemons)           |
| `teaspoon`    | Small volumes (vanilla extract, spices)      |
| `tablespoon`  | Medium volumes (oil, sauces in small amounts)|
| `clove`       | Garlic                                       |
| `pinch`       | Very small dry amounts (salt, spices)        |
| `can`         | Tinned/canned goods                          |
| `bunch`       | Fresh herbs                                  |
| `slice`       | Pre-sliced items (cheese, bread)             |

---

## Required Sections

### 1. Meta (Recipe Metadata)

Every recipe must include a short description, source, and cuisine type.

```yaml
meta:
  description: "Crisp golden fries tossed with garlic and parmesan cheese."
  source: "Original"               # or book title, website, etc.
  cuisine: "American"
```

### 2. Portion Information

```yaml
portion:
  quantity: 4                  # Integer — number of servings/pieces
  descriptor: "servings"       # String — what the quantity describes
  active_time_minutes: 25      # Integer — hands-on time in minutes
  passive_time_minutes: 0      # Integer — waiting/baking time in minutes
  complexity_rating: 2         # Integer 1–5 (1 = very simple, 5 = very complex)
  mayhem_rating: 1             # Integer 1–5 (1 = very clean, 5 = very messy)
```

### 3. Ingredients

```yaml
ingredients:
  - name: Butter               # Capitalize first letter; keep it short
    quantity: 170
    measurement: grams
    prep: "room temperature"   # Optional — preparation state
    sub: "or margarine"        # Optional — substitution suggestion
  - name: Egg
    quantity: 2
    measurement: unit
```

### 4. Items (Equipment)

List kitchen equipment that is **non-obvious or hard to substitute**. Skip universally available items like plates or cutlery. Include common items (bowls, trays) only if they're specifically essential.

```yaml
items:
  - name: Oven
    quantity: 1
  - name: Stand mixer
    quantity: 1
```

### 5. Instructions

Write instructions as natural, readable sentences. Reference ingredients using `[Ingredient Name]` in square brackets. Write quantities directly in the instruction text.

```yaml
instructions:
  - "Preheat the oven to 200°C. Line a baking tray with parchment paper."
  - "Cream 170g [butter] with 200g [brown sugar] and 100g [sugar] until fluffy."
  - "Beat in the [egg] one at a time, then add [vanilla extract]."
  - "Fold in 270g [flour] and [baking powder]. Stir in the [chocolate chips]."
  - "Scoop dough into balls and bake for 10 minutes until golden brown."
```

#### Referencing Rules

- **Bracket syntax**: `[Ingredient Name]` — case-insensitive match to `ingredients` or `pantry` names
- **Write quantities naturally**: Include the actual amount in the instruction text (e.g. "Add 200ml [milk]")
- **No proportions or fractions**: Don't calculate fractions of ingredient totals — just write the amount
- **Splitting ingredients across steps**: Write the amount for each step directly (e.g. "Add 500ml [water] to the pot" then later "Add the remaining 200ml [water]")
- **Pantry staples**: Reference the same way: "Season with [salt] and [pepper] to taste"

---

## Optional Sections

### 1. Tags

```yaml
tags:
  - "Vegetarian"
  - "Dessert"
  - "Baking"
```

### 2. Pantry Staples

Items most people already have at home and don't need to buy specifically for this recipe. Common examples: water, salt, pepper, olive oil, vegetable oil.

```yaml
pantry:
  - name: Water
    quantity: 500
    measurement: ml
  - name: Salt
    quantity: 1
    measurement: pinch
  - name: Olive oil
    quantity: 30
    measurement: ml
```

### 3. Notes

```yaml
note:
  - "For a vegan version, substitute butter with plant-based butter."
  - "Reduce sugar by 25% for a less sweet result."
```

---

## Data Types

| Type      | Used for                                    |
|-----------|---------------------------------------------|
| Integer   | Portion quantity, time, ratings, item counts |
| Float     | Ingredient quantities (e.g. 0.75 teaspoon)  |
| String    | Names, descriptions, instructions, tags      |
| List      | Ingredients, instructions, tags, notes       |

---

## Rating Systems

- **Complexity Rating**: 1 (very simple) to 5 (very complex)
- **Mayhem Rating**: 1 (very clean) to 5 (very messy)

---

## Complete Example

```yaml
meta:
  description: "Classic chocolate chip cookies with crispy edges and chewy centres."
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
  - "Baking"

ingredients:
  - name: Flour
    quantity: 270
    measurement: grams
  - name: Butter
    quantity: 170
    measurement: grams
    prep: "softened"
    sub: "or margarine"
  - name: Brown sugar
    quantity: 200
    measurement: grams
  - name: Sugar
    quantity: 100
    measurement: grams
  - name: Chocolate chips
    quantity: 350
    measurement: grams
  - name: Egg
    quantity: 1
    measurement: unit
  - name: Baking powder
    quantity: 1
    measurement: teaspoon
  - name: Vanilla extract
    quantity: 1
    measurement: teaspoon

pantry:
  - name: Salt
    quantity: 1
    measurement: pinch

items:
  - name: Oven
    quantity: 1
  - name: Mixing bowl
    quantity: 1
  - name: Baking tray
    quantity: 1

instructions:
  - "Preheat the oven to 200°C. Line a baking tray with parchment paper."
  - "Cream 170g [butter] with 200g [brown sugar] and 100g [sugar] until light and fluffy."
  - "Beat in the [egg], then add 1 tsp [vanilla extract]."
  - "Mix in 270g [flour], 1 tsp [baking powder], and a pinch of [salt] until just combined."
  - "Fold in 350g [chocolate chips]."
  - "Roll the dough into small balls and place on the baking tray, spaced apart."
  - "Bake for 10 minutes until the edges are golden but the centres are still soft."
  - "Let the cookies cool on the tray for 5 minutes before serving."

note:
  - "Substitute chocolate chips with chopped nuts or dried fruit."
  - "Reduce sugar and butter quantities for a lighter version."
```
