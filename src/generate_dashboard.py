#!/usr/bin/env python3
"""Generate a static dashboard HTML with embedded data."""
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from .tracker import tracker


# Default timezone for dashboard
DEFAULT_TIMEZONE = "America/Los_Angeles"


def generate_dashboard(timezone: str = None):
    """Generate dashboard HTML with current data embedded.
    
    Args:
        timezone: Timezone name (e.g., 'America/Los_Angeles'). 
                  Defaults to DEFAULT_TIMEZONE.
    """
    timezone = timezone or DEFAULT_TIMEZONE
    tz = ZoneInfo(timezone)
    
    # Get "today" in the user's timezone
    today = datetime.now(tz).date()
    
    # Get data using timezone-aware queries
    summary = tracker.get_daily_summary(today, timezone)
    food_log = tracker.get_food_log(today, timezone)
    
    # Get week data
    week_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        s = tracker.get_daily_summary(d, timezone)
        week_data.append({
            'date': d.isoformat(),
            'calories': s['food']['calories'],
            'protein': s['food']['protein_g'],
            'water_ml': s['water']['total_ml'],
        })
    
    # Friendly timezone name
    tz_short = datetime.now(tz).strftime('%Z')  # e.g., "PST" or "PDT"
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Macro Tracker</title>
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
        h1 {{ text-align: center; margin-bottom: 20px; font-size: 1.8em; }}
        .date {{ text-align: center; color: #888; margin-bottom: 20px; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
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
        .stat-card .progress-fill {{
            height: 100%;
            border-radius: 3px;
        }}
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
        .refresh {{ text-align: center; margin-top: 20px; color: #666; font-size: 0.8em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🍽️ Macro Tracker</h1>
        <div class="date">{today.strftime('%A, %B %d, %Y')}</div>

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
            <h2>📈 This Week</h2>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
        </div>

        <div class="section">
            <h2>📝 Today's Food</h2>
            <div class="food-log">
                {''.join(f'<div class="food-item"><span class="name">{f["name"]}</span><span class="macros">{int(f["calories"])} cal · {int(f["protein_g"])}g P</span></div>' for f in food_log) if food_log else '<div class="empty">No food logged today</div>'}
            </div>
        </div>
        
        <div class="refresh">Data as of {today.isoformat()} ({tz_short}) • Tell Neo to refresh dashboard</div>
    </div>

    <script>
        const weekData = {json.dumps(week_data)};
        const ctx = document.getElementById('trendChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: weekData.map(d => d.date.slice(5)),
                datasets: [
                    {{
                        label: 'Calories',
                        data: weekData.map(d => d.calories),
                        borderColor: '#e94560',
                        backgroundColor: 'rgba(233, 69, 96, 0.1)',
                        tension: 0.3,
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Protein (g)',
                        data: weekData.map(d => d.protein),
                        borderColor: '#4ecca3',
                        backgroundColor: 'rgba(78, 204, 163, 0.1)',
                        tension: 0.3,
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }},
                scales: {{
                    x: {{ ticks: {{ color: '#666' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                    y: {{ type: 'linear', position: 'left', ticks: {{ color: '#e94560' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                    y1: {{ type: 'linear', position: 'right', ticks: {{ color: '#4ecca3' }}, grid: {{ drawOnChartArea: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>'''
    
    # Write to canvas directory
    output_path = Path('/home/exedev/clawd/canvas/macro-tracker/index.html')
    output_path.write_text(html)
    print(f"Dashboard generated: {output_path}")
    return str(output_path)


if __name__ == '__main__':
    generate_dashboard()
