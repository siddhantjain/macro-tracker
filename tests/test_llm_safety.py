"""Tests for LLM safety features - duplicate detection, dry run, etc."""
import pytest
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
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


class TestDuplicateDetection:
    """Tests for duplicate detection feature."""

    def test_duplicate_detected_within_window(self, tracker):
        """Same food logged twice within window should be detected."""
        # First log succeeds
        result1 = tracker.log_food("rice", quantity=2, calories=200, protein_g=5)
        assert result1.get("logged") == True
        
        # Second log within 5 minutes should be detected as duplicate
        result2 = tracker.log_food("rice", quantity=2, calories=200, protein_g=5)
        assert result2.get("logged") == False
        assert result2.get("reason") == "duplicate_detected"
        assert "existing_entry" in result2

    def test_duplicate_detection_case_insensitive(self, tracker):
        """Duplicate detection should be case-insensitive."""
        tracker.log_food("Rice", calories=200, protein_g=5)
        
        result = tracker.log_food("rice", calories=200, protein_g=5)
        assert result.get("reason") == "duplicate_detected"
        
        result = tracker.log_food("RICE", calories=200, protein_g=5)
        assert result.get("reason") == "duplicate_detected"

    def test_duplicate_detection_can_be_disabled(self, tracker):
        """Setting dedupe_window_minutes=0 should allow duplicates."""
        tracker.log_food("rice", calories=200, protein_g=5)
        
        # With dedupe disabled, second log should succeed
        result = tracker.log_food("rice", calories=200, protein_g=5, dedupe_window_minutes=0)
        assert result.get("logged") == True

    def test_different_foods_not_detected_as_duplicate(self, tracker):
        """Different food names should not trigger duplicate detection."""
        tracker.log_food("rice", calories=200, protein_g=5)
        
        result = tracker.log_food("chicken", calories=300, protein_g=30)
        assert result.get("logged") == True

    def test_duplicate_message_shows_time_ago(self, tracker):
        """Duplicate message should show how long ago original was logged."""
        tracker.log_food("rice", calories=200, protein_g=5)
        
        result = tracker.log_food("rice", calories=200, protein_g=5)
        assert "minutes ago" in result.get("message", "")

    def test_duplicate_returns_existing_entry(self, tracker):
        """Duplicate response should include the existing entry data."""
        original = tracker.log_food("rice", quantity=2, calories=200, protein_g=5)
        
        result = tracker.log_food("rice", calories=200, protein_g=5)
        assert result["existing_entry"]["quantity"] == 2
        assert result["existing_entry"]["calories"] == 200


class TestDryRunMode:
    """Tests for dry run mode."""

    def test_dry_run_returns_preview(self, tracker):
        """Dry run should return what would be logged."""
        result = tracker.log_food("chicken", quantity=2, dry_run=True)
        
        assert result.get("dry_run") == True
        assert "would_log" in result
        assert result["would_log"]["name"] == "chicken"
        assert result["would_log"]["quantity"] == 2

    def test_dry_run_does_not_save(self, tracker):
        """Dry run should not persist any data."""
        tracker.log_food("chicken", quantity=2, dry_run=True)
        
        # Food log should be empty
        log = tracker.get_food_log()
        assert len(log) == 0

    def test_dry_run_with_manual_values(self, tracker):
        """Dry run should work with manual nutrition values."""
        result = tracker.log_food(
            "homemade soup",
            calories=350,
            protein_g=20,
            carbs_g=30,
            fat_g=10,
            dry_run=True
        )
        
        assert result["would_log"]["calories"] == 350
        assert result["would_log"]["protein_g"] == 20
        assert result["would_log"]["source"] == "manual"

    def test_dry_run_skips_duplicate_check(self, tracker):
        """Dry run should work even if same food exists."""
        tracker.log_food("rice", calories=200, protein_g=5)
        
        # Dry run should show preview, not duplicate error
        result = tracker.log_food("rice", calories=200, protein_g=5, dry_run=True)
        assert result.get("dry_run") == True
        assert "would_log" in result


