"""Tests for the JSON storage module."""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import date, timedelta

from src.storage.json_store import JsonStore, FoodEntry, WaterEntry


@pytest.fixture
def temp_store():
    """Create a temporary store for testing."""
    temp_dir = tempfile.mkdtemp()
    store = JsonStore(data_dir=temp_dir)
    yield store
    shutil.rmtree(temp_dir)


class TestFoodStorage:
    """Tests for food logging and retrieval."""

    def test_log_food_creates_entry(self, temp_store):
        """Logging food should create an entry with all fields."""
        entry = FoodEntry(
            timestamp="2026-01-10T12:00:00",
            name="Test Food",
            quantity=2,
            unit="serving",
            calories=200,
            protein_g=10,
            carbs_g=20,
            fat_g=5,
            source="test",
        )
        result = temp_store.log_food(entry)
        
        assert result["name"] == "Test Food"
        assert result["calories"] == 200
        assert result["protein_g"] == 10

    def test_get_food_log_returns_entries(self, temp_store):
        """Should retrieve logged entries for a day."""
        entry = FoodEntry(
            timestamp="2026-01-10T12:00:00",
            name="Test Food",
            quantity=1,
            unit="serving",
            calories=100,
            protein_g=5,
            carbs_g=10,
            fat_g=2,
        )
        temp_store.log_food(entry)
        
        log = temp_store.get_food_log()
        assert len(log) == 1
        assert log[0]["name"] == "Test Food"

    def test_get_daily_macros_sums_correctly(self, temp_store):
        """Daily macros should sum all entries."""
        for i in range(3):
            entry = FoodEntry(
                timestamp=f"2026-01-10T{12+i}:00:00",
                name=f"Food {i}",
                quantity=1,
                unit="serving",
                calories=100,
                protein_g=10,
                carbs_g=20,
                fat_g=5,
            )
            temp_store.log_food(entry)
        
        macros = temp_store.get_daily_macros()
        assert macros["calories"] == 300
        assert macros["protein_g"] == 30
        assert macros["carbs_g"] == 60
        assert macros["fat_g"] == 15
        assert macros["entries"] == 3

    def test_empty_day_returns_zeros(self, temp_store):
        """Empty day should return zero totals."""
        macros = temp_store.get_daily_macros()
        assert macros["calories"] == 0
        assert macros["protein_g"] == 0
        assert macros["entries"] == 0


class TestWaterStorage:
    """Tests for water logging and retrieval."""

    def test_log_water_creates_entry(self, temp_store):
        """Logging water should create an entry."""
        result = temp_store.log_water(500)
        
        assert result["amount_ml"] == 500
        assert "timestamp" in result

    def test_get_daily_water_sums_correctly(self, temp_store):
        """Daily water should sum all entries."""
        temp_store.log_water(250)
        temp_store.log_water(500)
        temp_store.log_water(250)
        
        water = temp_store.get_daily_water()
        assert water["total_ml"] == 1000
        assert water["total_liters"] == 1.0
        assert water["entries"] == 3

    def test_glasses_calculation(self, temp_store):
        """Glasses should be calculated from ml (237ml = 1 glass)."""
        temp_store.log_water(474)  # 2 glasses
        
        water = temp_store.get_daily_water()
        assert water["glasses"] == 2.0


class TestGoals:
    """Tests for goal management."""

    def test_default_goals_exist(self, temp_store):
        """Should have sensible default goals."""
        goals = temp_store.get_goals()
        
        assert "water_ml" in goals
        assert "protein_g" in goals
        assert "calories" in goals

    def test_set_goal_updates_value(self, temp_store):
        """Setting a goal should persist it."""
        temp_store.set_goal("protein_g", 180)
        
        goals = temp_store.get_goals()
        assert goals["protein_g"] == 180

    def test_set_goal_preserves_others(self, temp_store):
        """Setting one goal shouldn't affect others."""
        # Set initial goals
        temp_store.set_goal("water_ml", 3000)
        temp_store.set_goal("calories", 2000)
        
        original = temp_store.get_goals()
        temp_store.set_goal("protein_g", 200)
        
        goals = temp_store.get_goals()
        assert goals["water_ml"] == original["water_ml"]
        assert goals["calories"] == original["calories"]


class TestDateHandling:
    """Tests for multi-day storage."""

    def test_different_days_separate(self, temp_store):
        """Different days should have separate logs."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Log to today
        entry = FoodEntry(
            timestamp="2026-01-10T12:00:00",
            name="Today Food",
            quantity=1,
            unit="serving",
            calories=100,
            protein_g=10,
            carbs_g=10,
            fat_g=5,
        )
        temp_store.log_food(entry)
        
        # Yesterday should be empty
        log = temp_store.get_food_log(yesterday)
        assert len(log) == 0
        
        # Today should have the entry
        log = temp_store.get_food_log(today)
        assert len(log) == 1
