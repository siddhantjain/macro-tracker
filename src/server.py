#!/usr/bin/env python3
"""Combined HTTP server for dashboard + API."""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tracker import tracker

# Default timezone for the dashboard
DEFAULT_TIMEZONE = "America/Los_Angeles"


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

        # Parse timezone param
        timezone = params.get('tz', [DEFAULT_TIMEZONE])[0]
        tz = ZoneInfo(timezone)
        
        # Parse date param (in user's local timezone)
        date_str = params.get('date', [None])[0]
        if date_str:
            try:
                day = date.fromisoformat(date_str)
            except ValueError:
                day = datetime.now(tz).date()
        else:
            day = datetime.now(tz).date()

        # API routes
        if path.startswith('/api/'):
            self._handle_api(path, params, day, timezone)
            return

        # Dashboard
        if path == '/' or path == '/index.html':
            html = generate_dashboard_html(day, timezone)
            self._send_html(html)
            return

        self._send_html('<h1>Not Found</h1>', 404)

    def _handle_api(self, path, params, day, timezone):
        if path == '/api/summary':
            self._send_json(tracker.get_daily_summary(day, timezone))
        elif path == '/api/food':
            self._send_json(tracker.get_food_log(day, timezone))
        elif path == '/api/water':
            self._send_json(tracker.get_water_status(day, timezone))
        elif path == '/api/goals':
            self._send_json(tracker.get_goals())
        elif path == '/api/week':
            tz = ZoneInfo(timezone)
            today = datetime.now(tz).date()
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
        else:
            self._send_json({'error': 'Not found'}, 404)

    def log_message(self, format, *args):
        pass


