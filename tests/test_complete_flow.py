#!/usr/bin/env python3
"""
Complete test of photo-based food logging API.

This test demonstrates the full flow:
1. Upload food photo
2. Neo analyzes image (simulated with mock)
3. Nutrition lookup for each item
4. Return structured response

For real usage, Neo would monitor the vision queue and process requests.
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision_analyzer import VisionAnalyzer
from src.nutrition_lookup import NutritionLookup


def mock_vision_callback(image_path: str, prompt: str) -> str:
    """
    Mock vision callback that simulates Neo's image analysis.
    
    In production, this would be replaced by actual OpenClaw API call
    or Neo monitoring the vision queue and using the image tool.
    """
    print(f"🔍 Analyzing image: {Path(image_path).name}")
    print(f"   Prompt: {prompt[:80]}...")
    
    # Simulate Neo's vision analysis of a typical breakfast
    # This is what Neo would return after analyzing the image
    mock_responses = {
        "breakfast": """1. Scrambled eggs: 2 eggs
2. Whole wheat toast: 2 slices
3. Orange juice: 1 cup
4. Bacon strips: 3 strips""",
        
        "lunch": """1. Grilled chicken breast: 200 g
2. White rice: 150 g
3. Steamed broccoli: 100 g
4. Mixed salad: 2 cups""",
        
        "dinner": """1. Salmon fillet: 250 g
2. Quinoa: 150 g
3. Roasted vegetables: 200 g""",
    }
    
    # Return a default breakfast response
    response = mock_responses["breakfast"]
    print(f"   Vision result: {response.replace(chr(10), ' | ')}")
    
    return response


def test_complete_flow():
    """Test the complete photo-based food logging flow."""
    print("=" * 70)
    print("🍽️  Photo-Based Food Logging - Complete Integration Test")
    print("=" * 70)
    
    # Initialize components with mock vision callback
    vision_analyzer = VisionAnalyzer(vision_callback=mock_vision_callback)
    nutrition_lookup = NutritionLookup()
    
    # Create a test image file
    test_image = Path(__file__).parent / "test_food_photo.jpg"
    if not test_image.exists():
        print(f"⚠️  Test image not found: {test_image}")
        print("   Creating placeholder...")
        test_image.write_bytes(b'placeholder image data')
    
    try:
        # Step 1: Vision Analysis
        print("\n📸 Step 1: Vision Analysis")
        print("-" * 50)
        vision_result = vision_analyzer.analyze_food_photo(str(test_image))
        
        print(f"Detected {len(vision_result['items'])} items:")
        for item in vision_result['items']:
            print(f"   • {item['name']}: {item['quantity']} {item['unit']}")
        
        # Step 2: Nutrition Lookup
        print("\n🥗 Step 2: Nutrition Lookup")
        print("-" * 50)
        
        analyzed_items = []
        for item in vision_result['items']:
            print(f"   Looking up: {item['name']}...")
            nutrition = nutrition_lookup.lookup(
                item['name'], 
                item['quantity'], 
                item['unit']
            )
            analyzed_items.append(nutrition)
            
            if nutrition.get('source') == 'usda':
                print(f"   ✓ USDA: {nutrition['name']} - {nutrition['calories']} cal, "
                      f"{nutrition['protein_g']}g protein")
            elif nutrition.get('source') == 'web':
                print(f"   ✓ Web: {nutrition['name']} - {nutrition['calories']} cal, "
                      f"{nutrition['protein_g']}g protein")
            else:
                print(f"   ⚠ No data: {nutrition['name']}")
        
        # Step 3: Calculate Totals
        print("\n📊 Step 3: Totals")
        print("-" * 50)
        
        total = {
            'calories': sum(item['calories'] for item in analyzed_items),
            'protein_g': sum(item['protein_g'] for item in analyzed_items),
            'carbs_g': sum(item['carbs_g'] for item in analyzed_items),
            'fat_g': sum(item['fat_g'] for item in analyzed_items)
        }
        
        print(f"Total Calories: {total['calories']}")
        print(f"Total Protein: {total['protein_g']}g")
        print(f"Total Carbs: {total['carbs_g']}g")
        print(f"Total Fat: {total['fat_g']}g")
        
        # Step 4: API Response Format
        print("\n📱 Step 4: API Response")
        print("-" * 50)
        
        response = {
            "items": analyzed_items,
            "total": total,
            "raw_vision_response": vision_result['raw_response']
        }
        
        print(json.dumps(response, indent=2))
        
        # Validate response format
        assert 'items' in response
        assert 'total' in response
        assert len(response['items']) > 0
        assert all(['name' in item for item in response['items']])
        assert all(['calories' in item for item in response['items']])
        assert all(['protein_g' in item for item in response['items']])
        
        print("\n✅ All validations passed!")
        print("\n🎉 Test completed successfully!")
        
        return response
        
    finally:
        # Clean up test image if we created it
        if test_image.exists() and test_image.read_bytes() == b'placeholder image data':
            test_image.unlink()


def test_usda_lookup_only():
    """Test USDA lookup without vision (for when USDA API is available)."""
    print("\n" + "=" * 70)
    print("🥗 Testing USDA Nutrition Lookup")
    print("=" * 70)
    
    lookup = NutritionLookup()
    
    test_foods = [
        ("chicken breast", 200, "g"),
        ("scrambled eggs", 2, "eggs"),
        ("white rice", 150, "g"),
        ("toast", 2, "slices"),
        ("orange juice", 1, "cup"),
    ]
    
    print("\nUSDA Food Lookup Test:")
    print("-" * 50)
    
    for food, qty, unit in test_foods:
        result = lookup.lookup(food, qty, unit)
        
        status = "✓" if result['source'] == 'usda' else "⚠"
        print(f"{status} {food} ({qty} {unit}):")
        print(f"   Calories: {result['calories']}, "
              f"Protein: {result['protein_g']}g, "
              f"Carbs: {result['carbs_g']}g, "
              f"Fat: {result['fat_g']}g")
        print(f"   Source: {result['source']}, Confidence: {result['confidence']}")


if __name__ == '__main__':
    # Run complete integration test
    try:
        response = test_complete_flow()
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Run USDA lookup test (if API key available)
    try:
        test_usda_lookup_only()
    except Exception as e:
        print(f"\n⚠️ USDA lookup test failed: {e}")
        print("   This is expected if USDA_API_KEY is not configured")
    
    print("\n" + "=" * 70)
    print("🎯 Next Steps:")
    print("=" * 70)
    print("""
1. Start macro-tracker server:
   cd ~/clawd/macro-tracker
   python3 -m src.server
   
2. Test API with curl:
   curl -X POST http://localhost:4001/api/food/analyze \\
     -F "image=@path/to/food_photo.jpg" \\
     | python3 -m json.tool
   
3. For real vision analysis:
   - Configure OpenClaw API URL in vision_analyzer.py
   - Or monitor vision queue: python3 scripts/process_vision_queue.py
   
4. Configure USDA API key for nutrition lookup:
   Set USDA_API_KEY environment variable
""")
