#!/usr/bin/env python3
"""Save 比亚迪 and 金发科技 CSV data fetched from Tushare MCP to outputs/"""
import csv, os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 比亚迪 002594.SZ data (saved from API response)
byd_data = [
    ["trade_date","open","high","low","close","pre_close","change","pct_chg","vol","amount"],
]
# Note: The data is too large to embed directly. Let me use Python to save it.
# I'll write the data inline from the MCP response
print("Script placeholder - data will be saved from API response")
