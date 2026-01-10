---
layout: default
title: API Reference
---

# API Reference

Complete reference for the Macro Tracker Python API.

## MacroTracker Class

The main interface for all tracking operations.

```python
from src.tracker import tracker  # Default instance
# or
from src.tracker import MacroTracker
tracker = MacroTracker()
```

---

## Food Tracking

### `search_food(query, limit=5)`

Search the nutrition database for foods.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `query` | str | required | Food name to search |
| `limit` | int | 5 | Maximum results |

**Returns:** `list[dict]` — List of food items with nutrition info

**Example:**
```python
results = tracker.search_food("greek yogurt", limit=3)
# [
#   {"name": "Yogurt, Greek, plain", "calories": 100, "protein_g": 17.3, ...},
#   {"name": "Yogurt, Greek, strawberry", "calories": 120, "protein_g": 12.1, ...},
#   ...
# ]
```

---

### `log_food(name, quantity=1, unit="serving", calories=None, protein_g=None, carbs_g=None, fat_g=None)`

Log a food entry. Auto-looks up nutrition if not provided.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `name` | str | required | Food name |
| `quantity` | float | 1 | Amount consumed |
| `unit` | str | "serving" | Unit of measurement |
| `calories` | float | None | Manual calorie override |
| `protein_g` | float | None | Manual protein override |
| `carbs_g` | float | None | Manual carbs override |
| `fat_g` | float | None | Manual fat override |

**Returns:** `dict` — The logged entry

**Example:**
```python
# Auto-lookup
entry = tracker.log_food("scrambled eggs", quantity=2)

# Manual values
entry = tracker.log_food("protein shake", calories=200, protein_g=30, carbs_g=5, fat_g=3)
```

---

### `get_food_log(day=None)`

Get all food entries for a specific day.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `day` | date | None | Date to query (None = today) |

**Returns:** `list[dict]` — List of food entries

**Example:**
```python
from datetime import date, timedelta

# Today's log
log = tracker.get_food_log()

# Yesterday's log
yesterday = date.today() - timedelta(days=1)
log = tracker.get_food_log(yesterday)
```

---

## Water Tracking

### `log_water(amount, unit="ml")`

Log water intake.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `amount` | float | required | Quantity |
| `unit` | str | "ml" | Unit of measurement |

**Supported Units:**
| Unit | Conversion |
|------|------------|
| `ml` | 1ml |
| `l`, `liter`, `liters` | 1000ml |
| `glass`, `glasses` | 237ml (8 fl oz) |
| `oz`, `ounce`, `ounces` | 29.57ml |
| `cup`, `cups` | 236.6ml |

**Returns:** `dict` — The logged entry

**Example:**
```python
tracker.log_water(500, "ml")
tracker.log_water(2, "glasses")
tracker.log_water(1.5, "liters")
```

---

### `get_water_status(day=None)`

Get water intake status.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `day` | date | None | Date to query (None = today) |

**Returns:** `dict`
```python
{
    "total_ml": 1500,
    "total_liters": 1.5,
    "glasses": 6.3,
    "goal_ml": 3000,
    "goal_liters": 3.0,
    "remaining_ml": 1500,
    "progress_pct": 50.0
}
```

---

## Daily Summary

### `get_daily_summary(day=None)`

Get complete daily statistics.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `day` | date | None | Date to query (None = today) |

**Returns:** `dict`
```python
{
    "date": "2026-01-10",
    "food": {
        "calories": 1500,
        "protein_g": 95,
        "carbs_g": 150,
        "fat_g": 55,
        "entries": 5
    },
    "water": {
        "total_ml": 2250,
        "total_liters": 2.25,
        "glasses": 9.5
    },
    "goals": {
        "calories": 2000,
        "protein_g": 150,
        "water_ml": 3000
    },
    "progress": {
        "calories_pct": 75.0,
        "protein_pct": 63.3,
        "water_pct": 75.0
    }
}
```

---

## Goals

### `set_goal(category, value)`

Set a daily goal.

**Parameters:**
| Name | Type | Description |
|------|------|-------------|
| `category` | str | Goal type |
| `value` | float | Target value |

**Categories:**
- `calories` — Daily calorie target
- `protein_g` — Protein in grams
- `carbs_g` — Carbohydrates in grams
- `fat_g` — Fat in grams
- `water_ml` — Water in milliliters

**Returns:** `dict` — Updated goals

**Example:**
```python
tracker.set_goal("protein_g", 180)
tracker.set_goal("water_ml", 4000)
```

---

### `get_goals()`

Get current goals.

**Returns:** `dict`
```python
{
    "calories": 2000,
    "protein_g": 150,
    "water_ml": 3000
}
```

---

## HTTP API

When running the dashboard server, these endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML |
| `/?date=YYYY-MM-DD` | GET | Dashboard for specific date |
| `/api/summary` | GET | Daily summary JSON |
| `/api/food` | GET | Food log JSON |
| `/api/water` | GET | Water status JSON |
| `/api/goals` | GET | Goals JSON |
| `/api/week` | GET | 7-day summary JSON |

All endpoints accept `?date=YYYY-MM-DD` parameter.
