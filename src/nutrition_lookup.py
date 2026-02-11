#!/usr/bin/env python3
"""Nutrition data lookup service with USDA and web fallback."""
import re
from typing import Dict, Any, Optional
from .providers.usda import USDAProvider, default_provider

# Optional dependency for web search fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class NutritionLookup:
    """Look up nutrition data for food items."""
    
    def __init__(self, usda_provider=None, serper_api_key: Optional[str] = None):
        """Initialize nutrition lookup.
        
        Args:
            usda_provider: USDA provider instance (default: default_provider)
            serper_api_key: Serper API key for web search fallback
        """
        self.usda = usda_provider or default_provider
        self.serper_api_key = serper_api_key
        
    def lookup(self, food_name: str, quantity: float, unit: str) -> Dict[str, Any]:
        """Look up nutrition data for a food item.
        
        Strategy:
        1. Try USDA API first
        2. If not found or low confidence, try web search
        3. Return best available data
        
        Args:
            food_name: Name of the food item
            quantity: Quantity consumed
            unit: Unit of measurement
            
        Returns:
            Dict with:
            - name: Food name
            - quantity: Quantity
            - unit: Unit
            - calories: Total calories
            - protein_g: Total protein (grams)
            - carbs_g: Total carbs (grams)
            - fat_g: Total fat (grams)
            - source: 'usda' or 'web'
            - confidence: 'high', 'medium', or 'low'
        """
        # Try USDA first
        usda_result = self._lookup_usda(food_name, quantity, unit)
        if usda_result and usda_result['confidence'] == 'high':
            return usda_result
        
        # Fallback to web search
        web_result = self._lookup_web(food_name, quantity, unit)
        if web_result:
            return web_result
        
        # Return USDA result even if low confidence, or None
        return usda_result or {
            'name': food_name,
            'quantity': quantity,
            'unit': unit,
            'calories': 0,
            'protein_g': 0,
            'carbs_g': 0,
            'fat_g': 0,
            'source': 'none',
            'confidence': 'none',
            'error': 'No nutrition data found'
        }
    
    def _lookup_usda(self, food_name: str, quantity: float, unit: str) -> Optional[Dict[str, Any]]:
        """Look up food in USDA database.
        
        Returns:
            Nutrition data dict or None if not found
        """
        try:
            # Search for the food
            results = self.usda.search(food_name, limit=5)
            if not results:
                return None
            
            # Take the first result (most relevant)
            food = results[0]
            
            # Convert quantity to grams if needed
            quantity_g = self._convert_to_grams(quantity, unit, food)
            
            # Calculate nutrition per quantity
            # USDA data is per 100g
            multiplier = quantity_g / 100.0
            
            result = {
                'name': food.name,
                'quantity': quantity,
                'unit': unit,
                'quantity_g': quantity_g,
                'calories': round(food.calories * multiplier, 1),
                'protein_g': round(food.protein_g * multiplier, 1),
                'carbs_g': round(food.carbs_g * multiplier, 1),
                'fat_g': round(food.fat_g * multiplier, 1),
                'source': 'usda',
                'confidence': 'high',
                'usda_fdc_id': food.fdc_id
            }
            
            return result
            
        except Exception as e:
            print(f"USDA lookup failed for {food_name}: {e}")
            return None
    
    def _convert_to_grams(self, quantity: float, unit: str, food) -> float:
        """Convert quantity to grams using USDA portion data.
        
        Args:
            quantity: Quantity in the given unit
            unit: Unit of measurement
            food: USDA food object with portion data
            
        Returns:
            Quantity in grams
        """
        unit = unit.lower()
        
        # If already in grams, return as-is
        if unit in ['g', 'gram', 'grams']:
            return quantity
        
        # Try to find matching portion in USDA data
        if hasattr(food, 'portions') and food.portions:
            for portion in food.portions:
                portion_unit = portion.get('modifier', '').lower()
                # Match unit to portion (e.g., "cup" matches "cup", "egg" matches "large egg")
                if unit in portion_unit or portion_unit in unit:
                    gram_weight = portion.get('gram_weight', 0)
                    if gram_weight > 0:
                        return quantity * gram_weight
        
        # Default conversions if no USDA portion data
        # These are rough estimates
        conversions = {
            'oz': 28.35,
            'ounce': 28.35,
            'ounces': 28.35,
            'lb': 453.592,
            'pound': 453.592,
            'pounds': 453.592,
            'cup': 240,  # Approximate for liquids
            'cups': 240,
            'tbsp': 15,
            'tablespoon': 15,
            'tablespoons': 15,
            'tsp': 5,
            'teaspoon': 5,
            'teaspoons': 5,
            'ml': 1,  # For water/milk, 1ml ≈ 1g
            'pieces': 50,  # Very rough estimate
            'eggs': 50,  # Medium egg
            'egg': 50,
            'slices': 30,  # Bread slice
            'slice': 30,
        }
        
        if unit in conversions:
            return quantity * conversions[unit]
        
        # If we can't convert, assume it's already grams
        print(f"Warning: Unknown unit '{unit}', assuming grams")
        return quantity
    
    def _lookup_web(self, food_name: str, quantity: float, unit: str) -> Optional[Dict[str, Any]]:
        """Look up nutrition data via web search.
        
        Uses Serper API to search for nutrition facts, then parses the results.
        
        Returns:
            Nutrition data dict or None if not found
        """
        if not HAS_REQUESTS or not self.serper_api_key:
            return None
        
        try:
            # Search for nutrition facts
            query = f"{food_name} nutrition facts calories protein carbs fat per 100g"
            
            response = requests.post(
                'https://google.serper.dev/search',
                headers={
                    'X-API-KEY': self.serper_api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'q': query,
                    'gl': 'us',
                    'num': 5
                },
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            
            # Try to extract nutrition from featured snippet or knowledge graph
            nutrition = self._parse_search_results(data)
            if not nutrition:
                return None
            
            # Convert to requested quantity
            quantity_g = self._convert_to_grams(quantity, unit, None)
            multiplier = quantity_g / 100.0
            
            return {
                'name': food_name,
                'quantity': quantity,
                'unit': unit,
                'quantity_g': quantity_g,
                'calories': round(nutrition['calories'] * multiplier, 1),
                'protein_g': round(nutrition['protein_g'] * multiplier, 1),
                'carbs_g': round(nutrition['carbs_g'] * multiplier, 1),
                'fat_g': round(nutrition['fat_g'] * multiplier, 1),
                'source': 'web',
                'confidence': 'medium'
            }
            
        except Exception as e:
            print(f"Web lookup failed for {food_name}: {e}")
            return None
    
    def _parse_search_results(self, data: Dict) -> Optional[Dict[str, float]]:
        """Parse search results to extract nutrition data.
        
        Args:
            data: Serper API response
            
        Returns:
            Dict with calories, protein_g, carbs_g, fat_g per 100g or None
        """
        # Look in knowledge graph first
        if 'knowledgeGraph' in data:
            kg = data['knowledgeGraph']
            # Some knowledge graphs have nutrition info
            # This is highly variable, so we'd need to parse carefully
            # For now, skip this and look in snippets
        
        # Look in organic results snippets
        text = ""
        if 'organic' in data:
            for result in data['organic'][:3]:
                text += result.get('snippet', '') + " "
        
        # Try to extract numbers for calories, protein, carbs, fat
        # Look for patterns like "120 calories", "12g protein", etc.
        calories_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:cal|kcal|calories)', text, re.IGNORECASE)
        protein_match = re.search(r'(\d+(?:\.\d+)?)\s*g?\s*protein', text, re.IGNORECASE)
        carbs_match = re.search(r'(\d+(?:\.\d+)?)\s*g?\s*(?:carb|carbohydrate)', text, re.IGNORECASE)
        fat_match = re.search(r'(\d+(?:\.\d+)?)\s*g?\s*(?:fat|total fat)', text, re.IGNORECASE)
        
        if calories_match and protein_match:
            return {
                'calories': float(calories_match.group(1)),
                'protein_g': float(protein_match.group(1)),
                'carbs_g': float(carbs_match.group(1)) if carbs_match else 0,
                'fat_g': float(fat_match.group(1)) if fat_match else 0
            }
        
        return None


# Default lookup instance (requires Serper API key from env)
import os
default_lookup = NutritionLookup(serper_api_key=os.environ.get('SERPER_API_KEY'))
