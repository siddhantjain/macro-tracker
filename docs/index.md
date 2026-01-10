---
layout: default
title: Macro Tracker Documentation
---

# Macro Tracker Documentation

Welcome to Macro Tracker — an AI-native food and water tracking tool.

## What is Macro Tracker?

Macro Tracker is a nutrition tracking system designed to be used by AI assistants. Instead of manually entering foods into an app, you simply tell your AI assistant what you ate, and it handles everything:

1. **Looks up nutrition** from the USDA database
2. **Logs the entry** with timestamp
3. **Tracks progress** toward your daily goals
4. **Shows trends** over time

## Quick Links

- [Tool Reference](tool-reference.md) — How AI assistants should use this tool
- [API Documentation](api.md) — Complete API reference
- [Architecture](architecture.md) — System design and data flow
- [Custom Providers](providers.md) — Add your own nutrition sources

## Getting Started

### Installation

```bash
git clone https://github.com/yourusername/macro-tracker.git
cd macro-tracker
python -m src.server  # Start dashboard on port 4001
```

### Basic Usage

```python
from src.tracker import tracker

# Log food
tracker.log_food("chicken salad")

# Log water
tracker.log_water(2, "glasses")

# Check progress
summary = tracker.get_daily_summary()
print(f"Protein: {summary['food']['protein_g']}g")
```

## Features

### 🔍 Automatic Nutrition Lookup

The USDA FoodData Central database includes:
- 300,000+ foods
- Branded products
- Restaurant items
- International cuisines (Indian, Asian, European, etc.)

### 💧 Flexible Water Tracking

Track water in any unit:
- Milliliters (ml)
- Liters (l)
- Glasses (8 fl oz = 237ml)
- Ounces (oz)
- Cups

### 📊 Dashboard

A web-based dashboard showing:
- Daily macros with progress bars
- Water intake
- 7-day trend charts
- Food log

### 🔌 Extensible

Add your own nutrition providers by implementing the `NutritionProvider` interface.

## Example Conversation

**User:** I had 2 eggs and toast for breakfast

**AI:** Logged:
- 2x eggs — 143 cal, 12.6g protein
- Toast — 79 cal, 2.7g protein

Today's total: 222 cal, 15.3g protein (10% of goal)

---

**User:** Just drank a big glass of water

**AI:** Logged 237ml water. Today: 0.7L / 3L (24%)

---

**User:** How am I doing on protein?

**AI:** You've had 89g of protein today (59% of your 150g goal). You need about 61g more — that's roughly a chicken breast or a protein shake.

## Support

- [GitHub Issues](https://github.com/yourusername/macro-tracker/issues)
- [Contributing Guide](contributing.md)
