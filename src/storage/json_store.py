"""JSON file-based storage for tracking data."""
import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class FoodEntry:
    """A logged food entry."""
    timestamp: str
    name: str
    quantity: float
    unit: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    source: str = "manual"
    fdc_id: Optional[int] = None


@dataclass
class WaterEntry:
    """A logged water entry."""
    timestamp: str
    amount_ml: float


class JsonStore:
    """JSON file-based storage."""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default to data/ in the package directory
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_file(self, category: str, day: date = None) -> Path:
        """Get the file path for a category and date."""
        if day is None:
            day = date.today()
        return self.data_dir / f"{category}_{day.isoformat()}.json"

    def _load(self, category: str, day: date = None) -> list:
        """Load entries from a file."""
        path = self._get_file(category, day)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return []

    def _save(self, category: str, entries: list, day: date = None):
        """Save entries to a file."""
        path = self._get_file(category, day)
        with open(path, "w") as f:
            json.dump(entries, f, indent=2)

    # Food methods
    def log_food(self, entry: FoodEntry) -> dict:
        """Log a food entry."""
        entries = self._load("food")
        entry_dict = asdict(entry)
        entries.append(entry_dict)
        self._save("food", entries)
        return entry_dict

    def get_food_log(self, day: date = None) -> list[dict]:
        """Get food log for a day."""
        return self._load("food", day)

    def get_daily_macros(self, day: date = None) -> dict:
        """Get totals for a day."""
        entries = self._load("food", day)
        totals = {
            "calories": 0,
            "protein_g": 0,
            "carbs_g": 0,
            "fat_g": 0,
            "entries": len(entries),
        }
        for entry in entries:
            totals["calories"] += entry.get("calories", 0)
            totals["protein_g"] += entry.get("protein_g", 0)
            totals["carbs_g"] += entry.get("carbs_g", 0)
            totals["fat_g"] += entry.get("fat_g", 0)
        return totals

    # Water methods
    def log_water(self, amount_ml: float) -> dict:
        """Log water intake."""
        entries = self._load("water")
        entry = WaterEntry(
            timestamp=datetime.now().isoformat(),
            amount_ml=amount_ml,
        )
        entry_dict = asdict(entry)
        entries.append(entry_dict)
        self._save("water", entries)
        return entry_dict

    def get_water_log(self, day: date = None) -> list[dict]:
        """Get water log for a day."""
        return self._load("water", day)

    def get_daily_water(self, day: date = None) -> dict:
        """Get water totals for a day."""
        entries = self._load("water", day)
        total_ml = sum(e.get("amount_ml", 0) for e in entries)
        return {
            "total_ml": total_ml,
            "total_liters": round(total_ml / 1000, 2),
            "glasses": round(total_ml / 237, 1),  # 237ml = 1 glass (8 fl oz)
            "entries": len(entries),
        }

    # Goals
    def _goals_file(self) -> Path:
        return self.data_dir / "goals.json"

    def set_goal(self, category: str, value: float):
        """Set a daily goal."""
        path = self._goals_file()
        goals = {}
        if path.exists():
            with open(path) as f:
                goals = json.load(f)
        goals[category] = value
        with open(path, "w") as f:
            json.dump(goals, f, indent=2)

    def get_goals(self) -> dict:
        """Get all goals."""
        path = self._goals_file()
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {
            "water_ml": 3000,  # Default 3L
            "protein_g": 150,  # Default 150g
            "calories": 2000,  # Default 2000 kcal
        }


# Default store instance
default_store = JsonStore()
