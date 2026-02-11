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

## 📸 Photo-Based Food Logging

**NEW: Analyze food photos using OpenClaw vision!**

Upload a photo of your meal, and the API will:
1. Identify all food items in the photo
2. Estimate quantities
3. Look up nutrition data (calories, protein, carbs, fat)
4. Return structured JSON response

### API Endpoint

```
POST /api/food/analyze
Content-Type: multipart/form-data

Form field: "image" (image file)
```

### Response Format

```json
{
  "items": [
    {
      "name": "scrambled eggs",
      "quantity": 2,
      "unit": "eggs",
      "quantity_g": 100,
      "calories": 140,
      "protein_g": 12,
      "carbs_g": 2,
      "fat_g": 10,
      "source": "usda",
      "confidence": "high"
    },
    {
      "name": "toast",
      "quantity": 2,
      "unit": "slices",
      "quantity_g": 60,
      "calories": 160,
      "protein_g": 6,
      "carbs_g": 28,
      "fat_g": 2,
      "source": "usda",
      "confidence": "high"
    }
  ],
  "total": {
    "calories": 300,
    "protein_g": 18,
    "carbs_g": 30,
    "fat_g": 12
  }
}
```

### Example Usage (iOS Swift)

```swift
func analyzeFoodPhoto(image: UIImage) async throws -> FoodAnalysis {
    guard let imageData = image.jpegData(compressionQuality: 0.8) else {
        throw FoodLoggingError.invalidImage
    }
    
    let url = URL(string: "http://mac-mini:4001/api/food/analyze")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var body = Data()
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"image\"; filename=\"photo.jpg\"\r\n".data(using: .utf8)!)
    body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
    body.append(imageData)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = body
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(FoodAnalysis.self, from: data)
}
```

### Vision Queue Setup

The vision analysis uses OpenClaw's image tool. Neo monitors the vision queue automatically.

To manually process vision requests:
```bash
python scripts/process_vision_queue.py --once
```

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
