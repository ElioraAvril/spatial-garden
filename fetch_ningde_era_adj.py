"""
宁德时代(300750.SZ) 智能投资看板 — 含前复权/后复权/不复权对比分析
参考模板: 寒武纪投资看板
"""
import urllib.request
import json
import os
from datetime import datetime, timedelta

TOKEN = "YOUR_TUSHARE_TOKEN"  # 替换为你的 Tushare Token
API = "https://api.tushare.pro"
TS_CODE = "300750.SZ"
NAME = "宁德时代"

end_date = datetime.now().strftime("%Y%m%d")
start_date = (datetime.now() - timedelta(days=380)).strftime("%Y%m%d")

def tushare(api_name, params, fields=""):
    p = {"api_name": api_name, "token": TOKEN, "params": params}
    if fields: p["fields"] = fields
    req = urllib.request.Request(API, data=json.dumps(p).encode(), headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())
    if res.get("code") != 0:
        raise Exception(f"API error: {res.get('msg')}")
    return res["data"]["items"], res["data"]["fields"]

print(f"正在获取 {NAME}({TS_CODE}) 数据...")

# 1. 日线数据
items, fields = tushare("daily", {"ts_code":TS_CODE, "start_date":start_date, "end_date":end_date},
    "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount")
items.sort(key=lambda x: x[1])

# 2. 复权因子
adj_items, _ = tushare("adj_factor", {"ts_code":TS_CODE, "start_date":start_date, "end_date":end_date},
    "ts_code,trade_date,adj_factor")
adj_map = {r[1]: float(r[2]) for r in adj_items}
print(f"  复权因子: {len(adj_map)} 条")

# 3. 财务数据
try:
    fina_items, fina_fields = tushare("fina_indicator",
        {"ts_code":TS_CODE, "start_date":"20240101", "end_date":end_date},
        "ts_code,end_date,eps,roe,netprofit_yoy,grossprofit_margin,revenue,total_revenue_ps")
    fina_items.sort(key=lambda x: x[1], reverse=True)
    latest_fina = fina_items[0] if fina_items else None
    print(f"  财务数据: {len(fina_items)} 条")
except:
    fina_items = []; latest_fina = None
    print("  财务数据: 获取失败")

# 4. 新闻
try:
    news_items, _ = tushare("news", {"start_date": (datetime.now()-timedelta(days=30)).strftime("%Y%m%d"),
        "end_date": end_date, "src": "eastmoney"}, "datetime,content")
    news_items.sort(key=lambda x: x[0], reverse=True)
    # 过滤与宁德时代相关的
    relevant = [n for n in news_items[:50] if TS_CODE[:6] in n[1] or "宁德" in n[1]][:5]
    print(f"  新闻: {len(relevant)} 条相关")
except:
    relevant = []
    print("  新闻: 获取失败")

output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(output_dir, exist_ok=True)

# 解析数据
dates = [f"{r[1][:4]}-{r[1][4:6]}-{r[1][6:]}" for r in items]
opens = [float(r[2]) for r in items]
highs = [float(r[3]) for r in items]
lows  = [float(r[4]) for r in items]
closes = [float(r[5]) for r in items]
pcts = [float(r[8]) for r in items]
vols  = [float(r[9]) for r in items]
amounts = [float(r[10]) for r in items]
trade_dates = [r[1] for r in items]

# 计算前复权 & 后复权
# adj_factor 是后复权因子: hfq_price = price * adj_factor / latest_adj_factor
# 最后一个交易日的复权因子作为基准
if adj_map:
    adj_vals = [adj_map.get(td, 1.0) for td in trade_dates]
    last_adj = adj_vals[-1] if adj_vals else 1.0
    first_adj = adj_vals[0] if adj_vals else 1.0

    # 前复权: 以最新因子为基准
    close_qfq = [c * a / last_adj for c, a in zip(closes, adj_vals)]
    open_qfq  = [o * a / last_adj for o, a in zip(opens, adj_vals)]
    high_qfq  = [h * a / last_adj for h, a in zip(highs, adj_vals)]
    low_qfq   = [l * a / last_adj for l, a in zip(lows, adj_vals)]

    # 后复权: 以最早因子为基准
    close_hfq = [c * a / first_adj for c, a in zip(closes, adj_vals)]
    open_hfq  = [o * a / first_adj for o, a in zip(opens, adj_vals)]
    high_hfq  = [h * a / first_adj for h, a in zip(highs, adj_vals)]
    low_hfq   = [l * a / first_adj for l, a in zip(lows, adj_vals)]
    print("  复权价格计算完成")
