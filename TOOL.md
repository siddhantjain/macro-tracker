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

**⚠️ IMPORTANT: Unit Conversion is STRICT**

Units like "cup", "oz", "slice" are converted to grams using USDA portion data.
If no matching portion is found, logging will **FAIL** with available portions listed.

For reliable logging:
1. Use `unit="g"` with quantity in grams (most reliable)
2. Provide manual nutrition values (bypasses lookup)
3. Use units that match USDA portions (cup, oz, tbsp, slice, etc.)

```python
tracker.log_food(
    name: str,                      # Required: food name
    quantity: float = 1,            # Amount consumed
    unit: str = "g",                # Unit: g, cup, oz, tbsp, slice, etc.
    calories: float = None,         # Manual override (skips USDA lookup)
    protein_g: float = None,
    carbs_g: float = None,
    fat_g: float = None,
    dedupe_window_minutes: int = 5, # Duplicate detection window (0 = disabled)
    dry_run: bool = False,          # Preview without saving
) -> dict
```

**Returns:**
```python
# Success
{
    "logged": True, 
    "timestamp": "...", 
    "name": "rice", 
    "calories": 373,
    "gram_weight": 348,  # Actual grams calculated
    "conversion": "2 cup = 348g (based on 1 cup, cooked = 174g)"
}

# Portion not found (FAIL - won't log!)
{
    "logged": False, 
    "error": "PORTION_NOT_FOUND",
    "message": "Could not convert 'bucket' for 'rice'. No matching portion found.",
    "available_portions": [
        {"description": "1 cup, cooked", "gram_weight": 174},
        {"description": "1 oz", "gram_weight": 28.35}
    ],
    "suggestion": "Please use one of the available portions, or specify in grams."
}

# Food not found in USDA
{
    "logged": False, 
    "error": "FOOD_NOT_FOUND", 
    "message": "Could not find 'xyz123' in USDA database."
}

# Duplicate detected
{
    "logged": False, 
    "reason": "duplicate_detected", 
    "existing_entry": {...},
    "message": "'rice' was already logged 2.3 minutes ago."
}
```

**Examples:**
```python
# BEST: Use grams (most reliable)
tracker.log_food("chicken breast", quantity=150, unit="g")
# → 165 cal, 31g protein (150g of chicken)

# GOOD: Common units that USDA knows
tracker.log_food("rice white cooked", quantity=2, unit="cup")
# → 373 cal (2 cups × 174g = 348g)

tracker.log_food("milk whole", quantity=1, unit="cup")
# → 149 cal (1 cup = 244g)

tracker.log_food("eggs scrambled", quantity=2, unit="large")
# → If USDA has "large" portion, uses it

# GOOD: Manual nutrition (bypasses all lookups)
tracker.log_food("homemade smoothie", calories=350, protein_g=20, carbs_g=45, fat_g=8)

# Preview before committing
tracker.log_food("rice", quantity=2, unit="cup", dry_run=True)
```

---

### 2. How Unit Conversion Works

When you specify a unit other than "g", the tracker:

1. Searches USDA for the food (prioritizes Survey/FNDDS for better portion data)
2. Looks for a matching portion in `foodMeasures`:
   - "1 cup, cooked" → 174g
   - "1 oz" → 28.35g
   - "1 slice" → 25g
3. Calculates total grams: `quantity × portion_gram_weight`
4. Scales nutrition from per-100g to actual grams

**If no matching portion is found → Returns error with available portions!**

```python
# This will FAIL if USDA doesn't have "bucket" portion for rice
result = tracker.log_food("rice", quantity=1, unit="bucket")
# Returns: {
#     "logged": False,
#     "error": "PORTION_NOT_FOUND",
#     "available_portions": ["1 cup, cooked = 174g", "1 oz = 28.35g"],
#     "suggestion": "Please use one of the available portions, or specify in grams."
# }
```

---

### 3. Log Meal (Batch)

Log multiple food items as a meal. Atomic operation with duplicate detection.

```python
tracker.log_meal(
    items: list[dict],              # List of food items
    meal_name: str = None,          # Optional name for the meal
    dedupe_window_minutes: int = 5, # Per-item duplicate detection
    dry_run: bool = False,          # Preview without saving
) -> dict
```