class TestRecentEntries:
    """Tests for recent_entries helper."""

    def test_recent_entries_returns_only_recent(self, tracker):
        """Should only return entries within the time window."""
        tracker.log_food("food1", calories=100, protein_g=5)
        
        recent = tracker.recent_entries(minutes=10)
        assert len(recent) == 1
        assert recent[0]["name"] == "food1"

    def test_recent_entries_empty_when_no_logs(self, tracker):
        """Should return empty list when nothing logged."""
        recent = tracker.recent_entries(minutes=10)
        assert recent == []

    def test_recent_entries_multiple_items(self, tracker):
        """Should return all recent items."""
        tracker.log_food("food1", calories=100, protein_g=5, dedupe_window_minutes=0)
        tracker.log_food("food2", calories=200, protein_g=10, dedupe_window_minutes=0)
        tracker.log_food("food3", calories=300, protein_g=15, dedupe_window_minutes=0)
        
        recent = tracker.recent_entries(minutes=10)
        assert len(recent) == 3


class TestDeleteEntry:
    """Tests for delete_entry functionality."""

    def test_delete_entry_success(self, tracker):
        """Should delete entry by timestamp."""
        result = tracker.log_food("rice", calories=200, protein_g=5)
        timestamp = result["timestamp"]
        
        delete_result = tracker.delete_entry(timestamp)
        assert delete_result["deleted"] == True
        assert delete_result["entry"]["name"] == "rice"
        
        # Verify it's gone
        log = tracker.get_food_log()
        assert len(log) == 0

    def test_delete_entry_not_found(self, tracker):
        """Should handle non-existent timestamp gracefully."""
        result = tracker.delete_entry("2026-01-01T00:00:00.000000")
        
        assert result["deleted"] == False
        assert result["reason"] == "not_found"

    def test_delete_entry_invalid_timestamp(self, tracker):
        """Should handle invalid timestamp format."""
        result = tracker.delete_entry("not-a-timestamp")
        
        assert result["deleted"] == False
        assert result["reason"] == "invalid_timestamp"

    def test_delete_entries_multiple(self, tracker):
        """Should delete multiple entries."""
        r1 = tracker.log_food("food1", calories=100, protein_g=5, dedupe_window_minutes=0)
        r2 = tracker.log_food("food2", calories=200, protein_g=10, dedupe_window_minutes=0)
        r3 = tracker.log_food("food3", calories=300, protein_g=15, dedupe_window_minutes=0)
        
        result = tracker.delete_entries([r1["timestamp"], r2["timestamp"]])
        
        assert result["deleted_count"] == 2
        assert len(result["not_found"]) == 0
        
        # Only food3 should remain
        log = tracker.get_food_log()
        assert len(log) == 1
        assert log[0]["name"] == "food3"

    def test_delete_entries_partial_success(self, tracker):
        """Should report which timestamps were not found."""
        r1 = tracker.log_food("food1", calories=100, protein_g=5)
        
        result = tracker.delete_entries([
            r1["timestamp"],
            "2026-01-01T00:00:00.000000"  # Non-existent
        ])
        
        assert result["deleted_count"] == 1
        assert len(result["not_found"]) == 1
        assert result["success"] == False