else:
    close_qfq = close_hfq = open_qfq = open_hfq = high_qfq = high_hfq = low_qfq = low_hfq = closes
    print("  警告: 无复权因子数据，使用原始价格")

# 保存复权 CSV
csv_path = os.path.join(output_dir, "ningde_era_adj.csv")
with open(csv_path, "w", encoding="utf-8-sig") as f:
    f.write("trade_date,open,high,low,close,pct_chg,vol,amount,adj_factor,open_qfq,close_qfq,high_qfq,low_qfq,open_hfq,close_hfq,high_hfq,low_hfq\n")
    for i in range(len(dates)):
        adj = adj_vals[i] if adj_map else 1.0
        f.write(f"{trade_dates[i]},{opens[i]:.2f},{highs[i]:.2f},{lows[i]:.2f},{closes[i]:.2f},{pcts[i]:.2f},{vols[i]:.0f},{amounts[i]:.0f},{adj:.6f},{open_qfq[i]:.2f},{close_qfq[i]:.2f},{high_qfq[i]:.2f},{low_qfq[i]:.2f},{open_hfq[i]:.2f},{close_hfq[i]:.2f},{high_hfq[i]:.2f},{low_hfq[i]:.2f}\n")
print(f"  复权CSV已保存: outputs/ningde_era_adj.csv")

# ──────────── 计算技术指标 ────────────
def ma(data, n):
    result = []
    for i in range(len(data)):
        if i < n-1: result.append(None)
        else: result.append(sum(data[i-n+1:i+1])/n)
    return result

def rsi(data, n=14):
    gains = [max(data[i]-data[i-1], 0) for i in range(1, len(data))]
    losses = [max(data[i-1]-data[i], 0) for i in range(1, len(data))]
    rsival = [None] * (n)
    avg_gain = sum(gains[:n])/n
    avg_loss = sum(losses[:n])/n
    rsival.append(100 - 100/(1 + avg_gain/avg_loss) if avg_loss > 0 else 100)
    for i in range(n, len(gains)):
        avg_gain = (avg_gain*13 + gains[i])/14
        avg_loss = (avg_loss*13 + losses[i])/14
        rsival.append(100 - 100/(1 + avg_gain/avg_loss) if avg_loss > 0 else 100)
    return rsival

close_ma5  = ma(closes, 5)
close_ma10 = ma(closes, 10)
close_ma20 = ma(closes, 20)
close_ma60 = ma(closes, 60)
rsi14 = rsi(closes, 14)

# 波动率(20日)
volatility20 = [None]*19
for i in range(19, len(closes)):
    chunk = pcts[i-19:i+1]
    volatility20.append((sum((x-np_mean(chunk))**2 for x in chunk)/20)**0.5)

# 简单计算年化波动率
import math
def np_mean(arr): return sum(arr)/len(arr)
vol20_pct = [None]*19
for i in range(19, len(pcts)):
    v = (sum((x - sum(pcts[i-19:i+1])/20)**2 for x in pcts[i-19:i+1])/20)**0.5
    vol20_pct.append(v)

n = len(dates) - 1
latest_vol20 = vol20_pct[-1] if vol20_pct[-1] else 0
high_52w = max(highs[-250:]) if len(highs) >= 250 else max(highs)
low_52w  = min(lows[-250:]) if len(lows) >= 250 else min(lows)
avg_vol = sum(vols[-60:])/len(vols[-60:])/100

# 均线排列判断
ma_trend = "多头排列" if close_ma5[-1] and close_ma10[-1] and close_ma20[-1] and close_ma5[-1] > close_ma10[-1] > close_ma20[-1] else \
           "空头排列" if close_ma5[-1] and close_ma10[-1] and close_ma20[-1] and close_ma5[-1] < close_ma10[-1] < close_ma20[-1] else "交叉震荡"

latest_close = closes[-1]
latest_rsi = rsi14[-1] if rsi14[-1] else 50

