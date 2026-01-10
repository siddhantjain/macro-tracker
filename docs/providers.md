---
layout: default
title: Custom Providers
---

# Custom Nutrition Providers

Add your own nutrition data sources to Macro Tracker.

## Provider Interface

All providers must implement the `NutritionProvider` abstract class:

```python
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class NutritionInfo:
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

class NutritionProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for identification."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[NutritionInfo]:
        """Search for foods matching the query."""
        pass

    @abstractmethod
    def get_by_id(self, food_id: str) -> Optional[NutritionInfo]:
        """Get nutrition info by provider-specific ID."""
        pass
```

## Example: Custom Provider

Here's an example provider that uses a local CSV file:

```python
# src/providers/csv_provider.py
import csv
from pathlib import Path
from .base import NutritionProvider, NutritionInfo

class CSVProvider(NutritionProvider):
    """Load nutrition data from a local CSV file."""
    
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self._load_data()
    
    def _load_data(self):
        self.foods = []
        with open(self.csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.foods.append(NutritionInfo(
                    name=row['name'],
                    serving_size=row.get('serving', '100g'),
                    calories=float(row['calories']),
                    protein_g=float(row['protein']),
                    carbs_g=float(row['carbs']),
                    fat_g=float(row['fat']),
                    source='csv'
                ))
    
    @property
    def name(self) -> str:
        return "CSV Provider"
    
    def search(self, query: str, limit: int = 5) -> list[NutritionInfo]:
        query_lower = query.lower()
        matches = [f for f in self.foods if query_lower in f.name.lower()]
        return matches[:limit]
    
    def get_by_id(self, food_id: str) -> Optional[NutritionInfo]:
        # CSV doesn't have IDs, search by exact name
        for food in self.foods:
            if food.name == food_id:
                return food
        return None
```

## Using Custom Providers

### Option 1: Replace Default Provider

```python
from src.tracker import MacroTracker
from src.providers.csv_provider import CSVProvider

my_provider = CSVProvider("my_foods.csv")
tracker = MacroTracker(provider=my_provider)
```

### Option 2: Fallback Chain

Create a provider that tries multiple sources:

```python
class FallbackProvider(NutritionProvider):
    def __init__(self, providers: list[NutritionProvider]):
        self.providers = providers
    
    @property
    def name(self) -> str:
        return "Fallback"
    
    def search(self, query: str, limit: int = 5) -> list[NutritionInfo]:
        for provider in self.providers:
            results = provider.search(query, limit)
            if results:
                return results
        return []
    
    def get_by_id(self, food_id: str) -> Optional[NutritionInfo]:
        for provider in self.providers:
            result = provider.get_by_id(food_id)
            if result:
                return result
        return None

# Usage: Try local first, fall back to USDA
tracker = MacroTracker(provider=FallbackProvider([
    CSVProvider("my_foods.csv"),
    USDAProvider()
]))
```

## Provider Ideas

### Regional Databases

- **Indian Food DB** — IFCT (Indian Food Composition Tables)
- **UK Foods** — McCance and Widdowson's
- **Japanese Foods** — MEXT Standard Tables

### Barcode Lookup

```python
class BarcodeProvider(NutritionProvider):
    """Look up foods by barcode using OpenFoodFacts."""
    
    def search(self, query: str, limit: int = 5):
        # If query looks like a barcode, look it up
        if query.isdigit() and len(query) >= 8:
            return self._lookup_barcode(query)
        return []
    
    def _lookup_barcode(self, barcode: str):
        url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        # ... fetch and parse
```

### Restaurant Menus

```python
class RestaurantProvider(NutritionProvider):
    """Nutrition data for restaurant chains."""
    
    RESTAURANTS = {
        "chipotle": {...},
        "mcdonalds": {...},
    }
```

## Testing Providers

```python
def test_provider(provider: NutritionProvider):
    # Test search
    results = provider.search("chicken")
    assert len(results) > 0
    assert results[0].calories > 0
    assert results[0].protein_g > 0
    
    # Test edge cases
    empty = provider.search("xyznonexistent")
    assert empty == []
    
    print(f"✅ {provider.name} passed tests")

# Run tests
from src.providers.usda import USDAProvider
test_provider(USDAProvider())
```

## Contributing Providers

If you create a useful provider, consider contributing it:

1. Create `src/providers/your_provider.py`
2. Add tests
3. Document in this file
4. Submit a PR
