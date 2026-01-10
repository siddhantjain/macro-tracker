"""USDA FoodData Central nutrition provider."""
import os
from typing import Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
import json

from .base import NutritionProvider, NutritionInfo


class USDAProvider(NutritionProvider):
    """USDA FoodData Central API provider."""

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("USDA_API_KEY", "DEMO_KEY")

    @property
    def name(self) -> str:
        return "USDA FoodData Central"

    def _request(self, endpoint: str, params: dict = None) -> dict:
        """Make a request to the USDA API."""
        params = params or {}
        params["api_key"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}?{urlencode(params)}"
        
        req = Request(url, headers={"User-Agent": "MacroTracker/1.0"})
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())

    def _extract_nutrient(self, nutrients: list, nutrient_id: int) -> Optional[float]:
        """Extract a nutrient value by ID."""
        for n in nutrients:
            if n.get("nutrientId") == nutrient_id:
                return n.get("value")
        return None

    def _parse_food(self, food: dict) -> NutritionInfo:
        """Parse a food item from the API response."""
        nutrients = food.get("foodNutrients", [])
        
        # USDA nutrient IDs
        # 1003 = Protein, 1004 = Fat, 1005 = Carbs, 1008 = Calories
        # 1079 = Fiber, 2000 = Sugar, 1093 = Sodium
        
        return NutritionInfo(
            name=food.get("description", "Unknown"),
            serving_size=food.get("servingSize", "100g") if food.get("servingSize") else "100g",
            calories=self._extract_nutrient(nutrients, 1008) or 0,
            protein_g=self._extract_nutrient(nutrients, 1003) or 0,
            carbs_g=self._extract_nutrient(nutrients, 1005) or 0,
            fat_g=self._extract_nutrient(nutrients, 1004) or 0,
            fiber_g=self._extract_nutrient(nutrients, 1079),
            sugar_g=self._extract_nutrient(nutrients, 2000),
            sodium_mg=self._extract_nutrient(nutrients, 1093),
            source="usda",
            fdc_id=food.get("fdcId"),
        )

    def search(self, query: str, limit: int = 5) -> list[NutritionInfo]:
        """Search for foods matching the query."""
        try:
            data = self._request("foods/search", {
                "query": query,
                "pageSize": limit,
            })
            foods = data.get("foods", [])
            return [self._parse_food(f) for f in foods[:limit]]
        except Exception as e:
            print(f"USDA search error: {e}")
            return []

    def get_by_id(self, food_id: str) -> Optional[NutritionInfo]:
        """Get nutrition info by FDC ID."""
        try:
            data = self._request(f"food/{food_id}")
            return self._parse_food(data)
        except Exception as e:
            print(f"USDA get_by_id error: {e}")
            return None


# Default provider instance
default_provider = USDAProvider()
