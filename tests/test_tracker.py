"""Tests for the main tracker module."""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.tracker import MacroTracker
from src.storage.json_store import JsonStore
from src.providers.base import NutritionInfo


class MockProvider:
    """Mock nutrition provider for testing."""
    
    @property
    def name(self):
        return "Mock Provider"
    
    def search(self, query, limit=5, data_types=None):
        """Return mock nutrition data."""
        if "notfound" in query.lower():
            return []
        return [
            NutritionInfo(
                name=query.title(),
                serving_size="100g",
                calories=150,
                protein_g=10,
                carbs_g=15,
                fat_g=5,
                source="mock",
                portions=[
                    {"description": "1 cup", "gram_weight": 200},
                    {"description": "1 serving", "gram_weight": 100},
                ]
            )
        ]
    
    def search_with_portions(self, query, unit, quantity=1, limit=3):
        """Mock portion search."""
        if "notfound" in query.lower():
            return {
                "success": False,
                "error": "FOOD_NOT_FOUND",
                "message": f"Could not find '{query}' in mock database.",
            }
        
        # Mock portion matching
        unit_lower = unit.lower()
        if unit_lower in ("cup", "cups"):
            gram_weight = 200 * quantity
        elif unit_lower in ("serving", "servings"):
            gram_weight = 100 * quantity
        elif unit_lower in ("g", "gram", "grams"):
            gram_weight = quantity
        else:
            return {
                "success": False,
                "error": "PORTION_NOT_FOUND",
                "message": f"Could not convert '{unit}' for '{query}'.",
                "available_portions": [
                    {"description": "1 cup", "gram_weight": 200},
                    {"description": "1 serving", "gram_weight": 100},
                ],
                "suggestion": "Use one of the available portions or specify in grams.",
            }
        
        scale = gram_weight / 100
        return {
            "success": True,
            "food": NutritionInfo(
                name=query.title(),
                serving_size="100g",
                calories=150,
                protein_g=10,
                carbs_g=15,
                fat_g=5,
                source="mock",
            ),
            "portion_match": {"description": f"1 {unit}", "gram_weight": gram_weight / quantity},
            "gram_weight": gram_weight,
            "nutrition": {
                "calories": 150 * scale,
                "protein_g": 10 * scale,
                "carbs_g": 15 * scale,
                "fat_g": 5 * scale,
                "fiber_g": 0,
            },
            "conversion": f"{quantity} {unit} = {gram_weight}g",
        }
    
    def get_by_id(self, food_id):
        return None


@pytest.fixture
def tracker():
    """Create a tracker with temp storage and mock provider."""
    temp_dir = tempfile.mkdtemp()
    store = JsonStore(data_dir=temp_dir)
    mock_provider = MockProvider()
    t = MacroTracker(provider=mock_provider, store=store)
    yield t
    shutil.rmtree(temp_dir)


