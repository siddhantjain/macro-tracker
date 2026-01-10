---
layout: default
title: Architecture
---

# Architecture

Overview of Macro Tracker's system design.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      User / AI Assistant                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MacroTracker (tracker.py)                 │
│  • log_food()      • log_water()      • get_daily_summary() │
│  • search_food()   • get_water_status()  • set_goal()       │
└─────────────────────────────────────────────────────────────┘
                    │                   │
         ┌──────────┘                   └──────────┐
         ▼                                         ▼
┌─────────────────────┐                 ┌─────────────────────┐
│  NutritionProvider  │                 │      JsonStore      │
│  (providers/)       │                 │    (storage/)       │
├─────────────────────┤                 ├─────────────────────┤
│ • search()          │                 │ • log_food()        │
│ • get_by_id()       │                 │ • log_water()       │
└─────────────────────┘                 │ • get_daily_*()     │
         │                              │ • set_goal()        │
         ▼                              └─────────────────────┘
┌─────────────────────┐                            │
│  USDA FoodData API  │                            ▼
│  (External)         │                 ┌─────────────────────┐
└─────────────────────┘                 │    data/*.json      │
                                        │  (Local Storage)    │
                                        └─────────────────────┘
```

## Components

### MacroTracker (`tracker.py`)

The main API class that orchestrates all operations.

**Responsibilities:**
- Coordinate between providers and storage
- Handle unit conversions
- Calculate progress percentages
- Provide clean interface for AI assistants

### NutritionProvider (`providers/base.py`)

Abstract interface for nutrition data sources.

**Methods:**
- `search(query, limit)` — Find foods matching query
- `get_by_id(food_id)` — Get specific food by ID

**Implementations:**
- `USDAProvider` — USDA FoodData Central API

### JsonStore (`storage/json_store.py`)

Local file-based storage using JSON.

**Data Files:**
- `food_YYYY-MM-DD.json` — Daily food entries
- `water_YYYY-MM-DD.json` — Daily water entries
- `goals.json` — User goals

### Dashboard Server (`server.py`)

HTTP server for the web dashboard.

**Features:**
- Server-side rendered HTML
- Real-time data on each request
- Date navigation via URL parameters
- HTTP Basic Auth for security

## Data Flow

### Logging Food

```
1. User: "I had 2 eggs"
2. AI parses: food="eggs", quantity=2
3. tracker.log_food("eggs", quantity=2)
4. USDAProvider.search("eggs")
5. USDA API returns nutrition data
6. tracker multiplies by quantity
7. JsonStore.log_food(entry)
8. Entry saved to data/food_2026-01-10.json
9. Returns entry to AI
10. AI responds with summary
```

### Daily Summary

```
1. User: "How am I doing today?"
2. tracker.get_daily_summary()
3. JsonStore.get_daily_macros()
4. JsonStore.get_daily_water()
5. JsonStore.get_goals()
6. tracker calculates percentages
7. Returns summary dict
8. AI formats friendly response
```

## File Structure

```
macro-tracker/
├── src/
│   ├── __init__.py
│   ├── tracker.py          # Main API
│   ├── server.py           # Dashboard server
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py         # Provider interface
│   │   └── usda.py         # USDA implementation
│   └── storage/
│       ├── __init__.py
│       └── json_store.py   # JSON file storage
├── data/                   # User data (gitignored)
│   ├── food_*.json
│   ├── water_*.json
│   └── goals.json
├── docs/                   # Documentation
├── TOOL.md                 # LLM reference
└── README.md
```

## Design Decisions

### Why JSON Files?

- **Simplicity** — No database setup required
- **Portability** — Easy to backup, inspect, migrate
- **Transparency** — Users can see/edit their data
- **AI-friendly** — Easy to query and manipulate

### Why Server-Side Rendering?

- **No build step** — Pure Python, no JS bundling
- **Fresh data** — Always shows current state
- **Simple auth** — HTTP Basic Auth just works
- **LLM-friendly** — AI can generate/modify templates

### Why Pluggable Providers?

- **Flexibility** — Add regional food databases
- **Offline mode** — Could add local-only provider
- **Testing** — Easy to mock for tests
