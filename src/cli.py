#!/usr/bin/env python3
"""Simple CLI for macro tracker."""
import sys
import json
from .tracker import tracker


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.cli <command> [args]")
        print("\nCommands:")
        print("  search <food>       Search for nutrition info")
        print("  log <food>          Log a food item")
        print("  water <amount> [unit]  Log water (default ml)")
        print("  status              Daily summary")
        print("  water-status        Water intake status")
        print("  goals               Show current goals")
        return

    cmd = sys.argv[1].lower()

    if cmd == "search":
        query = " ".join(sys.argv[2:])
        results = tracker.search_food(query)
        for r in results:
            print(f"- {r['name']}: {r['calories']} cal, {r['protein_g']}g protein, {r['carbs_g']}g carbs, {r['fat_g']}g fat")

    elif cmd == "log":
        food = " ".join(sys.argv[2:])
        entry = tracker.log_food(food)
        print(f"Logged: {entry['name']} - {entry['calories']} cal, {entry['protein_g']}g protein")

    elif cmd == "water":
        amount = float(sys.argv[2]) if len(sys.argv) > 2 else 250
        unit = sys.argv[3] if len(sys.argv) > 3 else "ml"
        entry = tracker.log_water(amount, unit)
        print(f"Logged: {entry['amount_ml']}ml water")
        status = tracker.get_water_status()
        print(f"Today: {status['total_ml']}ml / {status['goal_ml']}ml ({status['progress_pct']}%)")

    elif cmd == "status":
        summary = tracker.get_daily_summary()
        print(f"\n📊 Daily Summary - {summary['date']}")
        print(f"\n🍽️  Food:")
        print(f"   Calories: {summary['food']['calories']} / {summary['goals'].get('calories', 2000)} kcal ({summary['progress']['calories_pct']}%)")
        print(f"   Protein:  {summary['food']['protein_g']}g / {summary['goals'].get('protein_g', 150)}g ({summary['progress']['protein_pct']}%)")
        print(f"   Carbs:    {summary['food']['carbs_g']}g")
        print(f"   Fat:      {summary['food']['fat_g']}g")
        print(f"\n💧 Water:")
        print(f"   Total: {summary['water']['total_liters']}L / {summary['goals'].get('water_ml', 3000)/1000}L ({summary['progress']['water_pct']}%)")

    elif cmd == "water-status":
        status = tracker.get_water_status()
        print(f"💧 Water: {status['total_ml']}ml ({status['glasses']} glasses)")
        print(f"   Goal: {status['goal_ml']}ml")
        print(f"   Remaining: {status['remaining_ml']}ml")
        print(f"   Progress: {status['progress_pct']}%")

    elif cmd == "goals":
        goals = tracker.get_goals()
        print("🎯 Current Goals:")
        for k, v in goals.items():
            print(f"   {k}: {v}")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
