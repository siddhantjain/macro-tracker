"""Main tracker module - the interface LLMs and users interact with."""
import re
from datetime import datetime, date
from typing import Optional

from .providers.usda import USDAProvider, default_provider
from .storage.json_store import JsonStore, FoodEntry, default_store


class MacroTracker:
    """Main tracker class for food and water logging."""

    def __init__(
        self,
        provider=None,
        store=None,
    ):
        self.provider = provider or default_provider
        self.store = store or default_store

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
        unit: str = "serving",
        calories: Optional[float] = None,
        protein_g: Optional[float] = None,
        carbs_g: Optional[float] = None,
        fat_g: Optional[float] = None,
    ) -> dict:
        """Log a food item.
        
        If nutrition values not provided, will search and use first result.
        
        Args:
            name: Food name
            quantity: Amount consumed
            unit: Unit (serving, g, oz, cup, etc.)
            calories: Optional manual override
            protein_g: Optional manual override
            carbs_g: Optional manual override
            fat_g: Optional manual override
            
        Returns:
            The logged entry
        """
        # If nutrition not provided, search for it
        if calories is None:
            results = self.provider.search(name, limit=1)
            if results:
                info = results[0]
                calories = info.calories * quantity
                protein_g = info.protein_g * quantity
                carbs_g = info.carbs_g * quantity
                fat_g = info.fat_g * quantity
                source = info.source
                fdc_id = info.fdc_id
            else:
                # Don't silently zero - return error so caller can handle
                return {
                    "logged": False,
                    "error": "nutrition_not_found",
                    "message": f"Could not find nutrition info for '{name}'. Please provide calories/protein/carbs/fat manually, or search using another source.",
                    "name": name,
                    "quantity": quantity,
                    "unit": unit,
                }
        else:
            source = "manual"
            fdc_id = None
            protein_g = protein_g or 0
            carbs_g = carbs_g or 0
            fat_g = fat_g or 0

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
        return self.store.log_food(entry)

    def get_food_log(self, day: date = None) -> list[dict]:
        """Get all food entries for a day."""
        return self.store.get_food_log(day)

    def get_daily_summary(self, day: date = None) -> dict:
        """Get daily macro summary with progress toward goals."""
        macros = self.store.get_daily_macros(day)
        water = self.store.get_daily_water(day)
        goals = self.store.get_goals()
        
        return {
            "date": (day or date.today()).isoformat(),
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

        return self.store.log_water(amount_ml)

    def get_water_status(self, day: date = None) -> dict:
        """Get water intake status for a day."""
        water = self.store.get_daily_water(day)
        goals = self.store.get_goals()
        goal_ml = goals.get("water_ml", 3000)
        
        return {
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