**Item format (prefer grams for reliability):**
```python
{"name": "rice", "quantity": 200, "unit": "g"}  # 200g of rice
{"name": "dal", "calories": 150, "protein_g": 8}  # Manual values
```

---

### 4. Search Food

Look up nutrition info without logging. Includes available portions!

```python
tracker.search_food(query: str, limit: int = 5) -> list[dict]
```

**Example:**
```python
results = tracker.search_food("greek yogurt")
# Returns: [{
#     "name": "Yogurt, Greek, plain, nonfat",
#     "calories": 59,  # per 100g
#     "protein_g": 10,
#     "portions": [
#         {"description": "1 container (6 oz)", "gram_weight": 170},
#         {"description": "1 cup", "gram_weight": 245}
#     ]
# }, ...]
```

---

### 5. Log Water

```python
tracker.log_water(amount: float, unit: str = "ml") -> dict
```

**Units:** ml, l/liters, glass/glasses, oz, cup

**Example:**
```python
tracker.log_water(2, "glasses")  # 2 glasses ≈ 474ml
tracker.log_water(500, "ml")
```

---

### 6. Get Status

```python
tracker.get_daily_summary(day=None, timezone=None) -> dict
tracker.get_water_status(day=None, timezone=None) -> dict
tracker.get_food_log(day=None, timezone=None) -> list[dict]
```

---

## Safe Logging Patterns for LLM Agents

### Pattern 1: Prefer Grams for Reliability

```python
# ✅ BEST: Always works
tracker.log_food("chicken breast", quantity=150, unit="g")

# ⚠️ RISKY: May fail if USDA doesn't have portion
tracker.log_food("chicken", quantity=1, unit="breast")
```

### Pattern 2: Handle Portion Errors Gracefully

```python
result = tracker.log_food("rice", quantity=2, unit="cup")

if not result.get("logged"):
    if result.get("error") == "PORTION_NOT_FOUND":
        # Show user available portions
        portions = result.get("available_portions", [])
        print(f"I don't know how to convert 'cup' for rice.")
        print(f"Available portions: {portions}")
        print(f"Can you give me the amount in grams?")
    elif result.get("error") == "FOOD_NOT_FOUND":
        print("I couldn't find that food. Can you provide nutrition values?")
```

### Pattern 3: Dry Run Before Committing

```python
# Preview first
result = tracker.log_food("mystery food", quantity=1, unit="cup", dry_run=True)
if result.get("dry_run"):
    print(f"Would log: {result['would_log']['calories']} cal")
    print(f"Conversion: {result.get('conversion')}")
    # Then commit
    tracker.log_food("mystery food", quantity=1, unit="cup")
```

### Pattern 4: Fallback to Manual Entry

```python
# If lookup fails, ask user for calories
result = tracker.log_food("grandma's special dish", quantity=1, unit="serving")
if not result.get("logged"):
    # Ask user: "I couldn't find nutrition for that. How many calories?"
    # Then log manually:
    tracker.log_food("grandma's special dish", calories=500, protein_g=20)
```

---

## Duplicate Detection

By default, `log_food()` prevents duplicates within 5 minutes:

```python
tracker.log_food("rice", quantity=200, unit="g")
# ✓ Logged

tracker.log_food("rice", quantity=200, unit="g")  # Within 5 minutes
# ✗ Returns: {"logged": False, "reason": "duplicate_detected", ...}
```

**To disable:** Set `dedupe_window_minutes=0`

---

## Timezone Handling

User timezone: `America/Los_Angeles` (California)

Entries stored in UTC, queries adapt to local timezone automatically.

---

## Data Storage

- Food logs: `data/food_YYYY-MM-DD.json` (UTC dates)
- Water logs: `data/water_YYYY-MM-DD.json` (UTC dates)  
- Goals: `data/goals.json`

---

## Quick Reference

| Task | Command |
|------|---------|
| Log food (grams) | `tracker.log_food("chicken", quantity=150, unit="g")` |
| Log food (cups) | `tracker.log_food("rice cooked", quantity=2, unit="cup")` |
| Log manual | `tracker.log_food("food", calories=500, protein_g=30)` |
| Preview | `tracker.log_food("food", quantity=1, unit="cup", dry_run=True)` |
| Search | `tracker.search_food("greek yogurt")` |
| Log water | `tracker.log_water(2, "glasses")` |
| Get summary | `tracker.get_daily_summary()` |
