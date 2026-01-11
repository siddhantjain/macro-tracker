#!/usr/bin/env python3
"""Simple HTTP API for the macro tracker dashboard."""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from .tracker import tracker


# Default timezone for the API
DEFAULT_TIMEZONE = "America/Los_Angeles"


class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _get_today(self, timezone: str) -> date:
        """Get today's date in the specified timezone."""
        return datetime.now(ZoneInfo(timezone)).date()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # Parse timezone param (default to California)
        timezone = params.get('tz', [DEFAULT_TIMEZONE])[0]

        # Parse date param (interpreted in the specified timezone)
        date_str = params.get('date', [None])[0]
        if date_str:
            try:
                day = date.fromisoformat(date_str)
            except ValueError:
                day = self._get_today(timezone)
        else:
            day = self._get_today(timezone)

        if path == '/api/summary':
            self._send_json(tracker.get_daily_summary(day, timezone))

        elif path == '/api/food':
            self._send_json(tracker.get_food_log(day, timezone))

        elif path == '/api/water':
            self._send_json(tracker.get_water_status(day, timezone))

        elif path == '/api/goals':
            self._send_json(tracker.get_goals())

        elif path == '/api/week':
            # Get last 7 days summary
            today = self._get_today(timezone)
            days = []
            for i in range(6, -1, -1):
                d = today - timedelta(days=i)
                summary = tracker.get_daily_summary(d, timezone)
                days.append({
                    'date': d.isoformat(),
                    'calories': summary['food']['calories'],
                    'protein': summary['food']['protein_g'],
                    'water_ml': summary['water']['total_ml'],
                })
            self._send_json({'days': days, 'goals': tracker.get_goals(), 'timezone': timezone})

        elif path == '/api/month':
            # Get last 30 days summary
            today = self._get_today(timezone)
            days = []
            for i in range(29, -1, -1):
                d = today - timedelta(days=i)
                summary = tracker.get_daily_summary(d, timezone)
                days.append({
                    'date': d.isoformat(),
                    'calories': summary['food']['calories'],
                    'protein': summary['food']['protein_g'],
                    'water_ml': summary['water']['total_ml'],
                })
            self._send_json({'days': days, 'goals': tracker.get_goals(), 'timezone': timezone})

        else:
            self._send_json({'error': 'Not found'}, 404)

    def log_message(self, format, *args):
        pass  # Suppress logging


def run_server(port=8787):
    server = HTTPServer(('127.0.0.1', port), APIHandler)
    print(f"Macro Tracker API running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == '__main__':
    run_server()
