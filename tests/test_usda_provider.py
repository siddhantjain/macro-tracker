"""Tests for USDA provider."""
import pytest
from unittest.mock import patch, Mock
import json

from src.providers.usda import USDAProvider


class TestUSDAProvider:
    """Tests for USDA FoodData Central provider."""

    @pytest.fixture
    def provider(self):
        return USDAProvider(api_key="test_key")

    def test_search_uses_require_all_words(self, provider):
        """Search should use requireAllWords=true to prevent fuzzy matches."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "foods": [{
                "fdcId": 123,
                "description": "Test Food",
                "foodNutrients": [
                    {"nutrientId": 1008, "value": 100},  # calories
                    {"nutrientId": 1003, "value": 10},   # protein
                    {"nutrientId": 1005, "value": 20},   # carbs
                    {"nutrientId": 1004, "value": 5},    # fat
                ]
            }]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch('src.providers.usda.urlopen', return_value=mock_response) as mock_urlopen:
            results = provider.search("test query")
            
            # Check that POST was used with correct body
            call_args = mock_urlopen.call_args
            request = call_args[0][0]
            
            assert request.method == "POST"
            body = json.loads(request.data.decode())
            assert body["requireAllWords"] == True
            assert body["query"] == "test query"

    def test_search_returns_empty_on_no_results(self, provider):
        """Search should return empty list when no foods found."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"foods": []}).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch('src.providers.usda.urlopen', return_value=mock_response):
            results = provider.search("xyznonexistent")
            assert results == []

    def test_search_parses_nutrients_correctly(self, provider):
        """Search should correctly parse nutrient values."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "foods": [{
                "fdcId": 456,
                "description": "Chicken Breast",
                "servingSize": 100,
                "foodNutrients": [
                    {"nutrientId": 1008, "value": 165},   # calories
                    {"nutrientId": 1003, "value": 31},    # protein
                    {"nutrientId": 1005, "value": 0},     # carbs
                    {"nutrientId": 1004, "value": 3.6},   # fat
                    {"nutrientId": 1079, "value": 0},     # fiber
                    {"nutrientId": 1093, "value": 74},    # sodium
                ]
            }]
        }).encode()
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch('src.providers.usda.urlopen', return_value=mock_response):
            results = provider.search("chicken breast")
            
            assert len(results) == 1
            food = results[0]
            assert food.name == "Chicken Breast"
            assert food.calories == 165
            assert food.protein_g == 31
            assert food.carbs_g == 0
            assert food.fat_g == 3.6
            assert food.sodium_mg == 74

    def test_search_handles_api_error_gracefully(self, provider):
        """Search should return empty list on API error."""
        with patch('src.providers.usda.urlopen', side_effect=Exception("API Error")):
            results = provider.search("anything")
            assert results == []
