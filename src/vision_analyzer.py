#!/usr/bin/env python3
"""OpenClaw vision integration for food photo analysis."""
import json
import re
import time
import uuid
import base64
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Optional requests for API calls
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class VisionAnalyzer:
    """Analyzes food photos using OpenClaw vision API."""
    
    def __init__(self, openclaw_url: str = "http://localhost:4000", vision_callback=None):
        """Initialize the vision analyzer.
        
        Args:
            openclaw_url: Base URL for OpenClaw gateway API
            vision_callback: Optional callback for testing (bypasses API)
        """
        self.openclaw_url = openclaw_url.rstrip('/')
        self.vision_callback = vision_callback
        
    def analyze_food_photo(self, image_path: str) -> Dict[str, Any]:
        """Analyze a food photo to identify items and quantities.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dict with 'items' list, each containing:
            - name: Food item name
            - quantity: Estimated quantity (numeric)
            - unit: Unit of measurement (g, oz, pieces, etc.)
            - raw_description: Original vision response for this item
            
        Raises:
            Exception: If vision analysis fails
        """
        # Prepare the prompt for food identification
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

        try:
            # Use callback if provided (for testing)
            if self.vision_callback:
                vision_text = self.vision_callback(image_path, prompt)
            elif HAS_REQUESTS:
                # Try to call OpenClaw sessions API
                try:
                    vision_text = self._call_openclaw_api(image_path, prompt)
                except Exception as api_error:
                    print(f"OpenClaw API call failed: {api_error}, using file queue")
                    # Fallback to file-based queue
                    vision_text = self._request_vision_analysis(image_path, prompt)
            else:
                # No requests library, use file queue
                vision_text = self._request_vision_analysis(image_path, prompt)
            
            if not vision_text:
                raise Exception("Empty response from vision analysis")
            
            # Parse the vision response
            items = self._parse_vision_response(vision_text)
            
            return {
                'items': items,
                'raw_response': vision_text
            }
            
        except Exception as e:
            raise Exception(f"Vision analysis failed: {e}")
    
    def _call_openclaw_api(self, image_path: str, prompt: str, timeout: int = 30) -> str:
        """Call OpenClaw sessions API for vision analysis.
        
        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            timeout: Request timeout in seconds
            
        Returns:
            Vision analysis text response
            
        Raises:
            Exception: If API call fails
        """
        # Read and encode image as base64
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Prepare the request payload
        payload = {
            "image": image_data,
            "prompt": prompt
        }
        
        # Try different API endpoints
        endpoints = [
            f"{self.openclaw_url}/api/v1/tools/image",
            f"{self.openclaw_url}/api/v1/analyze",
            f"{self.openclaw_url}/api/vision/analyze",
        ]
        
        last_error = None
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    },
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Try different response formats
                    if 'response' in result:
                        return result['response']
                    elif 'text' in result:
                        return result['text']
                    elif 'analysis' in result:
                        return result['analysis']
                    elif isinstance(result, str):
                        return result
                    else:
                        # Try to extract from whatever structure
                        return str(result)
                elif response.status_code == 405:
                    # Method not allowed, try next endpoint
                    continue
                else:
                    # Other error, try next endpoint
                    continue
                    
            except requests.exceptions.RequestException as e:
                last_error = e
                continue
        
        # All endpoints failed, raise exception
        raise Exception(f"OpenClaw API not accessible: {last_error or 'all endpoints returned 405'}")
    
    def _request_vision_analysis(self, image_path: str, prompt: str, timeout: int = 60) -> str:
        """Request vision analysis via queue file system (fallback).
        
        Args:
            image_path: Path to image file
            prompt: Analysis prompt
            timeout: Max seconds to wait for response
            
        Returns:
            Vision analysis text response
        """
        # Create queue directory if needed
        queue_dir = Path(__file__).parent.parent / "data" / "vision_queue"
        queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique request ID
        request_id = str(uuid.uuid4())
        request_file = queue_dir / f"request_{request_id}.json"
        response_file = queue_dir / f"response_{request_id}.json"
        
        # Write request
        request_data = {
            'request_id': request_id,
            'image_path': str(Path(image_path).absolute()),
            'prompt': prompt,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        request_file.write_text(json.dumps(request_data, indent=2))
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            if response_file.exists():
                try:
                    response_data = json.loads(response_file.read_text())
                    vision_text = response_data.get('response', '')
                    
                    # Clean up files
                    try:
                        request_file.unlink()
                        response_file.unlink()
                    except:
                        pass
                    
                    return vision_text
                except json.JSONDecodeError:
                    # Response file not fully written yet
                    pass
            
            time.sleep(0.5)
        
        # Timeout - clean up request file
        try:
            if request_file.exists():
                request_file.unlink()
        except:
            pass
        
        raise Exception(f"Vision analysis timeout after {timeout} seconds")
    
    def _parse_vision_response(self, text: str) -> List[Dict[str, Any]]:
        """Parse the vision model's response into structured food items.
        
        Args:
            text: Raw text response from vision model
            
        Returns:
            List of food items with name, quantity, and unit
        """
        items = []
        
        # Try to parse numbered list format: "1. Food name: quantity unit"
        # Pattern: optional number/bullet, food name, colon, quantity, unit
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remove leading numbering/bullets: "1.", "1)", "-", "*", "•"
            line = re.sub(r'^[\d\.\)•\-\*]+\s*', '', line)
            
            # Try to match: "Food name: quantity unit" or "Food name - quantity unit"
            match = re.match(r'^([^:\-]+)[\:\-]\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', line, re.IGNORECASE)
            
            if match:
                name = match.group(1).strip()
                quantity = float(match.group(2))
                unit = match.group(3).lower()
                
                # Check if the food name incorrectly includes a number (e.g., "5 roti")
                # This indicates the AI put the quantity in the wrong place
                name_with_num = re.match(r'^(\d+)\s+(.+)$', name)
                if name_with_num:
                    # Extract the actual quantity from the name
                    actual_quantity = float(name_with_num.group(1))
                    actual_name = name_with_num.group(2).strip()
                    
                    # Use the quantity from the name, not from after the colon
                    name = actual_name
                    quantity = actual_quantity
                    
                    # If unit is 'g' and quantity is 1, it's likely wrong - use 'pieces' instead
                    if unit == 'g' and quantity > 1:
                        unit = 'pieces'
                
                # Normalize units
                unit = self._normalize_unit(unit)
                
                # Validation: Reject suspiciously small quantities
                if unit == 'g' and quantity < 5:
                    # Less than 5g is suspicious, likely a parsing error
                    continue
                
                items.append({
                    'name': name,
                    'quantity': quantity,
                    'unit': unit,
                    'raw_description': line
                })
            else:
                # Try more flexible parsing: look for numbers in parentheses
                # E.g., "Scrambled eggs (2 eggs)" or "Rice (150g)"
                match = re.match(r'^([^(]+)\s*\((\d+(?:\.\d+)?)\s*([a-zA-Z]+)\)', line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    quantity = float(match.group(2))
                    unit = match.group(3).lower()
                    unit = self._normalize_unit(unit)
                    
                    items.append({
                        'name': name,
                        'quantity': quantity,
                        'unit': unit,
                        'raw_description': line
                    })
        
        return items
    
    def _normalize_unit(self, unit: str) -> str:
        """Normalize unit names to standard forms.
        
        Args:
            unit: Raw unit string
            
        Returns:
            Normalized unit string
        """
        unit = unit.lower().strip()
        
        # Map common variations
        unit_map = {
            'gram': 'g',
            'grams': 'g',
            'ounce': 'oz',
            'ounces': 'oz',
            'tablespoon': 'tbsp',
            'tablespoons': 'tbsp',
            'teaspoon': 'tsp',
            'teaspoons': 'tsp',
            'piece': 'pieces',
            'item': 'pieces',
            'items': 'pieces',
            'egg': 'eggs',
            'slice': 'slices',
            'cup': 'cups',
        }
        
        return unit_map.get(unit, unit)
    
    def parse_text_description(self, description: str) -> Dict[str, Any]:
        """Parse a text description of food to identify items and quantities.
        
        Args:
            description: Natural language description (e.g., "two toasts with guacamole and mixed nuts")
            
        Returns:
            Dict with 'items' list, each containing:
            - name: Food item name
            - quantity: Estimated quantity (numeric)
            - unit: Unit of measurement
            - raw_description: Original description
        
        Raises:
            Exception: If parsing fails
        """
        # Pre-process simple quantity patterns like "5 rotis" or "2 eggs"
        simple_match = re.match(r'^(\d+)\s+([a-zA-Z\s]+)$', description.strip())
        if simple_match:
            quantity = int(simple_match.group(1))
            food_name = simple_match.group(2).strip()
            
            # Determine unit based on food name
            # If plural (ends with 's'), use singular as unit
            if food_name.endswith('s') and len(food_name) > 2:
                unit = food_name[:-1]  # "rotis" → "roti"
            else:
                unit = 'pieces'
            
            return {
                'items': [{
                    'name': food_name,
                    'quantity': quantity,
                    'unit': unit,
                    'raw_description': description
                }],
                'raw_response': f"Simple pattern match: {quantity} {food_name}"
            }
        
        prompt = f"""Parse this food description and extract individual items with quantities:

"{description}"

For EACH food item mentioned, provide:
1. Food name (specific - e.g., "whole wheat toast" not just "bread")
2. Quantity as a number (estimate if not specified)
3. Unit (grams/g, pieces, slices, cups, tbsp, etc.)

Format your response EXACTLY as a numbered list:
1. [Food name]: [quantity] [unit]
2. [Food name]: [quantity] [unit]

CRITICAL: Put the food name FIRST, then colon, then quantity and unit.
WRONG: "5 roti: 1 g"
CORRECT: "Roti: 5 pieces"

Examples:
- "two eggs and toast" → 1. Scrambled eggs: 2 eggs, 2. Whole wheat toast: 2 slices
- "coffee with milk and sugar" → 1. Coffee: 1 cup, 2. Whole milk: 2 tbsp, 3. Sugar: 1 tsp
- "chicken salad" → 1. Grilled chicken: 150 g, 2. Mixed greens: 50 g, 3. Olive oil dressing: 1 tbsp
- "5 rotis" → 1. Roti: 5 pieces

Estimate reasonable serving sizes if quantities aren't specified. Be specific about food types."""

        try:
            # Use callback if provided (for testing)
            if self.vision_callback:
                parsed_text = self.vision_callback(None, prompt)
            elif HAS_REQUESTS:
                # Try OpenClaw API (text-only, no image)
                try:
                    parsed_text = self._call_openclaw_text_api(prompt)
                except Exception as api_error:
                    print(f"OpenClaw API call failed: {api_error}, using file queue")
                    parsed_text = self._request_text_analysis(prompt)
            else:
                parsed_text = self._request_text_analysis(prompt)
            
            if not parsed_text:
                raise Exception("Empty response from text parsing")
            
            # Parse the response using the same parser as vision
            items = self._parse_vision_response(parsed_text)
            
            return {
                'items': items,
                'raw_response': parsed_text
            }
            
        except Exception as e:
            raise Exception(f"Text parsing failed: {e}")
    
    def _call_openclaw_text_api(self, prompt: str, timeout: int = 30) -> str:
        """Call OpenClaw sessions API for text-only analysis (no image).
        
        Args:
            prompt: The prompt to send
            timeout: Request timeout in seconds
            
        Returns:
            Text response from AI
        """
        # Use the sessions API to send a message to main session
        api_url = f"{self.openclaw_url}/api/v1/message"
        
        payload = {
            "message": prompt,
            "sessionKey": "main",
            "timeoutSeconds": timeout
        }
        
        response = requests.post(api_url, json=payload, timeout=timeout + 5)
        response.raise_for_status()
        
        data = response.json()
        return data.get('reply', data.get('message', ''))
    
    def _request_text_analysis(self, prompt: str) -> str:
        """Request text analysis via file queue (fallback).
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Text response from AI
        """
        # Create queue directory
        queue_dir = Path(__file__).parent.parent / 'data' / 'vision_queue'
        queue_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Write request file (text-only, no image)
        request_data = {
            'id': request_id,
            'type': 'text',
            'prompt': prompt,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        request_file = queue_dir / f"{request_id}.json"
        request_file.write_text(json.dumps(request_data, indent=2))
        
        # Wait for response (up to 60 seconds)
        for _ in range(60):
            time.sleep(1)
            
            if request_file.exists():
                data = json.loads(request_file.read_text())
                if data.get('status') == 'completed':
                    response_text = data.get('response', '')
                    # Clean up request file
                    request_file.unlink()
                    return response_text
                elif data.get('status') == 'error':
                    error_msg = data.get('error', 'Unknown error')
                    request_file.unlink()
                    raise Exception(f"Text analysis error: {error_msg}")
        
        # Timeout
        if request_file.exists():
            request_file.unlink()
        raise Exception("Text analysis request timed out (60s)")


# Default analyzer instance
default_analyzer = VisionAnalyzer()
