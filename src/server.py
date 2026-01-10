#!/usr/bin/env python3
"""Combined HTTP server for dashboard + API."""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import date, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tracker import tracker


import base64

def load_token():
    """Load the dashboard token from file."""
    token_file = Path(__file__).parent.parent / 'data' / '.dashboard_token'
    if token_file.exists():
        return token_file.read_text().strip()
    return None

DASHBOARD_TOKEN = load_token()
# Basic auth: username "macro", password is the token
DASHBOARD_USER = "macro"


class MacroTrackerHandler(BaseHTTPRequestHandler):
    def _check_auth(self, params):
        """Check if request is authenticated via Basic Auth."""
        if not DASHBOARD_TOKEN:
            return True  # No token configured, allow all
        
        # Check Basic Auth header
        auth_header = self.headers.get('Authorization', '')
        if auth_header.startswith('Basic '):
            try:
                decoded = base64.b64decode(auth_header[6:]).decode()
                user, password = decoded.split(':', 1)
                if user == DASHBOARD_USER and password == DASHBOARD_TOKEN:
                    return True
            except:
                pass
        
        return False

    def _send_auth_required(self):
        """Send 401 with Basic Auth challenge."""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Macro Tracker"')
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<h1>Authentication Required</h1>')

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # Check authentication (Basic Auth)
        if not self._check_auth(params):
            self._send_auth_required()
            return

        # Parse date param
        date_str = params.get('date', [None])[0]
        if date_str:
            try:
                day = date.fromisoformat(date_str)
            except ValueError:
                day = date.today()
        else:
            day = date.today()

        # API routes
        if path.startswith('/api/'):
            self._handle_api(path, params, day)
            return

        # Dashboard
        if path == '/' or path == '/index.html':
            html = generate_dashboard_html(day)
            self._send_html(html)
            return

        self._send_html('<h1>Not Found</h1>', 404)

    def _handle_api(self, path, params, day):
        if path == '/api/summary':
            self._send_json(tracker.get_daily_summary(day))
        elif path == '/api/food':
            self._send_json(tracker.get_food_log(day))
        elif path == '/api/water':
            self._send_json(tracker.get_water_status(day))
        elif path == '/api/goals':
            self._send_json(tracker.get_goals())
        elif path == '/api/week':
            days = []
            for i in range(6, -1, -1):
                d = date.today() - timedelta(days=i)
                summary = tracker.get_daily_summary(d)
                days.append({
                    'date': d.isoformat(),
                    'calories': summary['food']['calories'],
                    'protein': summary['food']['protein_g'],
                    'water_ml': summary['water']['total_ml'],
                })
            self._send_json({'days': days, 'goals': tracker.get_goals()})
        else:
            self._send_json({'error': 'Not found'}, 404)

    def log_message(self, format, *args):
        pass


