# EU Allergen Checker for Menus & Recipes

**Turn any menu, dish list or recipe URL into a draft EU allergen declaration in seconds.** This Actor detects the **14 allergens of Regulation (EU) No 1169/2011, Annex II** in ingredient lists written in **English, Italian, French, Dutch, German and Spanish**, flags hidden allergens in compound ingredients (pesto, Worcestershire sauce, stock, mayonnaise, soy sauce…) and returns one clean, structured result per dish – ready for your POS, delivery app, menu builder or kitchen documentation.

Built by **Domenico Vescera**, professional Italian chef based in Brussels (*Chef's Notebook*), who has written allergen matrices for real restaurant menus and knows where allergens hide.

## What it does

- ✅ Detects all 14 EU allergens: cereals containing gluten, crustaceans, eggs, fish, peanuts, soybeans, milk, tree nuts, celery, mustard, sesame, sulphur dioxide/sulphites, lupin, molluscs.
- 🌍 Multilingual keyword dictionaries (EN, IT, FR, NL, DE, ES) with accent-stripped, word-boundary matching, plurals and German/Dutch compound words (*Weizenmehl*, *Haselnüsse*, *garnalen*, *Knollensellerie*).
- 🧠 Chef-grade rules to avoid classic false positives: *coconut*, *pine nuts* and *chestnuts* are not Annex II nuts (flagged as **check**), *nutmeg* and *butternut squash* are not nuts, *peanut* never triggers tree nuts, *buckwheat* is not gluten, *eggplant* is not egg, *cream of tartar* and *coconut milk* are not milk, *beurre noisette* and *noce di burro* are butter, *noix de Saint-Jacques* are scallops.
- 🔎 Hidden-allergen hints for compound ingredients: pesto → milk + nuts check; Worcestershire → fish; stock/broth/bouillon → celery check; mayonnaise/aioli → egg (+ mustard check); soy sauce → soy + gluten; wine/vinegar/dried fruit → sulphites check; pasta → gluten (+ egg check); breadcrumbs, béchamel, custard, savoiardi, puff pastry and many more.
- 🏷️ Two confidence levels: **contains** (the ingredient text clearly contains the allergen) and **check** (likely or possible – verify the recipe or supplier label).
- 🧾 Ready-made label line, e.g. `Contains: Gluten, Eggs, Milk`.
- 🌐 Reads recipe pages: parses schema.org `Recipe` JSON-LD (including `@graph`) and uses `name` + `recipeIngredient`.
- 🔒 100% rule-based Python – no AI/LLM calls, no API keys, deterministic and fast.

## Who it's for

- Restaurant-tech, POS and menu-management software that needs allergen tagging.
- Food-delivery and ordering apps enriching dish data.
- Recipe sites, meal-kit and dark-kitchen operators.
- Restaurants, caterers and food consultants drafting allergen matrices (EU, UK, Belgium, Italy, France, Germany, Netherlands, Spain…).

## Input

You can combine all three sources in one run.

| Field | Type | Description |
|---|---|---|
| `dishes` | array | Objects `{"name": "...", "ingredients": "a, b, c"}` – `ingredients` may be a string or an array. |
| `menuText` | string | One dish per line: `Dish name: ingredient, ingredient`, `Dish name - ingredients` or `Dish name (ingredients)`. Prices at the end of a line are ignored, lines starting with `#` are skipped. |
| `recipeUrls` | array | Recipe page URLs. Pages without a schema.org Recipe produce an error item (not charged). |
| `languages` | array | Optional. Restrict dictionaries to e.g. `["it", "fr"]` (English is always included). Default: all six languages. |

### Input example

```json
{
  "dishes": [
    { "name": "Spaghetti carbonara", "ingredients": "spaghetti, guanciale, egg yolks, Pecorino Romano, black pepper" },
    { "name": "Pesto alla genovese", "ingredients": ["trofie pasta", "basil", "pine nuts", "Parmigiano Reggiano", "Pecorino", "garlic", "extra virgin olive oil"] },
    { "name": "Moules-frites", "ingredients": "mussels, white wine, shallots, celery, butter, parsley, fries, mayonnaise" },
    { "name": "Tiramisu", "ingredients": "savoiardi, mascarpone, eggs, sugar, espresso, Marsala, cocoa powder" }
  ],
  "menuText": "Salade niçoise - thon, oeufs, anchois, olives, haricots verts, vinaigrette à la moutarde\nGarnalenkroket: garnalen, boter, bloem, melk, paneermeel",
  "recipeUrls": [{ "url": "https://www.example.com/my-recipe" }]
}
```

## Output

One dataset item per dish. The dataset has an **Overview** table view (dish, allergen line, items to verify) and a **Details** view.

```json
{
  "dishName": "Moules-frites",
  "source": "dishes",
  "ingredientsAnalyzed": [
    "mussels",
    "white wine",
    "shallots",
    "celery",
    "butter",
    "parsley",
    "fries",
    "mayonnaise"
  ],
  "allergens": [
    {
      "number": 3,
      "id": "eggs",
      "name": "Eggs",
      "matchedTerms": [
        "mayonnaise"
      ],
      "confidence": "contains"
    },
    {
      "number": 7,
      "id": "milk",
      "name": "Milk",
      "matchedTerms": [
        "butter"
      ],
      "confidence": "contains"
    },
    {
      "number": 9,
      "id": "celery",
      "name": "Celery",
      "matchedTerms": [
        "celery"
      ],
      "confidence": "contains"
    },
    {
      "number": 10,
      "id": "mustard",
      "name": "Mustard",
      "matchedTerms": [
        "mayonnaise"
      ],
      "confidence": "check"
    },
    {
      "number": 12,
      "id": "sulphites",
      "name": "Sulphur dioxide and sulphites",
      "matchedTerms": [
        "white wine"
      ],
      "confidence": "check"
    },
    {
      "number": 14,
      "id": "molluscs",
      "name": "Molluscs",
      "matchedTerms": [
        "mussels"
      ],
      "confidence": "contains"
    }
  ],
  "allergenCount": 4,
  "containsAllergens": [
    "Eggs",
    "Milk",
    "Celery",
    "Molluscs"
  ],
  "checkAllergens": [
    "Mustard",
    "Sulphites"
  ],
  "euAllergenLine": "Contains: Eggs, Milk, Celery, Molluscs",
  "checks": [
    "Wine and fortified wines almost always contain sulphites (>10 mg/l).",
    "Mayonnaise/aioli: contains egg; many recipes and commercial versions also contain mustard.",
    "Mustard (check): matched 'mayonnaise'. Mayonnaise, dressings, vinaigrettes and spice blends often contain mustard.",
    "Sulphites (check): matched 'white wine'. Wine, vinegar, dried fruit, pickles and some cured meats commonly contain sulphites (>10 mg/kg)."
  ],
  "disclaimer": "Automated draft based only on the ingredient text provided; not a legal allergen declaration. Verify against recipes and supplier specifications."
}
```

Fields: `dishName`, `source` (`dishes`, `menuText` or the recipe URL), `ingredientsAnalyzed`, `allergens[]` (`number` = Annex II order 1–14, `id`, `name`, `matchedTerms`, `confidence`), `allergenCount` (number of **contains** allergens), `containsAllergens`, `checkAllergens`, `euAllergenLine`, `checks` (human-readable notes) and `disclaimer`. Failed URLs return an item with an `error` field.

## Pricing

Pay per event: **$2.00 per 1,000 dishes analysed** (event `dish-analyzed`, $0.002 per dish). Error items for URLs without a recipe are free. You only pay for what you analyse, and the Actor stops cleanly when your run's maximum charge is reached.

## Limitations

- The analysis is based **only on the ingredient text you provide**. It cannot know what is inside a branded product, a house-made sauce or a supplier's stock cube unless you list it.
- Cross-contamination ("may contain traces of…") is not assessed.
- Keyword dictionaries cover EN, IT, FR, NL, DE and ES; other languages, slang or heavy abbreviations may be missed.
- When only a dish name is given (no ingredients), results are downgraded to **check**.
- Recipe URLs must expose schema.org `Recipe` JSON-LD; pages that block bots or render recipes only with JavaScript may fail.

## Legal disclaimer

Automated draft based only on the ingredient text provided; **not a legal allergen declaration**. Food business operators remain responsible for the allergen information they provide under Regulation (EU) No 1169/2011 and national law. Always verify against your recipes and supplier specifications before publishing allergen information to customers.

## Author

**Domenico Vescera** – professional chef in Brussels, author of the *Chef's Notebook* series. Feedback, missing ingredients or new language requests are welcome via the Actor's Issues tab.

## Local development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
apify run   # or: python -m src  (input in storage/key_value_stores/default/INPUT.json)
```
