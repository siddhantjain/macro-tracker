#!/usr/bin/env python3
"""
Helper script for food image analysis using OpenClaw vision.
Neo will execute this script to analyze food images.

Usage: python analyze_food_image.py <image_path>
"""
import sys
import json

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No image path provided'}))
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    # This script is a placeholder - Neo will intercept execution and handle it
    # using the image tool, then return the response via stdout
    
    prompt = """Identify all food items in this photo and estimate quantities.

For EACH food item, provide:
1. Food name (be specific - e.g., "scrambled eggs" not just "eggs")
2. Estimated quantity as a number
3. Unit (grams/g, ounces/oz, cups, tablespoons/tbsp, pieces/items, slices, etc.)

Format your response as a numbered list:
1. [Food name]: [quantity] [unit]
2. [Food name]: [quantity] [unit]

Examples:
- Scrambled eggs: 2 eggs (or 100g if you can estimate weight)
- White rice: 150 g
- Grilled chicken breast: 200 g
- Toast: 2 slices
- Milk: 1 cup

Be as specific and accurate as possible with quantities. If you're unsure, provide your best estimate."""
    
    # Output the request that Neo will process
    print(json.dumps({
        'type': 'vision_request',
        'image': image_path,
        'prompt': prompt
    }))

if __name__ == '__main__':
    main()