class TestLogMeal:
    """Tests for batch meal logging."""

    def test_log_meal_success(self, tracker):
        """Should log multiple items and return totals."""
        result = tracker.log_meal([
            {"name": "rice", "quantity": 2, "calories": 200, "protein_g": 5, "carbs_g": 40, "fat_g": 1},
            {"name": "dal", "quantity": 1, "calories": 150, "protein_g": 10, "carbs_g": 20, "fat_g": 3},
        ], meal_name="lunch")
        
        assert result["success"] == True
        assert result["items_logged"] == 2
        assert result["meal_name"] == "lunch"
        assert result["total"]["calories"] == 350
        assert result["total"]["protein_g"] == 15

    def test_log_meal_with_duplicate_detection(self, tracker):
        """Should skip duplicates within meal."""
        # Pre-log rice
        tracker.log_food("rice", calories=200, protein_g=5)
        
        # Meal that includes rice again
        result = tracker.log_meal([
            {"name": "rice", "calories": 200, "protein_g": 5},
            {"name": "dal", "calories": 150, "protein_g": 10},
        ])
        
        assert result["items_logged"] == 1  # Only dal
        assert result["items_skipped_duplicate"] == 1
        assert "skipped_duplicates" in result

    def test_log_meal_dry_run(self, tracker):
        """Dry run should preview meal without saving."""
        result = tracker.log_meal([
            {"name": "rice", "calories": 200, "protein_g": 5},
            {"name": "dal", "calories": 150, "protein_g": 10},
        ], dry_run=True)
        
        assert result["dry_run"] == True
        assert result["total"]["calories"] == 350
        
        # Nothing should be saved
        log = tracker.get_food_log()
        assert len(log) == 0

    def test_log_meal_with_errors(self, tracker):
        """Should report items that failed to log."""
        result = tracker.log_meal([
            {"name": "rice", "calories": 200, "protein_g": 5},
            {"name": "notfound item"},  # No manual calories, will fail
        ])
        
        assert result["success"] == False
        assert result["items_logged"] == 1
        assert result["items_failed"] == 1
        assert "errors" in result

    def test_log_meal_dedupe_disabled(self, tracker):
        """Should allow duplicates when dedupe disabled."""
        tracker.log_food("rice", calories=200, protein_g=5)
        
        result = tracker.log_meal([
            {"name": "rice", "calories": 200, "protein_g": 5},
        ], dedupe_window_minutes=0)
        
        assert result["items_logged"] == 1
        assert result["items_skipped_duplicate"] == 0


class TestIntegration:
    """Integration tests for LLM retry patterns."""

    def test_safe_retry_pattern(self, tracker):
        """Demonstrate safe retry pattern for LLMs."""
        # First attempt - some items fail
        result1 = tracker.log_meal([
            {"name": "rice", "calories": 200, "protein_g": 5},
            {"name": "notfound item"},  # Will fail
        ])
        
        assert result1["items_logged"] == 1
        assert result1["items_failed"] == 1
        
        # Retry only failed items with manual values
        # Rice should be detected as duplicate
        result2 = tracker.log_meal([
            {"name": "rice", "calories": 200, "protein_g": 5},  # Should skip
            {"name": "notfound item", "calories": 100, "protein_g": 5},  # Manual values
        ])
        
        assert result2["items_logged"] == 1  # Only the previously failed item
        assert result2["items_skipped_duplicate"] == 1  # Rice skipped

    def test_check_before_retry(self, tracker):
        """Demonstrate checking recent entries before retry."""
        tracker.log_food("rice", calories=200, protein_g=5)
        
        # Check what's already logged
        recent = tracker.recent_entries(minutes=5)
        logged_names = {e['name'].lower() for e in recent}
        
        # Only log items not already in recent
        items_to_log = []
        for item in [{"name": "rice", "calories": 200}, {"name": "dal", "calories": 150}]:
            if item["name"].lower() not in logged_names:
                items_to_log.append(item)
        
        assert len(items_to_log) == 1
        assert items_to_log[0]["name"] == "dal"

    def test_cleanup_after_mistake(self, tracker):
        """Demonstrate cleanup workflow after duplicate logging."""
        # Accidentally log same thing multiple times (with dedupe disabled)
        r1 = tracker.log_food("rice", calories=200, protein_g=5, dedupe_window_minutes=0)
        r2 = tracker.log_food("rice", calories=200, protein_g=5, dedupe_window_minutes=0)
        r3 = tracker.log_food("rice", calories=200, protein_g=5, dedupe_window_minutes=0)
        
        # Find duplicates
        recent = tracker.recent_entries(minutes=5)
        assert len(recent) == 3
        
        # Delete extras (keep only the first)
        to_delete = [r2["timestamp"], r3["timestamp"]]
        result = tracker.delete_entries(to_delete)
        
        assert result["deleted_count"] == 2
        
        # Verify only one remains
        log = tracker.get_food_log()
        assert len(log) == 1
