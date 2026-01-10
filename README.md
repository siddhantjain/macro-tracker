# 🍽️ Macro Tracker

**AI-native food and water tracking for LLM-powered assistants.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Macro Tracker is designed to be used by AI assistants as a tool. Tell your AI what you ate, and it handles nutrition lookup, logging, and progress tracking automatically.

## ✨ Features

- **🔍 Automatic Nutrition Lookup** — USDA FoodData Central with 300k+ foods including international cuisines
- **💧 Water Tracking** — Flexible units (ml, glasses, liters, oz)
- **📊 Progress Dashboard** — Web UI with daily/weekly views and charts
- **🤖 LLM-Native Design** — Built as a tool for AI assistants
- **🔌 Pluggable Providers** — Add your own nutrition data sources
- **💾 Local Storage** — Your data stays on your machine

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/siddhantjain/macro-tracker.git
cd macro-tracker
```

No dependencies required — uses Python standard library only.

### USDA API Key (Required)

Get a **free** API key from USDA FoodData Central:

1. Sign up at https://fdc.nal.usda.gov/api-key-signup.html
2. Check your email for the key (instant)
3. Add to `.env` file:
   ```
   USDA_API_KEY=your_key_here
   ```

The free key gives you **3,600 requests/hour** — plenty for personal use!

### Basic Usage

```python
from src.tracker import tracker

# Log food (auto-looks up nutrition)
tracker.log_food("2 scrambled eggs", quantity=2)

# Log water
tracker.log_water(2, "glasses")

# Get daily summary
tracker.get_daily_summary()
```

### Run Dashboard

```bash
python -m src.server
# Open http://localhost:4001
```

## 🤖 For AI Assistants

See **[TOOL.md](TOOL.md)** for the complete LLM integration reference.

### Example Prompts → Actions

| User Says | Tool Action |
|-----------|-------------|
| "I had 2 eggs and toast" | `tracker.log_food("eggs", quantity=2)` then `tracker.log_food("toast")` |
| "Log a protein shake, 200 cal, 30g protein" | `tracker.log_food("protein shake", calories=200, protein_g=30)` |
| "Drank 3 glasses of water" | `tracker.log_water(3, "glasses")` |
| "How much protein today?" | `tracker.get_daily_summary()["food"]["protein_g"]` |
| "Set my protein goal to 180g" | `tracker.set_goal("protein_g", 180)` |

## 📖 Documentation

- [Tool Reference (TOOL.md)](TOOL.md) — LLM integration guide
- [API Reference](docs/api.md) — Full API documentation
- [Architecture](docs/architecture.md) — System design
- [Adding Providers](docs/providers.md) — Custom nutrition sources

## 🏗️ Architecture

```
macro-tracker/
├── src/
│   ├── tracker.py      # Main API - start here
│   ├── providers/      # Nutrition data sources
│   │   ├── base.py     # Provider interface
│   │   └── usda.py     # USDA FoodData Central
│   ├── storage/
│   │   └── json_store.py  # Local JSON storage
│   └── server.py       # Dashboard web server
├── data/               # Your logs (gitignored)
├── TOOL.md             # LLM reference
└── docs/               # Documentation
```

## 🍕 Supported Foods

The USDA database includes:
- American foods
- Indian cuisine (dal, paneer, roti, biryani, dosa...)
- Asian foods (rice, noodles, tofu, curry...)
- European foods
- Branded products
- Restaurant items

## 🔧 Configuration

### Goals

```python
tracker.set_goal("calories", 2000)
tracker.set_goal("protein_g", 150)
tracker.set_goal("water_ml", 3000)
```

### Custom Providers

```python
from src.providers.base import NutritionProvider

class MyProvider(NutritionProvider):
    def search(self, query, limit=5):
        # Your implementation
        pass
```

## 📊 Dashboard

The web dashboard shows:
- Daily calories, protein, carbs, fat
- Water intake with goal progress
- 7-day trend charts
- Food log with per-item breakdown
- Date navigation

## 🔒 Privacy

- All data stored locally in `data/` directory
- No external services except USDA API for nutrition lookup
- Dashboard supports HTTP Basic Auth

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

## 🙏 Credits

- Nutrition data: [USDA FoodData Central](https://fdc.nal.usda.gov/)
- Charts: [Chart.js](https://www.chartjs.org/)