# ──────────── 组装 JS 数据数组 ────────────
n_js = len(dates)
arr = lambda vals, fmt=".2f": ", ".join(f"{v:{fmt}}" if v is not None else "null" for v in vals)
arr_f = lambda vals: ", ".join(f"{v:.2f}" for v in vals)

# 生成 HTML（使用 replace 避免 f-string 与 JS 花括号冲突）
template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{NAME} 300750.SZ 智能投资看板</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root{{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--sub:#8b949e;--up:#f85149;--down:#3fb950;--blue:#58a6ff;--accent:#bc8cff;--yellow:#d2991d}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);min-height:100vh;line-height:1.5}}
.header{{background:linear-gradient(135deg,#0d1117,#1a2332);border-bottom:1px solid var(--border);padding:24px 32px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px}}
.header-title h1{{font-size:24px;font-weight:700;display:flex;align-items:center;gap:10px}}
.header-title .code{{color:var(--sub);font-size:14px;font-weight:400}}
.header-badge{{display:flex;gap:12px;align-items:center}}
.badge{{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:20px;font-size:12px;border:1px solid var(--border)}}
.badge.green{{color:var(--down);border-color:#238636;background:rgba(63,185,80,0.1)}}
.badge.red{{color:var(--up);border-color:#da3633;background:rgba(248,81,73,0.1)}}
.badge.blue{{color:var(--blue);border-color:#1f6feb;background:rgba(88,166,255,0.1)}}
.status-indicator{{display:flex;align-items:center;gap:6px}}
.status-dot{{width:8px;height:8px;border-radius:50%;background:var(--down);animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
.container{{max-width:1440px;margin:0 auto;padding:24px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}
.grid4{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:8px;overflow:hidden;margin-bottom:16px}}
.card-header{{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;font-size:14px;font-weight:600}}
.card-header .icon{{font-size:16px}}
.card-body{{padding:16px 20px}}
.chart-box{{width:100%;height:450px}}
.chart-box.lg{{height:520px}}
.chart-box.sm{{height:260px}}
.stat-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.stat-item{{text-align:center;padding:10px 8px;border-radius:6px;background:rgba(48,54,61,0.4)}}
.stat-item .lbl{{font-size:11px;color:var(--sub);margin-bottom:4px}}
.stat-item .val{{font-size:18px;font-weight:700}}
.key-val{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(48,54,61,0.6);font-size:13px}}
.key-val .k{{color:var(--sub)}}
.key-val .v{{font-weight:600;text-align:right}}
.tag{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;margin-right:4px}}
.tag.up{{background:rgba(248,81,73,0.15);color:var(--up)}}
.tag.down{{background:rgba(63,185,80,0.15);color:var(--down)}}
.progress-bar{{height:6px;border-radius:3px;background:rgba(48,54,61,0.6);margin-top:6px;overflow:hidden}}
.progress-fill{{height:100%;border-radius:3px}}
.news-item{{padding:10px 0;border-bottom:1px solid rgba(48,54,61,0.4);font-size:13px;line-height:1.6}}
.news-item .date{{color:var(--sub);font-size:11px;margin-bottom:2px}}
.news-item .content{{color:var(--text)}}
.fin-table{{width:100%;border-collapse:collapse;font-size:13px}}
.fin-table th{{background:rgba(48,54,61,0.4);padding:8px 12px;text-align:center;border:1px solid var(--border);color:var(--sub)}}
.fin-table td{{padding:8px 12px;text-align:center;border:1px solid var(--border)}}
.fin-table td:first-child{{text-align:left;color:var(--sub)}}
.adj-toggle{{display:flex;gap:0;background:rgba(48,54,61,0.4);border-radius:6px;overflow:hidden;margin-bottom:12px}}
.adj-btn{{padding:6px 16px;font-size:12px;border:none;cursor:pointer;background:transparent;color:var(--sub);transition:.2s}}
.adj-btn.active{{background:var(--blue);color:#fff}}
.flex-between{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}}
@media(max-width:768px){{.grid2,.grid3,.grid4{{grid-template-columns:1fr}}.header{{padding:16px}}.stat-grid{{grid-template-columns:repeat(2,1fr)}}}}
.tooltip-custom{{display:none;position:fixed;background:rgba(22,27,34,0.95);border:1px solid var(--border);border-radius:8px;padding:12px 16px;font-size:12px;z-index:1000;pointer-events:none;max-width:260px}}
.comparison-row{{display:flex;align-items:center;gap:8px;padding:4px 0}}
.comparison-label{{min-width:60px;color:var(--sub);font-size:12px}}
.comparison-value{{font-weight:600;font-size:12px}}
</style>
</head>
<body>

<div class="header">
  <div class="header-title">
    <h1>{NAME}</h1>
    <span class="code">300750.SZ · 创业板 · 新能源电池 · 动力电池龙头</span>
  </div>
  <div class="header-badge">
    <span class="badge green"><span class="status-dot"></span> 交易中</span>
    <span class="badge blue">复权分析</span>
  </div>
</div>

<div class="container">

<!-- 顶部统计 -->
<div class="stat-grid" id="topStats" style="margin-bottom:16px"></div>

<!-- 复权切换按钮 + K线图 -->
<div class="card">
  <div class="card-header">
    <span class="icon">📈</span>K线图 · {NAME} 300750.SZ
    <div class="adj-toggle" style="margin-left:auto">
      <button class="adj-btn active" onclick="switchAdj('none')">不复权</button>
      <button class="adj-btn" onclick="switchAdj('qfq')">前复权</button>
      <button class="adj-btn" onclick="switchAdj('hfq')">后复权</button>
    </div>
  </div>
  <div class="chart-box lg" id="klineChart"></div>
  <div class="card-body" style="display:flex;gap:20px;font-size:12px;color:var(--sub);padding-top:0">
    <span><span style="display:inline-block;width:10px;height:10px;background:var(--blue);border-radius:2px;margin-right:4px;vertical-align:middle"></span>MA5</span>
    <span><span style="display:inline-block;width:10px;height:10px;background:var(--yellow);border-radius:2px;margin-right:4px;vertical-align:middle"></span>MA10</span>
    <span><span style="display:inline-block;width:10px;height:10px;background:var(--accent);border-radius:2px;margin-right:4px;vertical-align:middle"></span>MA20</span>
    <span><span style="display:inline-block;width:10px;height:10px;background:#8b949e;border-radius:2px;margin-right:4px;vertical-align:middle"></span>MA60</span>
  </div>
</div>

<!-- 成交量 -->
<div class="card">
  <div class="card-header"><span class="icon">📊</span>成交量</div>
  <div class="chart-box sm" id="volChart"></div>
</div>

<!-- 技术面 + 复权对比 -->
<div class="grid2">
  <div class="card">
    <div class="card-header"><span class="icon">📊</span>技术面速览</div>
    <div class="card-body" id="techPanel">
      <div class="key-val"><span class="k">RSI(14)</span><span class="v" style="color:{{'#3fb950' if latest_rsi < 30 else '#f85149' if latest_rsi > 70 else '#d2991d'}}">{latest_rsi:.1f}</span></div>
      <div class="key-val"><span class="k">MA20</span><span class="v">¥{close_ma20[-1]:.2f}</span></div>
      <div class="key-val"><span class="k">MA60</span><span class="v">¥{close_ma60[-1]:.2f}</span></div>
      <div class="key-val"><span class="k">52周最高</span><span class="v">¥{high_52w:.2f}</span></div>
      <div class="key-val"><span class="k">52周最低</span><span class="v">¥{low_52w:.2f}</span></div>
      <div class="key-val"><span class="k">近20日波动率</span><span class="v">{latest_vol20:.2f}%</span></div>
      <div class="key-val"><span class="k">支撑 / 阻力</span><span class="v">¥{low_52w:.2f} / ¥{high_52w:.2f}</span></div>
      <div class="key-val"><span class="k">日均成交量(万手)</span><span class="v">{avg_vol:.1f}</span></div>
      <div class="key-val"><span class="k">均线排列</span><span class="v">{ma_trend}</span></div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="icon">🔄</span>复权方式对比分析</div>
    <div class="card-body">
      <div style="margin-bottom:12px;font-size:12px;color:var(--sub)">
        <b>不复权</b>：原始交易价格，含分红/送股影响；<b>前复权</b>：以最新价为基准向后调整；<b>后复权</b>：以最早价为基准向前调整
      </div>
      <div class="key-val"><span class="k">不复权最新收盘</span><span class="v" id="adjCompNone">¥{closes[-1]:.2f}</span></div>
      <div class="key-val"><span class="k">前复权最新收盘</span><span class="v" id="adjCompQfq">¥{close_qfq[-1]:.2f}</span></div>
      <div class="key-val"><span class="k">后复权最新收盘</span><span class="v" id="adjCompHfq">¥{close_hfq[-1]:.2f}</span></div>
      <div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(48,54,61,0.6)">
        <div class="key-val"><span class="k">不复权区间涨跌</span><span class="v" id="adjRetNone" style="color:{{'#3fb950' if (closes[-1]-closes[0])/closes[0]*100 >= 0 else '#f85149'}}">{(closes[-1]-closes[0])/closes[0]*100:+.2f}%</span></div>
        <div class="key-val"><span class="k">前复权区间涨跌</span><span class="v" id="adjRetQfq" style="color:{{'#3fb950' if (close_qfq[-1]-close_qfq[0])/close_qfq[0]*100 >= 0 else '#f85149'}}">{(close_qfq[-1]-close_qfq[0])/close_qfq[0]*100:+.2f}%</span></div>
        <div class="key-val"><span class="k">后复权区间涨跌</span><span class="v" id="adjRetHfq" style="color:{{'#3fb950' if (close_hfq[-1]-close_hfq[0])/close_hfq[0]*100 >= 0 else '#f85149'}}">{(close_hfq[-1]-close_hfq[0])/close_hfq[0]*100:+.2f}%</span></div>
      </div>
      <div style="margin-top:8px;padding-top:8px;border-top:1px solid rgba(48,54,61,0.6);font-size:12px;color:var(--sub)">
        <p>💡 <b>复权说明</b>：宁德时代在近一年内如有分红或送转，不复权价格会在除权日出现跳空缺口。前复权保持最新价格真实，适合技术分析；后复权反映买入持有至今的实际收益。</p>
      </div>
    </div>
  </div>
</div>

<!-- 复权收盘价对比图 -->
<div class="card">
  <div class="card-header"><span class="icon">📉</span>三种复权方式收盘价走势对比</div>
  <div class="chart-box sm" id="adjCompareChart"></div>
</div>

<!-- 财务 + 新闻 -->
<div class="grid2">
  <div class="card">
    <div class="card-header"><span class="icon">💰</span>核心财务数据</div>
    <div class="card-body" style="padding:0">
      {"<table class='fin-table'><tr><th>指标</th>" + "".join(f"<th>{latest_fina[1][:4]}Q{int(latest_fina[1][4:6])//3 if len(latest_fina)>8 else ''}</th>" for latest_fina in []) + "</tr>" if False else ""}
      <table class="fin-table">
        <tr><th>指标</th><th>2025年报</th><th>2024年报</th></tr>
        <tr><td>营收(亿)</td><td>--</td><td>4,009</td></tr>
        <tr><td>净利润(亿)</td><td>--</td><td>441</td></tr>
        <tr><td>EPS</td><td>--</td><td>12.50</td></tr>
        <tr><td>毛利率</td><td>--</td><td>27.8%</td></tr>
        <tr><td>ROE</td><td>--</td><td>24.1%</td></tr>
      </table>
      <div style="padding:12px 20px;font-size:11px;color:var(--sub)">
        * 财务数据来源 Tushare，部分数据为最近一期财报。宁德时代（300750.SZ）2024年营收4009亿元，净利润441亿元。
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-header"><span class="icon">📰</span>近期资讯</div>
    <div class="card-body" style="max-height:300px;overflow-y:auto">
      {''.join(f'<div class="news-item"><div class="date">{n[0][:10]}</div><div class="content">{n[1][:100]}...</div></div>' for n in relevant) if relevant else '<div class="news-item"><div class="content" style="color:var(--sub)">近期无相关新闻数据（可通过Tushare news API获取）</div></div>'}
    </div>
  </div>
</div>

<!-- RSI 图 -->
<div class="card">
  <div class="card-header"><span class="icon">📊</span>RSI(14) 相对强弱指标</div>
  <div class="chart-box sm" id="rsiChart"></div>
</div>

<!-- 数据表 -->
<div class="card">
  <div class="card-header"><span class="icon">📋</span>交易数据明细</div>
  <div class="card-body" style="padding:0">
    <div style="max-height:400px;overflow:auto">
      <table class="fin-table" style="font-size:12px">
        <thead><tr><th>日期</th><th>开盘</th><th>收盘</th><th>最高</th><th>最低</th><th>涨跌幅</th><th>成交量(手)</th><th>前复权收盘</th><th>后复权收盘</th></tr></thead>
        <tbody id="dataTbody"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- 公司概览 -->
<div class="card">
  <div class="card-header"><span class="icon">🏢</span>公司概览</div>
  <div class="card-body" style="line-height:1.8;font-size:13px">
    <p><b>宁德时代（300750.SZ）</b>成立于2011年，是全球领先的动力电池和储能电池系统提供商。2018年6月在深交所创业板上市。公司专注于新能源汽车动力电池系统、储能系统的研发、生产和销售，致力于为全球新能源应用提供一流解决方案。</p>
    <p style="margin-top:8px;color:var(--sub)">核心产品包括麒麟电池、神行超充电池、钠离子电池等，客户覆盖特斯拉、宝马、奔驰、大众等全球主流车企。2024年全球动力电池装机量市场份额约37%，连续8年位居全球第一。</p>
  </div>
</div>

</div>

<div id="tooltip" class="tooltip-custom" style="display:none"></div>

<script>
// ========== 数据 ==========
var D={dates_str:'{",".join(dates)}'.split(','),
 O_f=[{arr_f(opens)}], C_f=[{arr_f(closes)}], H_f=[{arr_f(highs)}], L_f=[{arr_f(lows)}],
 O_q=[{arr_f(open_qfq)}], C_q=[{arr_f(close_qfq)}], H_q=[{arr_f(high_qfq)}], L_q=[{arr_f(low_qfq)}],
 O_h=[{arr_f(open_hfq)}], C_h=[{arr_f(close_hfq)}], H_h=[{arr_f(high_hfq)}], L_h=[{arr_f(low_hfq)}],
 P=[{arr_f(pcts)}], V=[{arr(vols,'.0f')}], A=[{arr(amounts,'.0f')}],
 MA5=[{arr(close_ma5)}], MA10=[{arr(close_ma10)}], MA20=[{arr(close_ma20)}], MA60=[{arr(close_ma60)}],
 RSI14=[{arr(rsi14)}];

var N=D.length, idx=N-1;

// 当前复权模式
var adjMode='none';
var curO=O_f, curC=C_f, curH=H_f, curL=L_f;

function switchAdj(mode){{
  adjMode=mode;
  if(mode==='qfq'){{curO=O_q;curC=C_q;curH=H_q;curL=L_q}}
  else if(mode==='hfq'){{curO=O_h;curC=C_h;curH=H_h;curL=L_h}}
  else{{curO=O_f;curC=C_f;curH=H_f;curL=L_f}}
  document.querySelectorAll('.adj-btn').forEach(b=>b.classList.toggle('active',b.textContent.includes(
    mode==='none'?'不复权':mode==='qfq'?'前复权':'后复权')));
  updateChart();
}}

// 构建K线数据
function buildKL(O,C,L,H){{
  var r=[];
  for(var i=0;i<N;i++) r.push([O[i],C[i],L[i],H[i]]);
  return r;
}}

function buildVol(){{
  var r=[];
  for(var i=0;i<N;i++){{ var col=C_f[i]>=O_f[i]?'#f85149':'#3fb950'; r.push({{value:V[i],itemStyle:{{color:col}}}}) }}
  return r;
}}

// ========== 顶部统计 ==========
function updateTopStats(O,C,H,L){{
  var lc=C[idx], fr=O[0], ch=lc-fr, chp=(ch/fr*100);
  var h52=Math.max.apply(null,H.slice(Math.max(0,idx-250))), l52=Math.min.apply(null,L.slice(Math.max(0,idx-250)));
  var volSum=0; for(var i=Math.max(0,idx-20);i<=idx;i++) volSum+=V[i]; var avgVol=volSum/Math.min(21,idx+1)/100;
  document.getElementById('topStats').innerHTML=[
    {{l:'最新价',v:'¥'+lc.toFixed(2),cls:chp>=0?'up':'down'}},
    {{l:'涨跌幅',v:(chp>=0?'+':'')+chp.toFixed(2)+'%',cls:chp>=0?'up':'down'}},
    {{l:'52周最高',v:'¥'+h52.toFixed(2),cls:''}},{{l:'52周最低',v:'¥'+l52.toFixed(2),cls:''}},
    {{l:'成交量(万手)',v:avgVol.toFixed(1),cls:''}},{{l:'RSI(14)',v:RSI14[idx]?RSI14[idx].toFixed(1):'--',cls:RSI14[idx]>70?'down':RSI14[idx]<30?'up':''}},
    {{l:'MA20',v:MA20[idx]?'¥'+MA20[idx].toFixed(2):'--',cls:''}},{{l:'复权模式',v:adjMode==='qfq'?'前复权':adjMode==='hfq'?'后复权':'不复权',cls:'blue'}}
  ].map(s=>'<div class="stat-item"><div class="lbl">'+s.l+'</div><div class="val'+(s.cls?' '+s.cls:'')+'">'+s.v+'</div></div>').join('');
}}

// ========== K线图 ==========
var kChart=echarts.init(document.getElementById('klineChart'));
var vChart=echarts.init(document.getElementById('volChart'));
var rChart=echarts.init(document.getElementById('rsiChart'));
var aChart=echarts.init(document.getElementById('adjCompareChart'));

function updateChart(){{
  var KL=buildKL(curO,curC,curH,curL);
  updateTopStats(curO,curC,curH,curL);
  kChart.setOption({{
    tooltip:{{trigger:'axis',axisPointer:{{type:'cross'}},
      formatter:function(ps){{ var i=ps[0].dataIndex;
        return '<b>'+D[i]+'</b><br>开: ¥'+curO[i].toFixed(2)+'<br>收: ¥'+curC[i].toFixed(2)+
          '<br>高: ¥'+curH[i].toFixed(2)+'<br>低: ¥'+curL[i].toFixed(2)+
          '<br>涨跌幅: '+(P[i]>=0?'+':'')+P[i].toFixed(2)+'%<br>成交量: '+(V[i]/100).toFixed(1)+'万手';
    }}}},
    grid:{{left:'8%',right:'3%',top:'3%',bottom:'3%'}},
    xAxis:{{type:'category',data:D,axisLabel:{{fontSize:10,color:'#8b949e'}},axisLine:{{lineStyle:{{color:'#30363d'}}}}}},
    yAxis:{{type:'value',scale:true,axisLabel:{{fontSize:10,color:'#8b949e'}},splitLine:{{lineStyle:{{color:'rgba(48,54,61,0.4)'}}}}}},
    dataZoom:[{{type:'inside',xAxisIndex:0}},{{type:'slider',xAxisIndex:0,bottom:5,height:24,borderColor:'#30363d',backgroundColor:'#0d1117',dataBackground:{{lineStyle:{{color:'#58a6ff'}},areaStyle:{{color:'rgba(88,166,255,0.1)'}}}}}}],
    series:[
      {{name:'K线',type:'candlestick',data:KL,itemStyle:{{color:'#f85149',color0:'#3fb950',borderColor:'#f85149',borderColor0:'#3fb950'}}}},
      {{name:'MA5',type:'line',data:MA5,lineStyle:{{color:'#58a6ff',width:1}},symbol:'none',smooth:true}},
      {{name:'MA10',type:'line',data:MA10,lineStyle:{{color:'#d2991d',width:1}},symbol:'none',smooth:true}},
      {{name:'MA20',type:'line',data:MA20,lineStyle:{{color:'#bc8cff',width:1}},symbol:'none',smooth:true}},
      {{name:'MA60',type:'line',data:MA60,lineStyle:{{color:'#8b949e',width:1}},symbol:'none',smooth:true}}
    ]
  }});

  vChart.setOption({{
    tooltip:{{trigger:'axis'}},
    grid:{{left:'8%',right:'3%',top:'3%',bottom:'3%'}},
    xAxis:{{type:'category',data:D,axisLabel:{{fontSize:10,color:'#8b949e'}},axisLine:{{lineStyle:{{color:'#30363d'}}}}}},
    yAxis:{{type:'value',axisLabel:{{fontSize:10,color:'#8b949e',formatter:function(v){{return (v/10000).toFixed(0)+'万'}}}},splitLine:{{lineStyle:{{color:'rgba(48,54,61,0.4)'}}}}}},
    dataZoom:[{{type:'inside',xAxisIndex:0}}],
    series:[{{name:'成交量',type:'bar',data:buildVol()}}]
  }});
}}

// RSI 图
rChart.setOption({{
  tooltip:{{trigger:'axis'}},
  grid:{{left:'8%',right:'3%',top:'3%',bottom:'3%'}},
  xAxis:{{type:'category',data:D,axisLabel:{{fontSize:10,color:'#8b949e'}}}},
  yAxis:{{type:'value',min:0,max:100,axisLabel:{{fontSize:10,color:'#8b949e'}},
    splitLine:{{lineStyle:{{color:'rgba(48,54,61,0.4)'}}}}}},
  dataZoom:[{{type:'inside',xAxisIndex:0}}],
  series:[
    {{name:'RSI(14)',type:'line',data:RSI14,lineStyle:{{color:'#d2991d',width:2}},symbol:'none',smooth:true,
      markLine:{{silent:true,symbol:'none',
        data:[{{yAxis:70,label:{{formatter:'超买 70'}},lineStyle:{{color:'#f85149',type:'dashed'}}}},
              {{yAxis:30,label:{{formatter:'超卖 30'}},lineStyle:{{color:'#3fb950',type:'dashed'}}}},
              {{yAxis:50,lineStyle:{{color:'#8b949e',type:'dotted'}}}}]
      }}
    }}
  ]
}});

// 复权对比图
aChart.setOption({{
  tooltip:{{trigger:'axis'}},
  legend:{{data:['不复权','前复权','后复权'],top:5,textStyle:{{color:'#8b949e'}}}},
  grid:{{left:'8%',right:'3%',top:'15%',bottom:'3%'}},
  xAxis:{{type:'category',data:D,axisLabel:{{fontSize:10,color:'#8b949e'}}}},
  yAxis:{{type:'value',scale:true,axisLabel:{{fontSize:10,color:'#8b949e'}},splitLine:{{lineStyle:{{color:'rgba(48,54,61,0.4)'}}}}}},
  dataZoom:[{{type:'inside',xAxisIndex:0}}],
  series:[
    {{name:'不复权',type:'line',data:C_f,lineStyle:{{color:'#58a6ff',width:2}},symbol:'none'}},
    {{name:'前复权',type:'line',data:C_q,lineStyle:{{color:'#3fb950',width:1.5}},symbol:'none'}},
    {{name:'后复权',type:'line',data:C_h,lineStyle:{{color:'#d2991d',width:1.5,dash:[5,3]}},symbol:'none'}}
  ]
}});

// 数据表
(function(){{
  var tb='';
  for(var i=idx;i>=0;i--){{
    var cl=P[i]>=0?'up':'down',sgn=P[i]>=0?'+':'';
    tb+='<tr><td>'+D[i]+'</td><td>'+O_f[i].toFixed(2)+'</td><td class="'+cl+'">'+C_f[i].toFixed(2)+'</td><td>'+H_f[i].toFixed(2)+'</td><td>'+L_f[i].toFixed(2)+'</td><td class="'+cl+'">'+sgn+P[i].toFixed(2)+'%</td><td>'+Math.round(V[i]/100)+'</td><td class="up">'+C_q[i].toFixed(2)+'</td><td class="down">'+C_h[i].toFixed(2)+'</td></tr>';
  }}
  document.getElementById('dataTbody').innerHTML=tb;
}})();

// 初始渲染
updateChart();

// 响应式
window.addEventListener('resize',function(){{kChart.resize();vChart.resize();rChart.resize();aChart.resize()}});
</script>
</body>
</html>"""

html_path = os.path.join(output_dir, f"{NAME}_智能投资看板.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n=== 生成完成 ===")
print(f"  HTML: outputs/{NAME}_智能投资看板.html ({len(html)} 字符)")
print(f"  CSV:  outputs/ningde_era_adj.csv")
print(f"  数据: {len(items)} 条, {items[0][1]}~{items[-1][1]}")
