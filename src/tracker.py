"""Main tracker module - the interface LLMs and users interact with."""
import os
import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

from .providers.usda import USDAProvider, default_provider
from .storage.json_store import JsonStore, FoodEntry, default_store


class MacroTracker:
    """Main tracker class for food and water logging."""

    # Default timezone for the user
    DEFAULT_TIMEZONE = "America/Los_Angeles"
    
    # Default dedupe window in minutes (0 = disabled)
    DEFAULT_DEDUPE_WINDOW = 5

    def __init__(
        self,
        provider=None,
        store=None,
        timezone: str = None,
        test_mode: bool = None,
    ):
        """Initialize the tracker.
        
        Args:
            provider: Nutrition data provider (default: USDA)
            store: Storage backend (default: JsonStore)
            timezone: User's timezone (default: America/Los_Angeles)
            test_mode: If True, uses a separate test database. 
                      Can also be set via MACRO_TRACKER_TEST_MODE=1 env var.
        """
        # Check for test mode
        if test_mode is None:
            test_mode = os.environ.get('MACRO_TRACKER_TEST_MODE', '').lower() in ('1', 'true', 'yes')
        
        self.test_mode = test_mode
        self.provider = provider or default_provider
        
        if test_mode and store is None:
            # Use separate test data directory
            from pathlib import Path
            test_data_dir = Path(__file__).parent.parent / "data_test"
            self.store = JsonStore(data_dir=str(test_data_dir))
            print(f"⚠️  TEST MODE: Using {test_data_dir}")
        else:
            self.store = store or default_store
            
        self.timezone = timezone or self.DEFAULT_TIMEZONE

    # ─────────────────────────────────────────────────────────────
    # Food tracking
    # ─────────────────────────────────────────────────────────────

    def search_food(self, query: str, limit: int = 5) -> list[dict]:
        """Search for a food item.
        
        Args:
            query: Food to search for (e.g., "chicken breast", "dal")
            limit: Max results to return
            
        Returns:
            List of food items with nutrition info
        """
        results = self.provider.search(query, limit)
        return [r.to_dict() for r in results]

    def log_food(
        self,
        name: str,
        quantity: float = 1,
        unit: str = "g",
        calories: Optional[float] = None,
        protein_g: Optional[float] = None,
        carbs_g: Optional[float] = None,
        fat_g: Optional[float] = None,
        dedupe_window_minutes: int = None,
        dry_run: bool = False,
    ) -> dict:
        """Log a food item with proper unit conversion.
        
        IMPORTANT: Unit conversion is now strict. If you specify a unit like "cup",
        we will look up the gram weight from USDA portion data. If no matching 
        portion is found, logging will FAIL with an error and available portions.
        
        For reliable logging, either:
        1. Use unit="g" and specify quantity in grams
        2. Provide calories/protein_g/carbs_g/fat_g manually
        3. Use a unit that matches USDA portion data (cup, oz, slice, etc.)
        
        Args:
            name: Food name
            quantity: Amount consumed  
            unit: Unit of measurement. Supported:
                  - "g" / "gram" - quantity is in grams (most reliable)
                  - "cup" - will look up "1 cup = Xg" from USDA
                  - "oz" / "ounce" - will look up ounce conversion
                  - "tbsp" / "tsp" - tablespoon/teaspoon
                  - "slice", "piece", "serving" - if USDA has data
                  - Other units may work if USDA has portion data
            calories: Optional manual override (bypasses USDA lookup)
            protein_g: Optional manual override
            carbs_g: Optional manual override
            fat_g: Optional manual override
            dedupe_window_minutes: Time window to check for duplicates.
                                   Set to 0 to disable. Default: 5 minutes.
            dry_run: If True, returns what would be logged without saving.
            
        Returns:
            On success: {"logged": True, ...entry data...}
            On failure: {"logged": False, "error": "...", "available_portions": [...]}
        """
        # Use default dedupe window if not specified
        if dedupe_window_minutes is None:
            dedupe_window_minutes = self.DEFAULT_DEDUPE_WINDOW
        
        # Check for duplicates
        if dedupe_window_minutes > 0 and not dry_run:
            duplicate = self._check_duplicate(name, dedupe_window_minutes)
            if duplicate:
                return duplicate
        
        # Normalize unit
        unit_lower = unit.lower().strip()
        
        # If manual nutrition provided, use it directly
        if calories is not None:
            source = "manual"
            fdc_id = None
            protein_g = protein_g or 0
            carbs_g = carbs_g or 0
            fat_g = fat_g or 0
            gram_weight = None
            conversion = "manual entry"
        
        # If unit is grams, do simple lookup (quantity = grams)
        elif unit_lower in ("g", "gram", "grams"):
            results = self.provider.search(name, limit=1)
            if not results:
                return {
                    "logged": False,
                    "error": "FOOD_NOT_FOUND",
                    "message": f"Could not find '{name}' in USDA database.",
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "suggestion": "Try a more specific food name, or provide nutrition manually.",
                }
            
            info = results[0]
            gram_weight = quantity
            scale = gram_weight / 100  # USDA nutrition is per 100g
            
            calories = round(info.calories * scale, 1)
            protein_g = round(info.protein_g * scale, 1)
            carbs_g = round(info.carbs_g * scale, 1)
            fat_g = round(info.fat_g * scale, 1)
            source = info.source
            fdc_id = info.fdc_id
            conversion = f"{quantity}g direct"
        
        # For other units, we MUST find a portion match
        else:
            # Use the new search_with_portions method
            result = self.provider.search_with_portions(name, unit, quantity)
            
            if not result["success"]:
                # Failed to find portion match - return error with available portions
                return {
                    "logged": False,
                    "error": result.get("error", "CONVERSION_FAILED"),
                    "message": result.get("message", f"Could not convert {quantity} {unit} of {name}"),
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                    "available_portions": result.get("available_portions", []),
                    "suggestion": result.get("suggestion", "Please specify in grams or use an available portion."),
                }
            
            # Success! Extract nutrition
            nutrition = result["nutrition"]
            calories = nutrition["calories"]
            protein_g = nutrition["protein_g"]
            carbs_g = nutrition["carbs_g"]
            fat_g = nutrition["fat_g"]
            gram_weight = result["gram_weight"]
            conversion = result["conversion"]
            source = result["food"].source
            fdc_id = result["food"].fdc_id

        entry = FoodEntry(
            timestamp=datetime.now().isoformat(),
            name=name,
            quantity=quantity,
            unit=unit,
            calories=round(calories, 1),
            protein_g=round(protein_g, 1),
            carbs_g=round(carbs_g, 1),
            fat_g=round(fat_g, 1),
            source=source,
            fdc_id=fdc_id,
        )
        
        # Dry run - return what would be logged without saving
        if dry_run:
            from dataclasses import asdict
            return {
                "dry_run": True,
                "would_log": asdict(entry),
                "gram_weight": gram_weight if 'gram_weight' in dir() else None,
                "conversion": conversion if 'conversion' in dir() else None,
                "message": "Dry run - nothing saved. Remove dry_run=True to log."
            }
        
        result = self.store.log_food(entry, timezone=self.timezone)
        result["logged"] = True
        if 'gram_weight' in dir() and gram_weight:
            result["gram_weight"] = gram_weight
            result["conversion"] = conversion
        return result
    
    def _check_duplicate(self, name: str, window_minutes: int) -> Optional[dict]:
        """Check if same food was logged recently.
        
        Args:
            name: Food name to check
            window_minutes: Time window in minutes
            
        Returns:
            Dict with duplicate info if found, None otherwise
        """
        recent = self.recent_entries(minutes=window_minutes)
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        
        for entry in recent:
            # Case-insensitive comparison
            if entry['name'].lower() == name.lower():
                entry_time = datetime.fromisoformat(entry['timestamp'])
                minutes_ago = round((datetime.now() - entry_time).total_seconds() / 60, 1)
                return {
                    "logged": False,
                    "reason": "duplicate_detected",
                    "message": f"'{name}' was already logged {minutes_ago} minutes ago.",
                    "existing_entry": entry,
                    "suggestion": "Set dedupe_window_minutes=0 to log anyway, or use a different name."
                }
        return None

    def log_meal(
        self,
        items: List[Dict[str, Any]],
        meal_name: str = None,
        dedupe_window_minutes: int = None,
        dry_run: bool = False,
    ) -> dict:
        """Log multiple food items as a meal.
        
        Args:
            items: List of food items, each with:
                   - name (required): Food name
                   - quantity: Amount (default 1)
                   - unit: Unit type (default "serving")
                   - calories, protein_g, carbs_g, fat_g: Optional nutrition
            meal_name: Optional name for the meal (for logging purposes)
            dedupe_window_minutes: Time window for duplicate detection per item.
                                   Set to 0 to disable.
            dry_run: If True, preview without saving.
            
        Returns:
            {"success": True, "items": [...], "total": {...}}
            or {"success": False, "errors": [...]}
        """
        if dedupe_window_minutes is None:
            dedupe_window_minutes = self.DEFAULT_DEDUPE_WINDOW
            
        logged_items = []
        errors = []
        skipped_duplicates = []
        
        total = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
        
        for item in items:
            result = self.log_food(
                name=item.get("name"),
                quantity=item.get("quantity", 1),
                unit=item.get("unit", "serving"),
                calories=item.get("calories"),
                protein_g=item.get("protein_g"),
                carbs_g=item.get("carbs_g"),
                fat_g=item.get("fat_g"),
                dedupe_window_minutes=dedupe_window_minutes,
                dry_run=dry_run,
            )
            
            if result.get("logged") or result.get("dry_run"):
                entry_data = result.get("would_log") if dry_run else result
                logged_items.append(entry_data)
                total["calories"] += entry_data.get("calories", 0)
                total["protein_g"] += entry_data.get("protein_g", 0)
                total["carbs_g"] += entry_data.get("carbs_g", 0)
                total["fat_g"] += entry_data.get("fat_g", 0)
            elif result.get("reason") == "duplicate_detected":
                skipped_duplicates.append(result)
            else:
                errors.append(result)
        
        # Round totals
        total = {k: round(v, 1) for k, v in total.items()}
        
        response = {
            "success": len(errors) == 0,
            "dry_run": dry_run,
            "meal_name": meal_name,
            "items_logged": len(logged_items),
            "items_skipped_duplicate": len(skipped_duplicates),
            "items_failed": len(errors),
            "items": logged_items,
            "total": total,
        }
        
        if skipped_duplicates:
            response["skipped_duplicates"] = skipped_duplicates
        if errors:
            response["errors"] = errors
            
        return response

    def recent_entries(self, minutes: int = 10) -> List[dict]:
        """Get food entries logged in the last N minutes.
        
        Useful for checking what was just logged before retrying.
        
        Args:
            minutes: Time window (default 10 minutes)
            
        Returns:
            List of recent food entries
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        all_entries = self.get_food_log()
        
        recent = []
        for entry in all_entries:
            try:
                entry_time = datetime.fromisoformat(entry['timestamp'])
                if entry_time > cutoff:
                    recent.append(entry)
            except (KeyError, ValueError):
                continue
                
        return recent

    def delete_entry(self, timestamp: str) -> dict:
        """Delete a food entry by its timestamp.
        
        Args:
            timestamp: ISO timestamp of the entry to delete
            
        Returns:
            {"deleted": True, "entry": {...}} or {"deleted": False, "reason": "..."}
        """
        return self.store.delete_food_entry(timestamp)
    
    def delete_entries(self, timestamps: List[str]) -> dict:
        """Delete multiple food entries by their timestamps.
        
        Args:
            timestamps: List of ISO timestamps to delete
            
        Returns:
            {"deleted_count": N, "not_found": [...]}
        """
        deleted = 0
        not_found = []
        
        for ts in timestamps:
            result = self.delete_entry(ts)
            if result.get("deleted"):
                deleted += 1
            else:
                not_found.append(ts)
                
        return {
            "deleted_count": deleted,
            "not_found": not_found,
            "success": len(not_found) == 0
        }

    def get_food_log(self, day: date = None, timezone: str = None) -> list[dict]:
        """Get all food entries for a day.
        
        Args:
            day: Date (in the specified timezone)
            timezone: Timezone name. Defaults to tracker's timezone.
        """
        timezone = timezone or self.timezone
        return self.store.get_food_log(day, timezone)

    def get_daily_summary(self, day: date = None, timezone: str = None) -> dict:
        """Get daily macro summary with progress toward goals.
        
        Args:
            day: Date (in the specified timezone). Defaults to today.
            timezone: Timezone name (e.g., 'America/Los_Angeles'). 
                      Defaults to tracker's timezone.
        """
        timezone = timezone or self.timezone
        
        # Use timezone-aware "today" if day not specified
        if day is None:
            day = datetime.now(ZoneInfo(timezone)).date()
        
        macros = self.store.get_daily_macros(day, timezone)
        water = self.store.get_daily_water(day, timezone)
        goals = self.store.get_goals()
        
        return {
            "date": day.isoformat(),
            "timezone": timezone,
            "food": {
                "calories": macros["calories"],
                "protein_g": macros["protein_g"],
                "carbs_g": macros["carbs_g"],
                "fat_g": macros["fat_g"],
                "entries": macros["entries"],
            },
            "water": {
                "total_ml": water["total_ml"],
                "total_liters": water["total_liters"],
                "glasses": water["glasses"],
            },
            "goals": goals,
            "progress": {
                "calories_pct": round(macros["calories"] / goals.get("calories", 2000) * 100, 1),
                "protein_pct": round(macros["protein_g"] / goals.get("protein_g", 150) * 100, 1),
                "water_pct": round(water["total_ml"] / goals.get("water_ml", 3000) * 100, 1),
            },
        }

    # ─────────────────────────────────────────────────────────────
    # Water tracking
    # ─────────────────────────────────────────────────────────────

    def log_water(self, amount: float, unit: str = "ml") -> dict:
        """Log water intake.
        
        Args:
            amount: Amount of water
            unit: Unit (ml, l, liters, glass, glasses, oz, cup)
            
        Returns:
            The logged entry
        """
        # Convert to ml
        unit = unit.lower()
        if unit in ("l", "liter", "liters"):
            amount_ml = amount * 1000
        elif unit in ("glass", "glasses"):
            amount_ml = amount * 237  # 1 glass = 8 fl oz ≈ 237ml
        elif unit in ("oz", "ounce", "ounces"):
            amount_ml = amount * 29.57
        elif unit in ("cup", "cups"):
            amount_ml = amount * 236.6
        else:  # ml
            amount_ml = amount

        return self.store.log_water(amount_ml, timezone=self.timezone)

    def get_water_status(self, day: date = None, timezone: str = None) -> dict:
        """Get water intake status for a day.
        
        Args:
            day: Date (in the specified timezone)
            timezone: Timezone name. Defaults to tracker's timezone.
        """
        timezone = timezone or self.timezone
        
        # Use timezone-aware "today" if day not specified
        if day is None:
            day = datetime.now(ZoneInfo(timezone)).date()
        
        water = self.store.get_daily_water(day, timezone)
        goals = self.store.get_goals()
        goal_ml = goals.get("water_ml", 3000)
        
        return {
            "date": day.isoformat(),
            "timezone": timezone,
            "total_ml": water["total_ml"],
            "total_liters": water["total_liters"],
            "glasses": water["glasses"],
            "goal_ml": goal_ml,
            "goal_liters": goal_ml / 1000,
            "remaining_ml": max(0, goal_ml - water["total_ml"]),
            "progress_pct": round(water["total_ml"] / goal_ml * 100, 1),
        }

    # ─────────────────────────────────────────────────────────────
    # Goals
    # ─────────────────────────────────────────────────────────────

    def set_goal(self, category: str, value: float) -> dict:
        """Set a daily goal.
        
        Args:
            category: Goal type (water_ml, protein_g, calories, carbs_g, fat_g)
            value: Target value
            
        Returns:
            Updated goals
        """
        self.store.set_goal(category, value)
        return self.store.get_goals()

    def get_goals(self) -> dict:
        """Get all current goals."""
        return self.store.get_goals()


# Default tracker instance
tracker = MacroTracker()
