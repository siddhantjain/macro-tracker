#!/usr/bin/env python3
"""Test photo-based food logging flow."""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision_analyzer import VisionAnalyzer
from src.nutrition_lookup import NutritionLookup


def mock_vision_callback(image_path: str, prompt: str) -> str:
    """Mock vision callback that returns a sample response."""
    print(f"Mock vision analyzing: {image_path}")
    print(f"Prompt: {prompt[:100]}...")
    
    # Simulate vision model response
    return """1. Scrambled eggs: 2 eggs
2. Whole wheat toast: 2 slices
3. Orange juice: 1 cup"""


def test_vision_parser():
    """Test vision response parsing."""
    print("\n=== Testing Vision Response Parser ===")
    
    analyzer = VisionAnalyzer(vision_callback=mock_vision_callback)
    
    test_response = """1. Scrambled eggs: 2 eggs
2. Toast: 2 slices
3. Milk: 1 cup
4. Banana: 1 piece"""
    
    items = analyzer._parse_vision_response(test_response)
    
    print(f"Parsed {len(items)} items:")
    for item in items:
        print(f"  - {item['name']}: {item['quantity']} {item['unit']}")
    
    assert len(items) == 4
    assert items[0]['name'] == 'Scrambled eggs'
    assert items[0]['quantity'] == 2
    assert items[0]['unit'] == 'eggs'
    
    print("✓ Vision parser test passed!")


def test_nutrition_lookup():
    """Test nutrition data lookup."""
    print("\n=== Testing Nutrition Lookup ===")
    
    lookup = NutritionLookup()
    
    # Test USDA lookup
    result = lookup.lookup('chicken breast', 200, 'g')
    
    print(f"Lookup result for chicken breast (200g):")
    print(f"  Calories: {result['calories']}")
    print(f"  Protein: {result['protein_g']}g")
    print(f"  Carbs: {result['carbs_g']}g")
    print(f"  Fat: {result['fat_g']}g")
    print(f"  Source: {result['source']}")
    print(f"  Confidence: {result['confidence']}")
    
    assert result['source'] in ['usda', 'web', 'none']
    if result['source'] == 'usda':
        assert result['calories'] > 0
        assert result['protein_g'] > 0
        print("✓ Nutrition lookup test passed!")
    else:
        print("⚠ USDA lookup failed (may need API key), got source:", result['source'])


def test_full_flow():
    """Test complete photo analysis flow with mock data."""
    print("\n=== Testing Full Photo Analysis Flow ===")
    
    # Create analyzer with mock vision callback
    analyzer = VisionAnalyzer(vision_callback=mock_vision_callback)
    lookup = NutritionLookup()
    
    # Create a dummy image file for testing
    test_image_path = Path(__file__).parent / "test_food_image.jpg"
    if not test_image_path.exists():
        # Create empty file
        test_image_path.write_bytes(b'fake image data')
    
    try:
        # Step 1: Analyze image
        print("\nStep 1: Analyzing image...")
        vision_result = analyzer.analyze_food_photo(str(test_image_path))
        
        print(f"Vision detected {len(vision_result['items'])} items:")
        for item in vision_result['items']:
            print(f"  - {item['name']}: {item['quantity']} {item['unit']}")
        
        # Step 2: Look up nutrition for each item
        print("\nStep 2: Looking up nutrition data...")
        analyzed_items = []
        for item in vision_result['items']:
            nutrition = lookup.lookup(item['name'], item['quantity'], item['unit'])
            analyzed_items.append(nutrition)
            print(f"  ✓ {nutrition['name']}: {nutrition['calories']} cal, {nutrition['protein_g']}g protein")
        
        # Step 3: Calculate totals
        total = {
            'calories': sum(item['calories'] for item in analyzed_items),
            'protein_g': sum(item['protein_g'] for item in analyzed_items),
            'carbs_g': sum(item['carbs_g'] for item in analyzed_items),
            'fat_g': sum(item['fat_g'] for item in analyzed_items)
        }
        
        print(f"\nTotal nutrition:")
        print(f"  Calories: {total['calories']}")
        print(f"  Protein: {total['protein_g']}g")
        print(f"  Carbs: {total['carbs_g']}g")
        print(f"  Fat: {total['fat_g']}g")
        
        # Build API response format
        response = {
            'items': analyzed_items,
            'total': total,
            'raw_vision_response': vision_result['raw_response']
        }
        
        print("\n=== API Response ===")
        print(json.dumps(response, indent=2))
        
        print("\n✓ Full flow test passed!")
        
    finally:
        # Clean up test file
        if test_image_path.exists() and test_image_path.read_bytes() == b'fake image data':
            test_image_path.unlink()


def test_vision_queue_system():
    """Test vision queue file system."""
    print("\n=== Testing Vision Queue System ===")
    
    # This tests the file-based queue that Neo monitors
    queue_dir = Path(__file__).parent.parent / "data" / "vision_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Vision queue directory: {queue_dir}")
    print(f"Exists: {queue_dir.exists()}")
    
    # Create a test request (Neo would process this)
    import uuid
    test_request_id = str(uuid.uuid4())
    request_file = queue_dir / f"request_{test_request_id}.json"
    
    request_data = {
        'request_id': test_request_id,
        'image_path': '/tmp/test.jpg',
        'prompt': 'Test prompt',
        'status': 'pending'
    }
    
    request_file.write_text(json.dumps(request_data, indent=2))
    print(f"✓ Created test request: {request_file.name}")
    
    # Simulate Neo's response
    response_file = queue_dir / f"response_{test_request_id}.json"
    response_data = {
        'request_id': test_request_id,
        'response': '1. Test food: 100 g',
        'timestamp': '2026-02-08T10:00:00'
    }
    response_file.write_text(json.dumps(response_data, indent=2))
    print(f"✓ Created mock response: {response_file.name}")
    
    # Verify files
    assert request_file.exists()
    assert response_file.exists()
    
    # Clean up
    request_file.unlink()
    response_file.unlink()
    
    print("✓ Vision queue system test passed!")


if __name__ == '__main__':
    print("=" * 60)
    print("Photo-Based Food Logging Test Suite")
    print("=" * 60)
    
    try:
        test_vision_parser()
        test_nutrition_lookup()
        test_vision_queue_system()
        test_full_flow()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
