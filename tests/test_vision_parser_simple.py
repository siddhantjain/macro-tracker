#!/usr/bin/env python3
"""Simple test for vision response parsing."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.vision_analyzer import VisionAnalyzer


def test_parse_simple():
    """Test basic vision parsing."""
    analyzer = VisionAnalyzer()
    
    text = """1. Scrambled eggs: 2 eggs
2. Toast: 2 slices
3. Orange juice: 1 cup"""
    
    items = analyzer._parse_vision_response(text)
    
    print(f"Parsed {len(items)} items:")
    for item in items:
        print(f"  - {item['name']}: {item['quantity']} {item['unit']}")
    
    assert len(items) == 3
    assert items[0]['name'] == 'Scrambled eggs'
    assert items[0]['quantity'] == 2
    assert items[0]['unit'] == 'eggs'
    
    assert items[1]['name'] == 'Toast'
    assert items[1]['quantity'] == 2
    assert items[1]['unit'] == 'slices'
    
    assert items[2]['name'] == 'Orange juice'
    assert items[2]['quantity'] == 1
    assert items[2]['unit'] == 'cups'
    
    print("\n✅ Test passed!")


if __name__ == '__main__':
    test_parse_simple()
