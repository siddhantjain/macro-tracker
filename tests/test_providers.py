"""Tests for nutrition providers."""
import pytest
from unittest.mock import patch, Mock
import json

from src.providers.base import NutritionProvider, NutritionInfo
from src.providers.usda import USDAProvider


class TestNutritionInfo:
    """Tests for the NutritionInfo dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        info = NutritionInfo(
            name="Test Food",
            serving_size="100g",
            calories=200,
            protein_g=15,
            carbs_g=20,
            fat_g=10,
            fiber_g=5,
            source="test",
        )
        
        d = info.to_dict()
        assert d["name"] == "Test Food"
        assert d["calories"] == 200
        assert d["protein_g"] == 15
        assert d["source"] == "test"

    def test_optional_fields_default_none(self):
        """Optional fields should default to None."""
        info = NutritionInfo(
            name="Minimal",
            serving_size="100g",
            calories=100,
            protein_g=5,
            carbs_g=10,
            fat_g=3,
        )
        
        assert info.fiber_g is None
        assert info.sugar_g is None
        assert info.sodium_mg is None


class TestUSDAProvider:
    """Tests for the USDA provider."""

    @pytest.fixture
    def provider(self):
        return USDAProvider(api_key="TEST_KEY")

    def test_provider_name(self, provider):
        """Provider should have correct name."""
        assert provider.name == "USDA FoodData Central"

    @patch('src.providers.usda.urlopen')
    def test_search_parses_response(self, mock_urlopen, provider):
        """Search should parse USDA API response correctly."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "foods": [
                {
                    "fdcId": 12345,
                    "description": "Chicken, breast, raw",
                    "foodNutrients": [
                        {"nutrientId": 1008, "value": 165},  # Calories
                        {"nutrientId": 1003, "value": 31},   # Protein
                        {"nutrientId": 1005, "value": 0},    # Carbs
                        {"nutrientId": 1004, "value": 3.6},  # Fat
                    ]
                }
            ]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        results = provider.search("chicken breast", limit=1)
        
        assert len(results) == 1
        assert results[0].name == "Chicken, breast, raw"
        assert results[0].calories == 165
        assert results[0].protein_g == 31
        assert results[0].fdc_id == 12345

    @patch('src.providers.usda.urlopen')
    def test_search_handles_empty_results(self, mock_urlopen, provider):
        """Search should handle empty results."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"foods": []}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        results = provider.search("xyznonexistent")
        assert results == []

    @patch('src.providers.usda.urlopen')
    def test_search_handles_api_error(self, mock_urlopen, provider):
        """Search should handle API errors gracefully."""
        mock_urlopen.side_effect = Exception("API Error")
        
        results = provider.search("chicken")
        assert results == []

    def test_extract_nutrient_missing(self, provider):
        """Should return None for missing nutrients."""
        nutrients = [{"nutrientId": 1003, "value": 10}]
        
        result = provider._extract_nutrient(nutrients, 9999)
        assert result is None

    def test_extract_nutrient_present(self, provider):
        """Should extract nutrient value correctly."""
        nutrients = [
            {"nutrientId": 1003, "value": 25},
            {"nutrientId": 1008, "value": 200},
        ]
        
        protein = provider._extract_nutrient(nutrients, 1003)
        calories = provider._extract_nutrient(nutrients, 1008)
        
        assert protein == 25
        assert calories == 200
