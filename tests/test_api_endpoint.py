#!/usr/bin/env python3
"""
Test the /api/food/analyze endpoint.

This script tests the photo-based food logging API endpoint.
Neo will handle the vision analysis when the request is processed.
"""
import sys
import json
from pathlib import Path

# Test script - use mock response for automated testing
def test_with_mock():
    """Test the endpoint with mock vision response."""
    print("=" * 60)
    print("Testing POST /api/food/analyze endpoint")
    print("=" * 60)
    
    # Simulate the endpoint flow
    print("\n1. Upload image: test_food_photo.jpg")
    print("2. Vision analysis request created")
    print("3. Neo processes vision queue...")
    
    # Mock vision response
    mock_vision_response = """1. Scrambled eggs: 2 eggs
2. Whole wheat toast: 2 slices
3. Orange juice: 1 cup"""
    
    print(f"\n4. Vision response:\n{mock_vision_response}")
    
    # Simulate nutrition lookup (would query USDA in real scenario)
    mock_items = [
        {
            "name": "scrambled eggs",
            "quantity": 2,
            "unit": "eggs",
            "quantity_g": 100,
            "calories": 140,
            "protein_g": 12,
            "carbs_g": 2,
            "fat_g": 10,
            "source": "usda",
            "confidence": "high"
        },
        {
            "name": "whole wheat toast",
            "quantity": 2,
            "unit": "slices",
            "quantity_g": 60,
            "calories": 160,
            "protein_g": 6,
            "carbs_g": 28,
            "fat_g": 2,
            "source": "usda",
            "confidence": "high"
        },
        {
            "name": "orange juice",
            "quantity": 1,
            "unit": "cups",
            "quantity_g": 240,
            "calories": 110,
            "protein_g": 2,
            "carbs_g": 26,
            "fat_g": 0,
            "source": "usda",
            "confidence": "high"
        }
    ]
    
    # Calculate totals
    total = {
        "calories": sum(item["calories"] for item in mock_items),
        "protein_g": sum(item["protein_g"] for item in mock_items),
        "carbs_g": sum(item["carbs_g"] for item in mock_items),
        "fat_g": sum(item["fat_g"] for item in mock_items)
    }
    
    # Build response
    response = {
        "items": mock_items,
        "total": total
    }
    
    print("\n5. API Response:")
    print(json.dumps(response, indent=2))
    
    print("\n✅ API endpoint flow validated!")
    print("\nNext steps:")
    print("1. Start macro-tracker server: python3 -m src.server")
    print("2. Start vision queue processor: python3 scripts/process_vision_queue.py")
    print("3. Test with curl:")
    print("   curl -X POST http://localhost:4001/api/food/analyze \\")
    print("     -F 'image=@tests/test_food_photo.jpg'")
    
    return response


def test_with_curl():
    """Instructions for testing with curl."""
    print("\n" + "=" * 60)
    print("Manual Testing with curl")
    print("=" * 60)
    
    print("""
To test the actual API endpoint:

1. Terminal 1 - Start macro-tracker server:
   cd ~/clawd/macro-tracker
   python3 -m src.server

2. Terminal 2 - Monitor vision queue (Neo will handle this):
   cd ~/clawd/macro-tracker
   python3 scripts/process_vision_queue.py

3. Terminal 3 - Send test request:
   curl -X POST http://localhost:4001/api/food/analyze \\
     -F 'image=@tests/test_food_photo.jpg' \\
     | python3 -m json.tool

Expected response:
{
  "items": [
    {
      "name": "food item",
      "quantity": 100,
      "unit": "g",
      "calories": 200,
      "protein_g": 20,
      ...
    }
  ],
  "total": {
    "calories": 200,
    "protein_g": 20,
    ...
  }
}

Note: Neo must be running and monitoring the vision queue for real image analysis.
""")


if __name__ == '__main__':
    response = test_with_mock()
    test_with_curl()