def generate_dashboard_html(day: date, timezone: str = DEFAULT_TIMEZONE) -> str:
    """Generate dashboard HTML for a specific day."""
    tz = ZoneInfo(timezone)
    today = datetime.now(tz).date()
    tz_short = datetime.now(tz).strftime('%Z')
    
    summary = tracker.get_daily_summary(day, timezone)
    food_log = tracker.get_food_log(day, timezone)
    water_log = tracker.store.get_water_log(day, timezone)
    
    # Convert water timestamps to local time for display
    for entry in water_log:
        try:
            ts = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=ZoneInfo('UTC'))
            local_ts = ts.astimezone(tz)
            entry['local_time'] = local_ts.strftime('%I:%M %p')
        except:
            entry['local_time'] = 'Unknown'
    
    prev_day = (day - timedelta(days=1)).isoformat()
    next_day = (day + timedelta(days=1)).isoformat()
    is_today = day == today
    
    goals = tracker.get_goals()
    week_data = []
    for i in range(6, -1, -1):
        d = day - timedelta(days=i)
        s = tracker.get_daily_summary(d, timezone)
        # Calculate deviation from goals (positive = exceeded, negative = missed)
        protein_diff = s['food']['protein_g'] - goals.get('protein_g', 150)
        water_diff_pct = ((s['water']['total_ml'] / goals.get('water_ml', 2218)) - 1) * 100
        week_data.append({
            'date': d.isoformat(),
            'protein': s['food']['protein_g'],
            'protein_goal': goals.get('protein_g', 150),
            'protein_diff': round(protein_diff, 1),
            'water_ml': s['water']['total_ml'],
            'water_goal': goals.get('water_ml', 2218),
            'water_diff_pct': round(water_diff_pct, 1),
        })

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Macro Tracker - {day.isoformat()}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation"></script>
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
        
        /* Clickable cards */
        .stat-card {{ cursor: pointer; transition: transform 0.2s, box-shadow 0.2s; }}
        .stat-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.3); }}
        
        /* Modal styles */
        .modal-overlay {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .modal-overlay.active {{ display: flex; }}
        .modal {{
            background: #1a1a2e;
            border-radius: 16px;
            padding: 25px;
            max-width: 500px;
            width: 100%;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        }}
        .modal h3 {{
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1.3em;
        }}
        .modal-close {{
            position: absolute;
            top: 15px;
            right: 15px;
            background: none;
            border: none;
            color: #888;
            font-size: 1.5em;
            cursor: pointer;
        }}
        .modal-close:hover {{ color: #fff; }}
        .modal-item {{
            display: flex;
            justify-content: space-between;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .modal-item:last-child {{ border-bottom: none; }}
        .modal-item .name {{ flex: 1; }}
        .modal-item .value {{ font-weight: bold; color: #4ecca3; }}
        .modal-item .time {{ color: #888; font-size: 0.9em; }}
        .modal-total {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 2px solid rgba(255,255,255,0.2);
            font-weight: bold;
            display: flex;
            justify-content: space-between;
        }}
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
            <div class="stat-card calories" onclick="showModal('calories')">
                <div class="icon">🔥</div>
                <div class="value">{int(summary['food']['calories'])}</div>
                <div class="label">Calories</div>
                <div class="goal">/ {summary['goals']['calories']}</div>
                <div class="progress-bar"><div class="progress-fill" style="width: {min(summary['progress']['calories_pct'], 100)}%"></div></div>
            </div>
            <div class="stat-card protein" onclick="showModal('protein')">
                <div class="icon">💪</div>
                <div class="value">{int(summary['food']['protein_g'])}</div>
                <div class="label">Protein (g)</div>
                <div class="goal">/ {summary['goals']['protein_g']}g</div>
                <div class="progress-bar"><div class="progress-fill" style="width: {min(summary['progress']['protein_pct'], 100)}%"></div></div>
            </div>
            <div class="stat-card water" onclick="showModal('water')">
                <div class="icon">💧</div>
                <div class="value">{summary['water']['total_liters']:.1f}</div>
                <div class="label">Water (L)</div>
                <div class="goal">/ {summary['goals']['water_ml']/1000:.1f}L</div>
                <div class="progress-bar"><div class="progress-fill" style="width: {min(summary['progress']['water_pct'], 100)}%"></div></div>
            </div>
            <div class="stat-card carbs" onclick="showModal('carbs')">
                <div class="icon">🍞</div>
                <div class="value">{int(summary['food']['carbs_g'])}</div>
                <div class="label">Carbs (g)</div>
                <div class="goal">&nbsp;</div>
                <div class="progress-bar"><div class="progress-fill" style="width: 0%"></div></div>
            </div>
        </div>
        
        <!-- Modals -->
        <div class="modal-overlay" id="modal-calories" onclick="closeModal(event)">
            <div class="modal" onclick="event.stopPropagation()">
                <button class="modal-close" onclick="closeModal()">&times;</button>
                <h3>🔥 Calories Breakdown</h3>
                {''.join(f'<div class="modal-item"><span class="name">{f["name"]}</span><span class="value">{int(f["calories"])} cal</span></div>' for f in food_log) if food_log else '<div class="empty">No food logged</div>'}
                <div class="modal-total"><span>Total</span><span>{int(summary['food']['calories'])} cal</span></div>
            </div>
        </div>
        
        <div class="modal-overlay" id="modal-protein" onclick="closeModal(event)">
            <div class="modal" onclick="event.stopPropagation()">
                <button class="modal-close" onclick="closeModal()">&times;</button>
                <h3>💪 Protein Breakdown</h3>
                {''.join(f'<div class="modal-item"><span class="name">{f["name"]}</span><span class="value">{f["protein_g"]:.1f}g</span></div>' for f in sorted(food_log, key=lambda x: x["protein_g"], reverse=True)) if food_log else '<div class="empty">No food logged</div>'}
                <div class="modal-total"><span>Total</span><span>{summary['food']['protein_g']:.1f}g</span></div>
            </div>
        </div>
        
        <div class="modal-overlay" id="modal-water" onclick="closeModal(event)">
            <div class="modal" onclick="event.stopPropagation()">
                <button class="modal-close" onclick="closeModal()">&times;</button>
                <h3>💧 Water Log</h3>
                {''.join('<div class="modal-item"><span class="time">' + w["local_time"] + '</span><span class="value">' + str(int(w["amount_ml"])) + 'ml</span></div>' for w in water_log) if water_log else '<div class="empty">No water logged</div>'}
                <div class="modal-total"><span>Total</span><span>{summary['water']['total_ml']:.0f}ml ({summary['water']['total_liters']:.2f}L)</span></div>
            </div>
        </div>
        
        <div class="modal-overlay" id="modal-carbs" onclick="closeModal(event)">
            <div class="modal" onclick="event.stopPropagation()">
                <button class="modal-close" onclick="closeModal()">&times;</button>
                <h3>🍞 Carbs Breakdown</h3>
                {''.join(f'<div class="modal-item"><span class="name">{f["name"]}</span><span class="value">{f["carbs_g"]:.1f}g</span></div>' for f in sorted(food_log, key=lambda x: x["carbs_g"], reverse=True)) if food_log else '<div class="empty">No food logged</div>'}
                <div class="modal-total"><span>Total</span><span>{summary['food']['carbs_g']:.1f}g</span></div>
            </div>
        </div>

        <div class="section">
            <h2>📈 Goal Progress (Past 7 Days)</h2>
            <div class="chart-container">
                <canvas id="proteinChart"></canvas>
            </div>
            <div class="chart-container" style="margin-top: 15px;">
                <canvas id="waterChart"></canvas>
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
        const proteinGoal = {goals.get('protein_g', 150)};
        const waterGoal = {goals.get('water_ml', 2218)};
        
        // Protein chart - bar chart showing vs goal
        new Chart(document.getElementById('proteinChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: weekData.map(d => d.date.slice(5)),
                datasets: [
                    {{ 
                        label: 'Protein (g)', 
                        data: weekData.map(d => d.protein), 
                        backgroundColor: weekData.map(d => d.protein >= proteinGoal ? '#4ecca3' : '#e94560'),
                        borderRadius: 4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{ 
                    legend: {{ display: false }},
                    title: {{ display: true, text: '💪 Protein (goal: ' + proteinGoal + 'g)', color: '#888' }},
                    annotation: {{
                        annotations: {{
                            goalLine: {{
                                type: 'line',
                                yMin: proteinGoal,
                                yMax: proteinGoal,
                                borderColor: '#fff',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {{ display: true, content: 'Goal', position: 'end', color: '#fff' }}
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#666' }}, grid: {{ display: false }} }},
                    y: {{ ticks: {{ color: '#888' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }}, beginAtZero: true }}
                }}
            }}
        }});
        
        // Water chart - bar chart showing vs goal  
        new Chart(document.getElementById('waterChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: weekData.map(d => d.date.slice(5)),
                datasets: [
                    {{ 
                        label: 'Water (ml)', 
                        data: weekData.map(d => d.water_ml), 
                        backgroundColor: weekData.map(d => d.water_ml >= waterGoal ? '#00adb5' : '#e94560'),
                        borderRadius: 4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{ 
                    legend: {{ display: false }},
                    title: {{ display: true, text: '💧 Water (goal: ' + (waterGoal/1000).toFixed(1) + 'L)', color: '#888' }},
                    annotation: {{
                        annotations: {{
                            goalLine: {{
                                type: 'line',
                                yMin: waterGoal,
                                yMax: waterGoal,
                                borderColor: '#fff',
                                borderWidth: 2,
                                borderDash: [5, 5],
                                label: {{ display: true, content: 'Goal', position: 'end', color: '#fff' }}
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ ticks: {{ color: '#666' }}, grid: {{ display: false }} }},
                    y: {{ ticks: {{ color: '#888', callback: v => (v/1000).toFixed(1) + 'L' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }}, beginAtZero: true }}
                }}
            }}
        }});
    </script>
    <script>
        function showModal(type) {{
            document.getElementById('modal-' + type).classList.add('active');
        }}
        function closeModal(event) {{
            if (!event || event.target.classList.contains('modal-overlay') || event.target.classList.contains('modal-close')) {{
                document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
            }}
        }}
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeModal();
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
