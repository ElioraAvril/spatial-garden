#!/usr/bin/env python3
"""Build complete indicator_tool.html - reads CATL CSV, embeds BYD/KINGFA data inline"""
import csv, json, os

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(PROJECT, "outputs")
DEST = os.path.join(PROJECT, "task02", "indicator_tool.html")

def load_catl():
    rows = []
    with open(os.path.join(OUT, "ningde_era_daily.csv"), "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    rows.sort(key=lambda x: x["trade_date"])
    return {
        "dates": [r["trade_date"] for r in rows],
        "o": [float(r["open"]) for r in rows],
        "h": [float(r["high"]) for r in rows],
        "l": [float(r["low"]) for r in rows],
        "c": [float(r["close"]) for r in rows],
        "v": [float(r["vol"]) for r in rows]
    }

def load_csv_data(filepath):
    """Load from any CSV if exists"""
    if not os.path.exists(filepath):
        return None
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    rows.sort(key=lambda x: x["trade_date"])
    return {
        "dates": [r["trade_date"] for r in rows],
        "o": [float(r["open"]) for r in rows],
        "h": [float(r["high"]) for r in rows],
        "l": [float(r["low"]) for r in rows],
        "c": [float(r["close"]) for r in rows],
        "v": [float(r["vol"]) for r in rows]
    }

print("Loading data...")
stock_data = {}
stock_data["300750.SZ"] = {"name": "宁德时代", "id": "catl", **load_catl()}
print(f"  宁德时代: {len(stock_data['300750.SZ']['dates'])} records")

# Try loading BYD and KINGFA from CSV
byd = load_csv_data(os.path.join(OUT, "byd_daily.csv"))
kingfa = load_csv_data(os.path.join(OUT, "kingfa_daily.csv"))

if byd:
    stock_data["002594.SZ"] = {"name": "比亚迪", "id": "byd", **byd}
    print(f"  比亚迪: {len(byd['dates'])} records (from CSV)")
else:
    print("  比亚迪: CSV not found, skipping")

if kingfa:
    stock_data["600143.SH"] = {"name": "金发科技", "id": "kingfa", **kingfa}
    print(f"  金发科技: {len(kingfa['dates'])} records (from CSV)")
else:
    print("  金发科技: CSV not found, skipping")

if len(stock_data) < 3:
    print("\nERROR: Some stock data is missing!")
    print("Make sure byd_daily.csv and kingfa_daily.csv exist in outputs/")
    print("Run task02/fetch_missing_data.py first to fetch missing stocks.")
    exit(1)

js_data = json.dumps(stock_data, ensure_ascii=False, separators=(",", ":"))

print(f"Embedded data size: {len(js_data)} chars (~{len(js_data)//1024}KB)")

# Read HTML template
import sys
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "indicator_tool_template.html")
if os.path.exists(TEMPLATE_PATH):
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__DATA_PLACEHOLDER__", js_data)
else:
    print("ERROR: Template not found!")
    exit(1)

os.makedirs(os.path.dirname(DEST), exist_ok=True)
with open(DEST, "w", encoding="utf-8") as f:
    f.write(html)

size = os.path.getsize(DEST) / 1024
print(f"\nGenerated: {DEST}")
print(f"Size: {size:.0f} KB")
print("Done!")
