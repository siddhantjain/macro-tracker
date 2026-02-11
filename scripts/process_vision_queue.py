#!/usr/bin/env python3
"""
Vision queue processor for Neo.
Monitors vision_queue directory and processes image analysis requests.

Usage: python process_vision_queue.py [--once]
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def process_request(request_file: Path):
    """Process a single vision analysis request.
    
    Neo will intercept this and use the image tool to analyze the image,
    then write the response.
    
    Args:
        request_file: Path to request JSON file
    """
    try:
        request_data = json.loads(request_file.read_text())
        request_id = request_data['request_id']
        image_path = request_data['image_path']
        prompt = request_data['prompt']
        
        print(f"Processing vision request {request_id}: {image_path}")
        
        # This is where Neo will intercept and use the image tool
        # For now, return a placeholder that Neo will replace
        
        print(f"VISION_REQUEST:{request_id}:{image_path}:{prompt}")
        
        # Neo will see this output and handle it appropriately
        # The response will be written by Neo to response_{request_id}.json
        
    except Exception as e:
        print(f"Error processing request: {e}")
        # Write error response
        response_file = request_file.parent / f"response_{request_data.get('request_id', 'unknown')}.json"
        response_file.write_text(json.dumps({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }))


def monitor_queue(queue_dir: Path, once: bool = False):
    """Monitor vision queue directory and process requests.
    
    Args:
        queue_dir: Path to vision_queue directory
        once: If True, process once and exit
    """
    print(f"Monitoring vision queue: {queue_dir}")
    
    while True:
        # Find pending requests
        request_files = list(queue_dir.glob("request_*.json"))
        
        for request_file in request_files:
            process_request(request_file)
        
        if once:
            break
        
        time.sleep(1)


def main():
    # Get queue directory
    queue_dir = Path(__file__).parent.parent / "data" / "vision_queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    # Check for --once flag
    once = '--once' in sys.argv
    
    monitor_queue(queue_dir, once=once)


if __name__ == '__main__':
    main()
