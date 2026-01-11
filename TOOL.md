# Macro Tracker — LLM Tool Reference

> Use this tool to track food intake, water consumption, and nutritional goals.

## Setup

```python
from src.tracker import tracker
```

---

## Commands

### 1. Log Food

Log what the user ate. Nutrition is auto-looked up from USDA database.

```python
tracker.log_food(name, quantity=1, unit="serving", calories=None, protein_g=None, carbs_g=None, fat_g=None)
```

**Parameters:**
- `name` (str): Food name — be specific (e.g., "scrambled eggs" not just "eggs")
- `quantity` (float): How much — default 1
- `unit` (str): Unit type — "serving", "g", "oz", "cup", etc.
- `calories`, `protein_g`, `carbs_g`, `fat_g` (float): Optional manual overrides

**Returns:** Logged entry with nutrition data

**Examples:**
```python
# Auto-lookup nutrition
tracker.log_food("scrambled eggs", quantity=2)
tracker.log_food("chicken breast", quantity=150, unit="g")
tracker.log_food("dal", quantity=1, unit="bowl")

# Manual nutrition (when user provides values)
tracker.log_food("homemade smoothie", calories=350, protein_g=20, carbs_g=45, fat_g=8)
```

---

### 2. Search Food

Look up nutrition info without logging.

```python
tracker.search_food(query, limit=5)
```

**Parameters:**
- `query` (str): Food to search
- `limit` (int): Max results

**Returns:** List of foods with nutrition info

**Example:**
```python
results = tracker.search_food("greek yogurt")
# Returns: [{"name": "Yogurt, Greek...", "calories": 100, "protein_g": 17, ...}, ...]
```

---

### 3. Log Water

Track water intake.

```python
tracker.log_water(amount, unit="ml")
```

**Parameters:**
- `amount` (float): Quantity
- `unit` (str): One of "ml", "l", "liters", "glass", "glasses", "oz", "cup"

**Conversions:**
- 1 glass = 237ml (8 fl oz)
- 1 liter = 1000ml
- 1 oz = 29.57ml
- 1 cup = 236.6ml

**Examples:**
```python
tracker.log_water(500, "ml")
tracker.log_water(2, "glasses")
tracker.log_water(1.5, "liters")
```

---

### 4. Get Daily Summary

Get complete daily stats with goal progress.

```python
tracker.get_daily_summary(day=None)  # None = today
```

**Returns:**
```python
{
    "date": "2026-01-10",
    "food": {
        "calories": 1250,
        "protein_g": 85,
        "carbs_g": 120,
        "fat_g": 45,
        "entries": 4
    },
    "water": {
        "total_ml": 2000,
        "total_liters": 2.0,
        "glasses": 8.4
    },
    "goals": {
        "calories": 2000,
        "protein_g": 150,
        "water_ml": 3000
    },
    "progress": {
        "calories_pct": 62.5,
        "protein_pct": 56.7,
        "water_pct": 66.7
    }
}
```

---

### 5. Get Water Status

Quick water check.

```python
tracker.get_water_status(day=None)
```

**Returns:**
```python
{
    "total_ml": 2000,
    "total_liters": 2.0,
    "glasses": 8.4,
    "goal_ml": 3000,
    "remaining_ml": 1000,
    "progress_pct": 66.7
}
```

---

### 6. Get Food Log

List all food entries for a day.

```python
tracker.get_food_log(day=None)
```

**Returns:** List of food entries with timestamps and nutrition.

---

### 7. Set Goals

Update daily targets.

```python
tracker.set_goal(category, value)
```

**Categories:**
- `"calories"` — daily calorie target
- `"protein_g"` — protein in grams
- `"carbs_g"` — carbs in grams
- `"fat_g"` — fat in grams
- `"water_ml"` — water in milliliters

**Example:**
```python
tracker.set_goal("protein_g", 180)
tracker.set_goal("water_ml", 4000)
```

---

### 8. Get Goals

Retrieve current goals.

```python
tracker.get_goals()
```

**Returns:**
```python
{"calories": 2000, "protein_g": 150, "water_ml": 3000}
```

---

## Natural Language Mapping

| User Input | Interpretation |
|------------|----------------|
| "2 eggs" | `log_food("eggs", quantity=2)` |
| "a bowl of dal" | `log_food("dal", quantity=1, unit="bowl")` |
| "200g chicken breast" | `log_food("chicken breast", quantity=200, unit="g")` |
| "protein shake with 30g protein" | `log_food("protein shake", protein_g=30)` |
| "3 glasses of water" | `log_water(3, "glasses")` |
| "half a liter of water" | `log_water(0.5, "liters")` |
| "how much protein today" | `get_daily_summary()["food"]["protein_g"]` |
| "water status" | `get_water_status()` |
| "what did I eat" | `get_food_log()` |
| "set protein goal to 200" | `set_goal("protein_g", 200)` |

---

## Response Guidelines

After logging food:
> "Logged: [food] — [calories] cal, [protein]g protein. Today's total: [total_calories] cal, [total_protein]g protein."

After logging water:
> "Logged [amount]. Today: [total]L / [goal]L ([percent]%)"

For daily summary:
> Provide a brief overview of calories, protein, and water progress.

---

## Error Handling

### Nutrition Not Found

When `log_food()` can't find nutrition data, it returns:
```python
{
    "logged": False,
    "error": "nutrition_not_found",
    "message": "Could not find nutrition info for 'masala chai'. Please provide calories/protein/carbs/fat manually, or search using another source.",
    "name": "masala chai",
    "quantity": 0.5,
    "unit": "cup"
}
```

**Recommended flow for LLM agents:**

1. Call `tracker.log_food("food name")` 
2. If `logged: False` and `error: "nutrition_not_found"`:
   - Use your own search capability (e.g., web search, Serper, Google) to find nutrition info
   - Search for: `"{food name} nutrition calories protein per serving"`
   - Extract approximate values from search results
   - Re-call with explicit values: `tracker.log_food("food name", calories=X, protein_g=Y, carbs_g=Z, fat_g=W)`
3. Confirm to user what was logged

**Alternative flow (search first):**

1. Call `tracker.search_food("food name")` first
2. If results are empty or poor quality, use external search
3. Then call `tracker.log_food()` with explicit values

This keeps the tracker focused on storage/USDA lookup, while the LLM orchestrates fallback searches.

### Other Errors

- **Invalid quantity:** Default to 1 serving
- **Past dates:** Support "log [food] for yesterday" by passing date parameter

---

## Data Storage

- Food logs: `data/food_YYYY-MM-DD.json`
- Water logs: `data/water_YYYY-MM-DD.json`  
- Goals: `data/goals.json`

All data is local. No cloud sync.
