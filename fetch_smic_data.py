"""
使用标准库 urllib 获取中芯国际(688981.SH)近一年日线行情数据
纯 Python 标准库，无需安装任何第三方包
"""
import urllib.request
import json
import os
from datetime import datetime, timedelta

TOKEN = "YOUR_TUSHARE_TOKEN"  # 替换为你的 Tushare Pro Token
API_URL = "https://api.tushare.pro"
TS_CODE = "688981.SH"

# 计算时间范围
end_date = datetime.now().strftime("%Y%m%d")
start_date = (datetime.now() - timedelta(days=380)).strftime("%Y%m%d")

print(f"获取 {TS_CODE} 从 {start_date} 到 {end_date} 的日线数据...")

# 调用 daily 接口
payload = json.dumps({
    "api_name": "daily",
    "token": TOKEN,
    "params": {
        "ts_code": TS_CODE,
        "start_date": start_date,
        "end_date": end_date
    },
    "fields": "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount"
}).encode("utf-8")

req = urllib.request.Request(API_URL, data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read().decode("utf-8"))

if result.get("code") != 0:
    print(f"API 错误 (code={result.get('code')}): {result.get('msg', '未知错误')}")
    exit(1)

data_wrapper = result["data"]
fields = data_wrapper["fields"]
items = data_wrapper["items"]

if not items:
    print("未获取到数据")
    exit(1)

# 按日期升序排列
items.sort(key=lambda x: x[1])

output_dir = os.path.dirname(os.path.abspath(__file__))

# ========== 保存 CSV ==========
csv_path = os.path.join(output_dir, "smic_daily_data.csv")
with open(csv_path, "w", encoding="utf-8-sig") as f:
    f.write(",".join(fields) + "\n")
    for row in items:
        f.write(",".join(str(v) for v in row) + "\n")

print(f"\n数据已保存: {csv_path}")
print(f"共获取 {len(items)} 条记录")
print(f"日期范围: {items[0][1]} ~ {items[-1][1]}")

# 打印最近5条
print("\n数据预览 (最近5条):")
hdr = f"{'日期':<12} {'开盘':>8} {'收盘':>8} {'最高':>8} {'最低':>8} {'涨跌幅':>8} {'成交量(手)':>12}"
print(hdr)
print("-" * len(hdr))
for row in items[-5:]:
    d = row[1]
    fmt = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    print(f"{fmt:<12} {row[2]:>8.2f} {row[5]:>8.2f} {row[3]:>8.2f} {row[4]:>8.2f} {row[8]:>7.2f}% {row[9]:>10.0f}")

# ========== 生成 HTML ==========
csv_content = ",".join(fields) + "\n"
csv_content += "\n".join(",".join(str(v) for v in row) for row in items)

template_path = os.path.join(output_dir, "smic_dashboard_template.html")
with open(template_path, "r", encoding="utf-8") as f:
    html = f.read()

html = html.replace("__DATA_PLACEHOLDER__", csv_content)

html_path = os.path.join(output_dir, "smic_dashboard.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nHTML 面板已生成: {html_path}")
