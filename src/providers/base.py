"""Base interface for nutrition data providers."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class NutritionInfo:
    """Nutrition information for a food item.
    
    Nutrition values are per 100g by default (USDA standard).
    Use portions to convert to other units.
    """
    name: str
    serving_size: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    source: str = "unknown"
    fdc_id: Optional[int] = None  # USDA FoodData Central ID
    portions: Optional[list] = None  # Available portion conversions

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "serving_size": self.serving_size,
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "fiber_g": self.fiber_g,
            "sugar_g": self.sugar_g,
            "sodium_mg": self.sodium_mg,
            "source": self.source,
            "fdc_id": self.fdc_id,
            "portions": self.portions,
        }


class NutritionProvider(ABC):
    """Abstract base class for nutrition data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[NutritionInfo]:
        """Search for foods matching the query."""
        pass

    @abstractmethod
    def get_by_id(self, food_id: str) -> Optional[NutritionInfo]:
        """Get nutrition info by provider-specific ID."""
        pass
