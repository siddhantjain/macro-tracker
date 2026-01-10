---
layout: default
title: Tool Reference
---

# LLM Tool Reference

Complete guide for AI assistants using Macro Tracker.

{% raw %}
> **For LLMs:** This page describes how to use Macro Tracker as a tool. Parse user intent, call the appropriate function, and format a helpful response.
{% endraw %}

## Quick Reference

| Action | Function | Example |
|--------|----------|---------|
| Log food | `tracker.log_food(name, quantity)` | `tracker.log_food("eggs", quantity=2)` |
| Log water | `tracker.log_water(amount, unit)` | `tracker.log_water(2, "glasses")` |
| Check progress | `tracker.get_daily_summary()` | Returns calories, protein, water stats |
| Water status | `tracker.get_water_status()` | Quick water check with remaining |
| Set goal | `tracker.set_goal(type, value)` | `tracker.set_goal("protein_g", 180)` |
| Search food | `tracker.search_food(query)` | Lookup without logging |
| View log | `tracker.get_food_log()` | List today's food entries |

## Natural Language Parsing

### Food Logging

| User Says | Parse As |
|-----------|----------|
| "2 eggs" | `log_food("eggs", quantity=2)` |
| "a bowl of dal" | `log_food("dal", quantity=1)` |
| "200g chicken breast" | `log_food("chicken breast", quantity=200, unit="g")` |
| "large coffee with milk" | `log_food("coffee with milk", quantity=1)` |
| "protein shake, 30g protein, 200 cal" | `log_food("protein shake", protein_g=30, calories=200)` |

### Water Logging

| User Says | Parse As |
|-----------|----------|
| "glass of water" | `log_water(1, "glasses")` |
| "2 glasses of water" | `log_water(2, "glasses")` |
| "500ml water" | `log_water(500, "ml")` |
| "a liter of water" | `log_water(1, "liters")` |
| "big bottle of water" | `log_water(500, "ml")` (estimate) |

### Queries

| User Says | Action |
|-----------|--------|
| "how much protein today" | `get_daily_summary()` → report protein |
| "water status" | `get_water_status()` |
| "what did I eat" | `get_food_log()` |
| "daily summary" | `get_daily_summary()` |
| "am I on track" | `get_daily_summary()` → compare to goals |

## Response Templates

### After Logging Food

```
Logged: {food_name} — {calories} cal, {protein}g protein

Today's total: {total_calories} cal ({calories_pct}%), {total_protein}g protein ({protein_pct}%)
```

### After Logging Water

```
Logged {amount}ml water 💧

Today: {total_liters}L / {goal_liters}L ({progress_pct}%)
{remaining}ml to go!
```

### Daily Summary

```
📊 Today's Progress

🔥 Calories: {calories} / {goal} ({pct}%)
💪 Protein: {protein}g / {goal}g ({pct}%)
💧 Water: {liters}L / {goal}L ({pct}%)

{encouragement_based_on_progress}
```

## Handling Edge Cases

### Food Not Found

If `search_food()` returns empty:

1. Ask user for nutrition info: "I couldn't find that. Do you know the calories and protein?"
2. Or estimate: "I'll estimate a medium portion at ~300 calories"
3. Log with manual values: `log_food(name, calories=300)`

### Ambiguous Quantities

- "some chicken" → default to 1 serving
- "a lot of water" → estimate 500ml
- "small salad" → 1 serving, note "small" in name

### Past Dates

Support logging to yesterday:
```python
from datetime import date, timedelta
yesterday = date.today() - timedelta(days=1)
# Note: current version logs to today only
# Future: tracker.log_food(..., day=yesterday)
```

## Encouragement Guidelines

Based on progress percentage:

| Progress | Response Tone |
|----------|---------------|
| 0-25% | Encouraging start |
| 25-50% | Good progress |
| 50-75% | More than halfway! |
| 75-99% | Almost there! |
| 100%+ | Goal achieved! 🎉 |

## Error Handling

| Error | User Message |
|-------|--------------|
| API timeout | "Having trouble looking that up. Want to add it manually?" |
| Invalid unit | "I don't recognize that unit. Try ml, glasses, or liters." |
| Negative value | "That doesn't seem right. How much did you actually have?" |

## Best Practices

1. **Confirm logging** — Always tell user what was logged
2. **Show context** — Include daily totals after each entry
3. **Be encouraging** — Celebrate progress toward goals
4. **Handle errors gracefully** — Offer alternatives when lookup fails
5. **Respect intent** — If user says "log" they want to track, not just search