def generate_dashboard_html(day: date) -> str:
    """Generate dashboard HTML for a specific day."""
    today = date.today()
    summary = tracker.get_daily_summary(day)
    food_log = tracker.get_food_log(day)
    
    prev_day = (day - timedelta(days=1)).isoformat()
    next_day = (day + timedelta(days=1)).isoformat()
    is_today = day == today
    
    week_data = []
    for i in range(6, -1, -1):
        d = day - timedelta(days=i)
        s = tracker.get_daily_summary(d)
        week_data.append({
            'date': d.isoformat(),
            'calories': s['food']['calories'],
            'protein': s['food']['protein_g'],
            'water_ml': s['water']['total_ml'],
        })

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Macro Tracker - {day.isoformat()}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 15px; font-size: 1.8em; }}
        
        .date-nav {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
        }}
        .date-nav a, .date-nav button {{
            background: #0f3460;
            border: none;
            color: #fff;
            padding: 10px 18px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            text-decoration: none;
        }}
        .date-nav a:hover, .date-nav button:hover {{ background: #e94560; }}
        .date-nav .current {{
            background: rgba(255,255,255,0.1);
            padding: 10px 15px;
            border-radius: 8px;
            min-width: 140px;
            text-align: center;
        }}
        .date-nav input {{
            background: #0f3460;
            border: none;
            color: #fff;
            padding: 10px;
            border-radius: 8px;
            font-size: 1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
            text-align: center;
        }}
        .stat-card .icon {{ font-size: 2em; margin-bottom: 8px; }}
        .stat-card .value {{ font-size: 1.8em; font-weight: bold; }}
        .stat-card .label {{ color: #888; font-size: 0.9em; margin-top: 4px; }}
        .stat-card .goal {{ color: #666; font-size: 0.8em; }}
        .stat-card .progress-bar {{
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            margin-top: 10px;
            overflow: hidden;
        }}
        .stat-card .progress-fill {{ height: 100%; border-radius: 3px; }}
        .calories .progress-fill {{ background: #e94560; }}
        .protein .progress-fill {{ background: #4ecca3; }}
        .water .progress-fill {{ background: #00adb5; }}
        .carbs .progress-fill {{ background: #f39c12; }}
        
        .section {{ margin-bottom: 25px; }}
        .section h2 {{ font-size: 1.2em; margin-bottom: 15px; color: #888; }}
        .chart-container {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 20px;
        }}
        .food-log {{
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 15px;
        }}
        .food-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .food-item:last-child {{ border-bottom: none; }}
        .food-item .name {{ flex: 1; }}
        .food-item .macros {{ color: #888; font-size: 0.9em; }}
        .empty {{ text-align: center; color: #666; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🍽️ Macro Tracker</h1>
        
        <div class="date-nav">
            <a href="/?date={prev_day}">◀ Prev</a>
            <div class="current">{day.strftime('%a, %b %d')}</div>
            <a href="/?date={next_day}">Next ▶</a>
            {'' if is_today else f'<a href="/">Today</a>'}
        </div>

        <div class="stats-grid">
            <div class="stat-card calories">
                <div class="icon">🔥</div>
                <div class="value">{int(summary['food']['calories'])}</div>
                <div class="label">Calories</div>
                <div class="goal">/ {summary['goals']['calories']}</div>
                <div class="progress-bar"><div class="progress-fill" style="width: {min(summary['progress']['calories_pct'], 100)}%"></div></div>
            </div>
            <div class="stat-card protein">
                <div class="icon">💪</div>
                <div class="value">{int(summary['food']['protein_g'])}</div>
                <div class="label">Protein (g)</div>
                <div class="goal">/ {summary['goals']['protein_g']}g</div>
                <div class="progress-bar"><div class="progress-fill" style="width: {min(summary['progress']['protein_pct'], 100)}%"></div></div>
            </div>
            <div class="stat-card water">
                <div class="icon">💧</div>
                <div class="value">{summary['water']['total_liters']:.1f}</div>
                <div class="label">Water (L)</div>
                <div class="goal">/ {summary['goals']['water_ml']/1000:.1f}L</div>
                <div class="progress-bar"><div class="progress-fill" style="width: {min(summary['progress']['water_pct'], 100)}%"></div></div>
            </div>
            <div class="stat-card carbs">
                <div class="icon">🍞</div>
                <div class="value">{int(summary['food']['carbs_g'])}</div>
                <div class="label">Carbs (g)</div>
                <div class="goal">&nbsp;</div>
                <div class="progress-bar"><div class="progress-fill" style="width: 0%"></div></div>
            </div>
        </div>

        <div class="section">
            <h2>📈 Past 7 Days</h2>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>📝 Food Log</h2>
            <div class="food-log">
                {''.join(f'<div class="food-item"><span class="name">{f["name"]}</span><span class="macros">{int(f["calories"])} cal · {int(f["protein_g"])}g P</span></div>' for f in food_log) if food_log else '<div class="empty">No food logged for this day</div>'}
            </div>
        </div>
    </div>
    <script>
        const weekData = {json.dumps(week_data)};
        new Chart(document.getElementById('trendChart').getContext('2d'), {{
            type: 'line',
            data: {{
                labels: weekData.map(d => d.date.slice(5)),
                datasets: [
                    {{ label: 'Calories', data: weekData.map(d => d.calories), borderColor: '#e94560', tension: 0.3, yAxisID: 'y' }},
                    {{ label: 'Protein (g)', data: weekData.map(d => d.protein), borderColor: '#4ecca3', tension: 0.3, yAxisID: 'y1' }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }},
                scales: {{
                    x: {{ ticks: {{ color: '#666' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                    y: {{ position: 'left', ticks: {{ color: '#e94560' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                    y1: {{ position: 'right', ticks: {{ color: '#4ecca3' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>'''


def run_server(port=4001):
    server = HTTPServer(('0.0.0.0', port), MacroTrackerHandler)
    print(f"Macro Tracker running on http://0.0.0.0:{port}")
    server.serve_forever()


if __name__ == '__main__':
    run_server()
