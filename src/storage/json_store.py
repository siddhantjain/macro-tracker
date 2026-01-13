"""JSON file-based storage for tracking data."""
import json
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from zoneinfo import ZoneInfo


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

    def __init__(self, data_dir: str = None, default_timezone: str = "UTC"):
        if data_dir is None:
            # Default to data/ in the package directory
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.default_timezone = default_timezone

    def _get_file(self, category: str, day: date = None) -> Path:
        """Get the file path for a category and date (UTC)."""
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

    def _get_local_day_utc_range(self, local_date: date, timezone: str) -> tuple[datetime, datetime]:
        """Get UTC datetime range for a local date.
        
        Args:
            local_date: The date in local timezone
            timezone: Timezone name (e.g., 'America/Los_Angeles')
            
        Returns:
            Tuple of (start_utc, end_utc) datetimes
        """
        tz = ZoneInfo(timezone)
        # Start of local day in local timezone
        local_start = datetime(local_date.year, local_date.month, local_date.day, 0, 0, 0, tzinfo=tz)
        # End of local day (start of next day)
        local_end = local_start + timedelta(days=1)
        # Convert to UTC
        utc_start = local_start.astimezone(ZoneInfo("UTC"))
        utc_end = local_end.astimezone(ZoneInfo("UTC"))
        return utc_start, utc_end

    def _load_for_local_day(self, category: str, local_date: date = None, timezone: str = None) -> list:
        """Load entries for a local day, potentially spanning multiple UTC files.
        
        Args:
            category: 'food' or 'water'
            local_date: Date in the user's local timezone (defaults to today in that tz)
            timezone: Timezone name (e.g., 'America/Los_Angeles')
            
        Returns:
            List of entries that fall within the local day
        """
        timezone = timezone or self.default_timezone
        
        # If no timezone awareness needed, use simple load
        if timezone == "UTC":
            return self._load(category, local_date)
        
        tz = ZoneInfo(timezone)
        if local_date is None:
            local_date = datetime.now(tz).date()
        
        # Get UTC range for this local day
        utc_start, utc_end = self._get_local_day_utc_range(local_date, timezone)
        
        # Determine which UTC dates we need to load
        # The local day might span 2 UTC dates
        utc_dates = set()
        utc_dates.add(utc_start.date())
        utc_dates.add((utc_end - timedelta(seconds=1)).date())  # End is exclusive, so check just before
        
        # Load entries from all relevant UTC date files
        all_entries = []
        for utc_date in utc_dates:
            all_entries.extend(self._load(category, utc_date))
        
        # Filter to only entries within the local day's UTC range
        filtered = []
        for entry in all_entries:
            ts_str = entry.get("timestamp", "")
            try:
                # Parse the ISO timestamp
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                entry_dt = datetime.fromisoformat(ts_str)
                # Make timezone-aware if naive (assume UTC)
                if entry_dt.tzinfo is None:
                    entry_dt = entry_dt.replace(tzinfo=ZoneInfo("UTC"))
                else:
                    entry_dt = entry_dt.astimezone(ZoneInfo("UTC"))
                
                # Check if within range
                if utc_start <= entry_dt < utc_end:
                    filtered.append(entry)
            except (ValueError, TypeError):
                # If timestamp parsing fails, skip this entry
                continue
        
        return filtered

    def _save(self, category: str, entries: list, day: date = None):
        """Save entries to a file."""
        path = self._get_file(category, day)
        with open(path, "w") as f:
            json.dump(entries, f, indent=2)

    # Food methods
    def log_food(self, entry: FoodEntry, timezone: str = None) -> dict:
        """Log a food entry.
        
        Args:
            entry: The food entry to log
            timezone: Timezone for determining which date file to use.
                      Defaults to store's default_timezone.
        """
        timezone = timezone or self.default_timezone
        tz = ZoneInfo(timezone)
        
        # Use local date for file
        local_date = datetime.now(tz).date()
        
        entries = self._load("food", local_date)
        entry_dict = asdict(entry)
        entries.append(entry_dict)
        self._save("food", entries, local_date)
        return entry_dict

    def delete_food_entry(self, timestamp: str) -> dict:
        """Delete a food entry by its timestamp.
        
        Args:
            timestamp: ISO timestamp of the entry to delete
            
        Returns:
            {"deleted": True, "entry": {...}} or {"deleted": False, "reason": "not_found"}
        """
        # Parse timestamp to find which file it's in
        try:
            dt = datetime.fromisoformat(timestamp)
            entry_date = dt.date()
        except ValueError:
            return {"deleted": False, "reason": "invalid_timestamp"}
        
        # Load entries for that date
        entries = self._load("food", entry_date)
        
        # Find and remove the entry
        for i, entry in enumerate(entries):
            if entry.get("timestamp") == timestamp:
                removed = entries.pop(i)
                self._save("food", entries, entry_date)
                return {"deleted": True, "entry": removed}
        
        return {"deleted": False, "reason": "not_found", "timestamp": timestamp}

    def get_food_log(self, day: date = None, timezone: str = None) -> list[dict]:
        """Get food log for a day.
        
        Args:
            day: Date (in the specified timezone)
            timezone: Timezone name (e.g., 'America/Los_Angeles'). Defaults to store's default.
        """
        timezone = timezone or self.default_timezone
        return self._load_for_local_day("food", day, timezone)

    def get_daily_macros(self, day: date = None, timezone: str = None) -> dict:
        """Get totals for a day.
        
        Args:
            day: Date (in the specified timezone)
            timezone: Timezone name (e.g., 'America/Los_Angeles'). Defaults to store's default.
        """
        timezone = timezone or self.default_timezone
        entries = self._load_for_local_day("food", day, timezone)
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
    def log_water(self, amount_ml: float, timezone: str = None) -> dict:
        """Log water intake.
        
        Args:
            amount_ml: Amount of water in milliliters
            timezone: Timezone for determining which date file to use.
                      Defaults to store's default_timezone.
        """
        timezone = timezone or self.default_timezone
        tz = ZoneInfo(timezone)
        
        # Use local date for file, but UTC timestamp in entry
        local_now = datetime.now(tz)
        local_date = local_now.date()
        
        entries = self._load("water", local_date)
        entry = WaterEntry(
            timestamp=datetime.now(ZoneInfo("UTC")).isoformat(),
            amount_ml=amount_ml,
        )
        entry_dict = asdict(entry)
        entries.append(entry_dict)
        self._save("water", entries, local_date)
        return entry_dict

    def get_water_log(self, day: date = None, timezone: str = None) -> list[dict]:
        """Get water log for a day.
        
        Args:
            day: Date (in the specified timezone)
            timezone: Timezone name (e.g., 'America/Los_Angeles'). Defaults to store's default.
        """
        timezone = timezone or self.default_timezone
        return self._load_for_local_day("water", day, timezone)

    def get_daily_water(self, day: date = None, timezone: str = None) -> dict:
        """Get water totals for a day.
        
        Args:
            day: Date (in the specified timezone)
            timezone: Timezone name (e.g., 'America/Los_Angeles'). Defaults to store's default.
        """
        timezone = timezone or self.default_timezone
        entries = self._load_for_local_day("water", day, timezone)
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
# Default store with PT timezone (matching the default user timezone)
default_store = JsonStore(default_timezone="America/Los_Angeles")
