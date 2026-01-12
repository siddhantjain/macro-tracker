"""USDA FoodData Central nutrition provider."""
import os
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote
import json

from .base import NutritionProvider, NutritionInfo


def _load_dotenv():
    """Load .env file from project root if it exists."""
    # Walk up from this file to find .env
    current = Path(__file__).resolve().parent
    for _ in range(5):  # max 5 levels up
        env_file = current / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, _, value = line.partition("=")
                        os.environ.setdefault(key.strip(), value.strip())
            break
        current = current.parent


# Load .env on module import
_load_dotenv()


class PortionInfo:
    """Information about a food portion/measure."""
    
    def __init__(self, description: str, gram_weight: float, modifier: str = None):
        self.description = description  # e.g., "1 cup, cooked"
        self.gram_weight = gram_weight  # grams for this portion
        self.modifier = modifier        # USDA modifier code
    
    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "gram_weight": self.gram_weight,
        }
    
    def __repr__(self):
        return f"PortionInfo({self.description!r}, {self.gram_weight}g)"


class USDAProvider(NutritionProvider):
    """USDA FoodData Central API provider.
    
    Prioritizes Survey (FNDDS) data for better portion information.
    """

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    # Unit aliases for matching portions
    UNIT_ALIASES = {
        "cup": ["cup", "cups", "c"],
        "tbsp": ["tbsp", "tablespoon", "tablespoons", "tbs"],
        "tsp": ["tsp", "teaspoon", "teaspoons"],
        "oz": ["oz", "ounce", "ounces"],
        "fl oz": ["fl oz", "fluid ounce", "fluid ounces", "floz"],
        "g": ["g", "gram", "grams"],
        "lb": ["lb", "lbs", "pound", "pounds"],
        "slice": ["slice", "slices"],
        "piece": ["piece", "pieces", "pc", "pcs"],
        "serving": ["serving", "servings"],
        "bowl": ["bowl", "bowls"],
        "glass": ["glass", "glasses"],
        "bottle": ["bottle", "bottles"],
        "can": ["can", "cans"],
        "container": ["container", "containers"],
        "packet": ["packet", "packets", "pack", "packs"],
        "scoop": ["scoop", "scoops"],
        "large": ["large", "lg"],
        "medium": ["medium", "med"],
        "small": ["small", "sm"],
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("USDA_API_KEY", "DEMO_KEY")

    @property
    def name(self) -> str:
        return "USDA FoodData Central"

    def _request(self, endpoint: str, params: dict = None, method: str = "GET", body: dict = None) -> dict:
        """Make a request to the USDA API."""
        params = params or {}
        params["api_key"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}?{urlencode(params)}"
        
        headers = {"User-Agent": "MacroTracker/1.0"}
        data = None
        
        if method == "POST" and body:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        
        req = Request(url, headers=headers, data=data, method=method)
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())

    def _extract_nutrient(self, nutrients: list, nutrient_id: int) -> Optional[float]:
        """Extract a nutrient value by ID."""
        for n in nutrients:
            if n.get("nutrientId") == nutrient_id:
                return n.get("value")
        return None

    def _parse_portions(self, food: dict) -> List[PortionInfo]:
        """Parse portion information from a food item."""
        portions = []
        
        # Try foodMeasures (from search results)
        for measure in food.get("foodMeasures", []):
            desc = measure.get("disseminationText", "")
            gram_weight = measure.get("gramWeight")
            if desc and gram_weight and gram_weight > 0:
                portions.append(PortionInfo(
                    description=desc,
                    gram_weight=gram_weight,
                    modifier=measure.get("modifier")
                ))
        
        # Try foodPortions (from direct food lookup)
        for portion in food.get("foodPortions", []):
            desc = portion.get("portionDescription") or portion.get("modifier", "")
            gram_weight = portion.get("gramWeight")
            if desc and gram_weight and gram_weight > 0:
                # Try to build a better description
                amount = portion.get("amount", 1)
                if amount and amount != 1:
                    desc = f"{amount} {desc}"
                portions.append(PortionInfo(
                    description=desc,
                    gram_weight=gram_weight,
                    modifier=portion.get("modifier")
                ))
        
        return portions

    def _normalize_unit(self, unit: str) -> str:
        """Normalize a unit string for matching."""
        unit = unit.lower().strip()
        for canonical, aliases in self.UNIT_ALIASES.items():
            if unit in aliases:
                return canonical
        return unit

    def _match_portion(self, portions: List[PortionInfo], unit: str, quantity: float = 1) -> Optional[Dict[str, Any]]:
        """Find a portion that matches the given unit.
        
        Args:
            portions: List of available portions
            unit: Unit to match (e.g., "cup", "oz", "slice")
            quantity: Amount of the unit
            
        Returns:
            Dict with gram_weight and matched_portion, or None if no match
        """
        if not portions:
            return None
        
        unit_normalized = self._normalize_unit(unit)
        
        # Special case: if unit is grams, just use it directly
        if unit_normalized == "g":
            return {
                "gram_weight": quantity,
                "matched_portion": f"{quantity}g (direct)",
                "conversion": f"{quantity}g = {quantity}g"
            }
        
        # Try to match the unit in portion descriptions
        for portion in portions:
            desc_lower = portion.description.lower()
            
            # Check if the normalized unit appears in the description
            # e.g., "1 cup, cooked" contains "cup"
            if unit_normalized in desc_lower:
                # Found a match!
                # The portion's gram_weight is for the amount in the description (usually 1)
                # We multiply by quantity
                total_grams = portion.gram_weight * quantity
                return {
                    "gram_weight": total_grams,
                    "matched_portion": portion.description,
                    "conversion": f"{quantity} {unit} = {total_grams}g (based on {portion.description} = {portion.gram_weight}g)"
                }
            
            # Check aliases
            for canonical, aliases in self.UNIT_ALIASES.items():
                if unit_normalized == canonical:
                    for alias in aliases:
                        if alias in desc_lower:
                            total_grams = portion.gram_weight * quantity
                            return {
                                "gram_weight": total_grams,
                                "matched_portion": portion.description,
                                "conversion": f"{quantity} {unit} = {total_grams}g (based on {portion.description} = {portion.gram_weight}g)"
                            }
        
        # No match found
        return None

    def _parse_food(self, food: dict, include_portions: bool = True) -> NutritionInfo:
        """Parse a food item from the API response.
        
        Returns nutrition per 100g by default.
        """
        nutrients = food.get("foodNutrients", [])
        
        # USDA nutrient IDs
        # 1003 = Protein, 1004 = Fat, 1005 = Carbs, 1008 = Calories
        # 1079 = Fiber, 2000 = Sugar, 1093 = Sodium
        
        # Parse portions if available
        portions = self._parse_portions(food) if include_portions else []
        
        return NutritionInfo(
            name=food.get("description", "Unknown"),
            serving_size="100g",  # USDA always returns per 100g
            calories=self._extract_nutrient(nutrients, 1008) or 0,
            protein_g=self._extract_nutrient(nutrients, 1003) or 0,
            carbs_g=self._extract_nutrient(nutrients, 1005) or 0,
            fat_g=self._extract_nutrient(nutrients, 1004) or 0,
            fiber_g=self._extract_nutrient(nutrients, 1079),
            sugar_g=self._extract_nutrient(nutrients, 2000),
            sodium_mg=self._extract_nutrient(nutrients, 1093),
            source="usda",
            fdc_id=food.get("fdcId"),
            portions=[p.to_dict() for p in portions],
        )

    def search(self, query: str, limit: int = 5, data_types: List[str] = None) -> list[NutritionInfo]:
        """Search for foods matching the query.
        
        Args:
            query: Food search query
            limit: Maximum results to return
            data_types: USDA data types to search. Default prioritizes Survey (FNDDS)
                       for better portion data. Options:
                       - "Survey (FNDDS)" - best portions, common foods
                       - "SR Legacy" - comprehensive, good portions
                       - "Foundation" - raw ingredients
                       - "Branded" - packaged foods
        
        Returns:
            List of NutritionInfo with portion data included
        """
        # Default: prioritize FNDDS for better portion data
        if data_types is None:
            data_types = ["Survey (FNDDS)", "SR Legacy"]
        
        try:
            data = self._request(
                "foods/search",
                method="POST",
                body={
                    "query": query,
                    "pageSize": limit,
                    "dataType": data_types,
                    "requireAllWords": True,
                },
            )
            foods = data.get("foods", [])
            return [self._parse_food(f) for f in foods[:limit]]
        except Exception as e:
            print(f"USDA search error: {e}")
            return []

    def search_with_portions(self, query: str, unit: str, quantity: float = 1, limit: int = 3) -> Dict[str, Any]:
        """Search for a food and find matching portion.
        
        This is the main method for logging food with units.
        
        Args:
            query: Food search query
            unit: Unit to match (e.g., "cup", "oz", "slice")
            quantity: Amount of the unit
            limit: Maximum foods to search
            
        Returns:
            {
                "success": True/False,
                "food": NutritionInfo (if found),
                "portion_match": {...} (if unit matched),
                "gram_weight": float (total grams),
                "nutrition": {...} (scaled to actual grams),
                "available_portions": [...] (if no match),
                "error": str (if failed)
            }
        """
        results = self.search(query, limit=limit)
        
        if not results:
            return {
                "success": False,
                "error": "FOOD_NOT_FOUND",
                "message": f"Could not find '{query}' in USDA database.",
                "query": query,
            }
        
        # Try each result until we find one with a matching portion
        for food in results:
            portions = [PortionInfo(p["description"], p["gram_weight"]) for p in food.portions]
            match = self._match_portion(portions, unit, quantity)
            
            if match:
                # Calculate nutrition scaled to actual grams
                gram_weight = match["gram_weight"]
                scale = gram_weight / 100  # USDA is per 100g
                
                return {
                    "success": True,
                    "food": food,
                    "portion_match": match,
                    "gram_weight": gram_weight,
                    "nutrition": {
                        "calories": round(food.calories * scale, 1),
                        "protein_g": round(food.protein_g * scale, 1),
                        "carbs_g": round(food.carbs_g * scale, 1),
                        "fat_g": round(food.fat_g * scale, 1),
                        "fiber_g": round((food.fiber_g or 0) * scale, 1),
                    },
                    "conversion": match["conversion"],
                }
        
        # No portion match found - return available portions
        all_portions = []
        for food in results:
            for p in food.portions:
                if p not in all_portions:
                    all_portions.append(p)
        
        return {
            "success": False,
            "error": "PORTION_NOT_FOUND",
            "message": f"Could not convert '{unit}' for '{query}'. No matching portion found.",
            "query": query,
            "requested_unit": unit,
            "requested_quantity": quantity,
            "available_portions": all_portions[:10],  # Limit to top 10
            "suggestion": "Please use one of the available portions, or specify in grams (e.g., quantity=150, unit='g').",
        }

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