class TestFoodTracking:
    """Tests for food logging."""

    def test_log_food_with_auto_lookup(self, tracker):
        """Logging food should auto-lookup nutrition (default unit is grams)."""
        result = tracker.log_food("chicken breast", quantity=100, unit="g")
        
        assert result["name"] == "chicken breast"
        assert result["calories"] == 150  # 150 cal per 100g
        assert result["protein_g"] == 10

    def test_log_food_with_quantity(self, tracker):
        """Quantity in grams should scale nutrition values."""
        result = tracker.log_food("eggs", quantity=200, unit="g")  # 200g = 2x100g
        
        assert result["calories"] == 300  # 150 * 2
        assert result["protein_g"] == 20  # 10 * 2

    def test_log_food_with_manual_values(self, tracker):
        """Manual values should override lookup."""
        result = tracker.log_food(
            "protein shake",
            calories=200,
            protein_g=30,
            carbs_g=5,
            fat_g=2,
        )
        
        assert result["calories"] == 200
        assert result["protein_g"] == 30
        assert result["source"] == "manual"

    def test_log_food_not_found(self, tracker):
        """Food not in database should return error."""
        result = tracker.log_food("notfound item", quantity=100, unit="g")
        
        assert result["logged"] == False
        assert result["error"] == "FOOD_NOT_FOUND"
        assert "notfound item" in result["message"]

    def test_log_food_not_found_preserves_input(self, tracker):
        """Error response should include original input for retry."""
        result = tracker.log_food("notfound xyz", quantity=100, unit="g")
        
        assert result["logged"] == False
        assert result["name"] == "notfound xyz"
        assert result["quantity"] == 100
        assert result["unit"] == "g"

    def test_log_food_not_found_can_retry_with_manual(self, tracker):
        """After not found error, can retry with manual values."""
        # First attempt fails
        result1 = tracker.log_food("notfound item")
        assert result1["logged"] == False
        
        # Retry with manual values succeeds
        result2 = tracker.log_food(
            "notfound item",
            calories=100,
            protein_g=5,
            carbs_g=10,
            fat_g=2
        )
        assert "logged" not in result2 or result2.get("logged") != False
        assert result2["calories"] == 100
        assert result2["protein_g"] == 5
        assert result2["source"] == "manual"

    def test_search_food_returns_results(self, tracker):
        """Search should return nutrition info."""
        results = tracker.search_food("chicken")
        
        assert len(results) == 1
        assert results[0]["name"] == "Chicken"
        assert results[0]["calories"] == 150


class TestWaterTracking:
    """Tests for water logging."""

    def test_log_water_ml(self, tracker):
        """Water in ml should be stored directly."""
        result = tracker.log_water(500, "ml")
        assert result["amount_ml"] == 500

    def test_log_water_glasses(self, tracker):
        """Glasses should convert to ml (237ml each)."""
        result = tracker.log_water(2, "glasses")
        assert result["amount_ml"] == 474

    def test_log_water_liters(self, tracker):
        """Liters should convert to ml."""
        result = tracker.log_water(1.5, "liters")
        assert result["amount_ml"] == 1500

    def test_log_water_oz(self, tracker):
        """Ounces should convert to ml."""
        result = tracker.log_water(8, "oz")
        assert abs(result["amount_ml"] - 236.56) < 1

    def test_get_water_status(self, tracker):
        """Water status should show totals and progress."""
        tracker.log_water(1500, "ml")
        
        status = tracker.get_water_status()
        assert status["total_ml"] == 1500
        assert status["total_liters"] == 1.5
        assert "goal_ml" in status
        assert "progress_pct" in status


class TestDailySummary:
    """Tests for daily summary."""

    def test_summary_includes_all_sections(self, tracker):
        """Summary should have food, water, goals, progress."""
        tracker.log_food("test food")
        tracker.log_water(500, "ml")
        
        summary = tracker.get_daily_summary()
        
        assert "food" in summary
        assert "water" in summary
        assert "goals" in summary
        assert "progress" in summary
        assert "date" in summary

    def test_summary_calculates_progress(self, tracker):
        """Progress should be percentage of goal."""
        tracker.set_goal("calories", 1000)
        tracker.log_food("food", calories=500)
        
        summary = tracker.get_daily_summary()
        assert summary["progress"]["calories_pct"] == 50.0

    def test_empty_day_summary(self, tracker):
        """Empty day should have zero values."""
        summary = tracker.get_daily_summary()
        
        assert summary["food"]["calories"] == 0
        assert summary["food"]["entries"] == 0
        assert summary["water"]["total_ml"] == 0


class TestGoals:
    """Tests for goal management."""

    def test_set_goal(self, tracker):
        """Setting goal should persist."""
        tracker.set_goal("protein_g", 180)
        
        goals = tracker.get_goals()
        assert goals["protein_g"] == 180

    def test_get_goals_has_defaults(self, tracker):
        """Goals should have sensible defaults."""
        goals = tracker.get_goals()
        
        assert goals["water_ml"] > 0
        assert goals["protein_g"] > 0
        assert goals["calories"] > 0
