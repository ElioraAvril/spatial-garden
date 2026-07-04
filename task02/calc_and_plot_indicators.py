# -*- coding: utf-8 -*-
"""
宁德时代(300750.SZ) 技术指标计算与可视化
- RSI (14日)
- MACD (12, 26, 9)
- Bollinger Bands (20, 2)

四面板专业图表:
  面板1: K线图 + 布林带 + EMA双线
  面板2: 成交量
  面板3: RSI(14) + 超买超卖线
  面板4: MACD(DIF/DEA/柱状图)
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

print("=" * 70)
print("  宁德时代 (300750.SZ) 技术指标计算与可视化")
print("=" * 70)

# ============================================================
# 1. 加载数据
# ============================================================
df = pd.read_csv(
    'outputs/ningde_era_daily.csv',
    encoding='utf-8-sig',
    parse_dates=['trade_date']
)
df = df.sort_values('trade_date').reset_index(drop=True).copy()
n = len(df)

print(f"\n  数据: {n} 条, {df['trade_date'].min().strftime('%Y-%m-%d')} ~ {df['trade_date'].max().strftime('%Y-%m-%d')}")

close = df['close'].values
high  = df['high'].values
low   = df['low'].values
open_ = df['open'].values
vol   = df['vol'].values
dates = df['trade_date']
date_nums = mdates.date2num(dates)

# ============================================================
# 2. RSI (Wilder's smoothing)
# ============================================================
def calc_rsi(prices, period=14):
    n = len(prices)
    delta = np.zeros(n)
    delta[1:] = np.diff(prices)
    gain = np.maximum(delta, 0)
    loss = np.maximum(-delta, 0)

    avg_gain = np.full(n, np.nan)
    avg_loss = np.full(n, np.nan)
    avg_gain[period] = gain[1:period+1].mean()
    avg_loss[period] = loss[1:period+1].mean()

    for i in range(period + 1, n):
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i]) / period

    rsi = np.full(n, np.nan)
    for i in range(period, n):
        if avg_loss[i] == 0:
            rsi[i] = 100.0
        else:
            rsi[i] = 100.0 - 100.0 / (1.0 + avg_gain[i] / avg_loss[i])
    return rsi

rsi = calc_rsi(close, 14)

# ============================================================
# 3. EMA / MACD
# ============================================================
def ema(series, period):
    k = 2.0 / (period + 1.0)
    result = np.zeros_like(series, dtype=float)
    result[0] = series[0]
    for i in range(1, len(series)):
        result[i] = series[i] * k + result[i-1] * (1.0 - k)
    return result

ema12 = ema(close, 12)
ema26 = ema(close, 26)
dif  = ema12 - ema26
dea  = ema(dif, 9)
macd_bar = 2.0 * (dif - dea)

# ============================================================
# 4. Bollinger Bands
# ============================================================
bb_period = 20
bb_mid = pd.Series(close).rolling(bb_period).mean().values
bb_std = pd.Series(close).rolling(bb_period).std(ddof=0).values
bb_up  = bb_mid + 2.0 * bb_std
bb_dn  = bb_mid - 2.0 * bb_std

# ============================================================
# 5. 统计摘要
# ============================================================
print("\n" + "-" * 60)
print("  指标统计摘要")
print("-" * 60)
print(f"  RSI(14) 最新: {rsi[-1]:.2f}")
print(f"    >70 天数: {(rsi > 70).sum()},  <30 天数: {(rsi < 30).sum()}")

golden_cross = ((dif > dea) & (np.roll(dif < dea, 1))).sum()
dead_cross   = ((dif < dea) & (np.roll(dif > dea, 1))).sum()
print(f"  MACD 最新: DIF={dif[-1]:.2f}, DEA={dea[-1]:.2f}, BAR={macd_bar[-1]:.2f}")
print(f"    金叉: {int(golden_cross)}次,  死叉: {int(dead_cross)}次")

band_width = bb_up[-1] - bb_dn[-1] if not np.isnan(bb_up[-1]) else np.nan
print(f"  BB 最新: 中轨={bb_mid[-1]:.2f}, 上轨={bb_up[-1]:.2f}, 下轨={bb_dn[-1]:.2f}, 带宽={band_width:.2f}")

# ============================================================
# 6. 可视化 —— 四面板专业图表
# ============================================================
print("\n  绘制可视化图谱...")

RED    = '#E24B4A'
GREEN  = '#1D9E75'
PURPLE = '#534AB7'
CORAL  = '#F0997B'
GRAY   = '#888780'
DARK   = '#2C2C2A'
BLUE_L = '#B5D4F4'
BLUE_M = '#378ADD'
BLUE_BG= '#E6F1FB'

fig = plt.figure(figsize=(24, 15))
fig.patch.set_facecolor('#FAFAFA')

gs = fig.add_gridspec(4, 1, height_ratios=[2.5, 0.8, 1.0, 1.0],
                      hspace=0.12, left=0.045, right=0.985, top=0.955, bottom=0.035)

ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1], sharex=ax1)
ax3 = fig.add_subplot(gs[2], sharex=ax1)
ax4 = fig.add_subplot(gs[3], sharex=ax1)

# K线宽度（以天为单位）
k_width = 0.65

# ---- Panel 1: 价格 + 布林带 + EMA ----
ax1.fill_between(dates, bb_up, bb_dn, color=BLUE_BG, alpha=0.35, edgecolor='none')
ax1.plot(dates, bb_up,  color=BLUE_L, lw=1.2, alpha=0.9, label='上轨 (+2σ)')
ax1.plot(dates, bb_mid, color=BLUE_M, lw=0.8, alpha=0.6, ls='--', label='中轨 (SMA20)')
ax1.plot(dates, bb_dn,  color=BLUE_L, lw=1.2, alpha=0.9, label='下轨 (-2σ)')

for i in range(n):
    o, c, h, l = open_[i], close[i], high[i], low[i]
    color = RED if c >= o else GREEN
    ax1.plot([dates.iloc[i], dates.iloc[i]], [l, h], color=color, lw=0.7, solid_capstyle='round')
    dn = date_nums[i]
    body_bottom = min(o, c)
    body_height = abs(c - o) if abs(c - o) > 0.01 else 0.03
    ax1.add_patch(Rectangle((dn - k_width/2, body_bottom), k_width, body_height,
                             fc=color, ec='none', alpha=0.92))

ax1.plot(dates, ema12, color=PURPLE, lw=0.8, alpha=0.55, label='EMA12')
ax1.plot(dates, ema26, color=CORAL, lw=0.8, alpha=0.55, label='EMA26')

ax1.set_ylabel('价格 / 元', fontsize=11, color=DARK)
ax1.set_title('宁德时代 300750.SZ  技术指标综合面板', fontsize=15, weight='500',
              color=DARK, pad=12)
ax1.legend(loc='upper left', fontsize=8.5, framealpha=0.85, ncol=3, borderpad=0.5)
ax1.tick_params(labelsize=9, colors=DARK)
ax1.grid(axis='y', alpha=0.22, lw=0.5)

# ---- Panel 2: 成交量 ----
bar_colors = [RED if close[i] >= open_[i] else GREEN for i in range(n)]
vol_scaled = vol / 1e4
ax2.bar(date_nums, vol_scaled, width=k_width, color=bar_colors, alpha=0.8, ec='none')
ax2.axhline(y=vol_scaled.mean(), color=GRAY, lw=0.6, ls='--', alpha=0.4)
ax2.set_ylabel('成交量\n/ 万手', fontsize=10, color=DARK)
ax2.tick_params(labelsize=9, colors=DARK)
ax2.grid(axis='y', alpha=0.22, lw=0.5)

# ---- Panel 3: RSI ----
ax3.plot(dates, rsi, color=PURPLE, lw=1.3, label='RSI(14)')
ax3.axhline(y=70, color=RED,   lw=0.8, ls='--', alpha=0.55, label='超买 70')
ax3.axhline(y=30, color=GREEN, lw=0.8, ls='--', alpha=0.55, label='超卖 30')
ax3.axhline(y=50, color=GRAY,  lw=0.4, ls=':',  alpha=0.30)
ax3.fill_between(dates, 70, 100, color=RED,   alpha=0.06)
ax3.fill_between(dates,  0,  30, color=GREEN, alpha=0.06)
ax3.set_ylabel('RSI', fontsize=10, color=DARK)
ax3.set_ylim(0, 100)
ax3.legend(loc='upper left', fontsize=8, framealpha=0.85, ncol=3, borderpad=0.5)
ax3.tick_params(labelsize=9, colors=DARK)
ax3.grid(axis='y', alpha=0.22, lw=0.5)

# ---- Panel 4: MACD ----
prev_bar = np.full(n, np.nan)
prev_bar[1:] = macd_bar[:-1]
for i in range(n):
    if np.isnan(macd_bar[i]):
        continue
    cur = macd_bar[i]
    prv = prev_bar[i] if not np.isnan(prev_bar[i]) else 0
    c = RED if cur >= prv else GREEN
    ax4.bar(date_nums[i], cur, width=k_width, color=c, alpha=0.8, ec='none')

ax4.plot(dates, dif, color=PURPLE, lw=0.95, label='DIF')
ax4.plot(dates, dea, color=CORAL, lw=0.95, label='DEA')
ax4.axhline(y=0, color=GRAY, lw=0.5, alpha=0.45)
ax4.set_ylabel('MACD', fontsize=10, color=DARK)
ax4.legend(loc='upper left', fontsize=8, framealpha=0.85, ncol=2, borderpad=0.5)
ax4.tick_params(labelsize=9, colors=DARK)
ax4.grid(axis='y', alpha=0.22, lw=0.5)

# X轴格式化
for ax in [ax1, ax2, ax3, ax4]:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.set_xlim(date_nums[0] - 1, date_nums[-1] + 1)

plt.setp([ax1.get_xticklabels(), ax2.get_xticklabels(), ax3.get_xticklabels()],
         visible=False)

# ============================================================
# 保存
# ============================================================
output_img = 'outputs/ningde_era_technical_indicators.png'
plt.savefig(output_img, dpi=150, bbox_inches='tight', facecolor='#FAFAFA')
plt.close()
print(f"  图表: {output_img}")

# ============================================================
# 7. 同时输出 HTML 交互式面板
# ============================================================
print("  生成交互式 HTML 面板...")

# 准备 JSON 数据
indicators_json = []
for i in range(n):
    if not np.isnan(rsi[i]) and not np.isnan(bb_mid[i]):
        indicators_json.append({
            'date': dates.iloc[i].strftime('%Y-%m-%d'),
            'open':  float(round(open_[i], 2)),
            'high':  float(round(high[i], 2)),
            'low':   float(round(low[i], 2)),
            'close': float(round(close[i], 2)),
            'vol':   float(round(vol[i], 0)),
            'rsi':   float(round(rsi[i], 2)),
            'dif':   float(round(dif[i], 2)),
            'dea':   float(round(dea[i], 2)),
            'macd':  float(round(macd_bar[i], 2)),
            'bb_up': float(round(bb_up[i], 2)),
            'bb_mid':float(round(bb_mid[i], 2)),
            'bb_dn': float(round(bb_dn[i], 2)),
        })

import json
html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>宁德时代 300750.SZ 技术指标面板</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif;background:#f5f5f5;color:#222}
.header{background:#fff;padding:16px 24px;border-bottom:1px solid #e0e0e0;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.header h1{font-size:18px;font-weight:500}
.header .meta{font-size:13px;color:#666}
.container{padding:16px;max-width:1400px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
.card{background:#fff;border-radius:8px;border:1px solid #e8e8e8;padding:14px 16px}
.card h2{font-size:14px;font-weight:500;color:#333;margin-bottom:10px}
.chart-wrap{position:relative;width:100%}
chart-wrap:first-of-type{height:420px}
.rsichart{height:180px}
.macdchart{height:180px}
.volchart{height:130px}
.stat-row{display:flex;gap:12px;flex-wrap:wrap}
.stat{flex:1;min-width:100px;background:#f8f8f8;border-radius:6px;padding:10px 14px;text-align:center}
.stat .lbl{font-size:12px;color:#888;margin-bottom:3px}
.stat .val{font-size:20px;font-weight:500}
.stat .sub{font-size:11px;color:#aaa;margin-top:2px}
.red{color:#e24b4a}
.green{color:#1d9e75}
.blue{color:#378add}
.purple{color:#534ab7}
.latest{font-size:12px;color:#999;margin-top:3px}
</style>
</head>
<body>

<div class="header">
<div>
<h1>宁德时代 300750.SZ  技术指标面板</h1>
<div class="meta">数据范围: ''' + indicators_json[0]['date'] + ''' ~ ''' + indicators_json[-1]['date'] + ''' | 共 ''' + str(len(indicators_json)) + ''' 个交易日</div>
</div>
<div id="statBar" class="stat-row"></div>
</div>

<div class="container">
<div class="card">
<h2>K线图 + Bollinger Bands (20, 2)</h2>
<div class="chart-wrap mainchart"><canvas id="mainChart"></canvas></div>
</div>

<div class="card">
<h2>成交量</h2>
<div class="chart-wrap volchart"><canvas id="volChart"></canvas></div>
</div>

<div class="card">
<h2>RSI (相对强弱指标, 14)</h2>
<div class="chart-wrap rsichart"><canvas id="rsiChart"></canvas></div>
</div>

<div class="card">
<h2>MACD (指数平滑异同移动平均线, 12/26/9)</h2>
<div class="chart-wrap macdchart"><canvas id="macdChart"></canvas></div>
</div>
</div>

<script>
const RAW_DATA = ''' + json.dumps(indicators_json, ensure_ascii=False) + ''';

// Derivative arrays
const dates = RAW_DATA.map(d => d.date);
const close = RAW_DATA.map(d => d.close);
const high  = RAW_DATA.map(d => d.high);
const low   = RAW_DATA.map(d => d.low);
const open  = RAW_DATA.map(d => d.open);
const vol   = RAW_DATA.map(d => d.vol);
const rsi   = RAW_DATA.map(d => d.rsi);
const dif   = RAW_DATA.map(d => d.dif);
const dea   = RAW_DATA.map(d => d.dea);
const macd  = RAW_DATA.map(d => d.macd);
const bb_up = RAW_DATA.map(d => d.bb_up);
const bb_mid= RAW_DATA.map(d => d.bb_mid);
const bb_dn = RAW_DATA.map(d => d.bb_dn);

// Candlestick colors
const csColors = close.map((c, i) => c >= open[i] ? '#E24B4A' : '#1D9E75');

// === Latest stats ===
const last = RAW_DATA[RAW_DATA.length - 1];
let statHtml = '';
statHtml += '<div class="stat"><div class="lbl">最新收盘</div><div class="val">' + last.close + '</div><div class="sub">元</div></div>';
statHtml += '<div class="stat"><div class="lbl">RSI(14)</div><div class="val ' + (last.rsi > 70 ? 'red' : last.rsi < 30 ? 'green' : '') + '">' + last.rsi + '</div><div class="sub">' + last.date + '</div></div>';
statHtml += '<div class="stat"><div class="lbl">MACD DIF</div><div class="val ' + (last.dif > 0 ? 'red' : 'green') + '">' + last.dif.toFixed(2) + '</div><div class="sub">DEA: ' + last.dea.toFixed(2) + '</div></div>';
statHtml += '<div class="stat"><div class="lbl">BB 中轨</div><div class="val purple">' + last.bb_mid.toFixed(2) + '</div><div class="sub">带宽: ' + (last.bb_up - last.bb_dn).toFixed(2) + '</div></div>';
document.getElementById('statBar').innerHTML = statHtml;

// Chart.js plugin: candlestick
const candlestickPlugin = {
  id: 'candlestick',
  afterDatasetsDraw(chart, args, opts) {
    const ctx = chart.ctx;
    const meta0 = chart.getDatasetMeta(0);
    if (!meta0 || !meta0.data) return;
    const xScale = chart.scales.x;
    const yScale = chart.scales.y;
    const barWidth = xScale.width / Math.max(dates.length, 1) * 0.7;
    ctx.save();
    for (let i = 0; i < dates.length; i++) {
      const x = xScale.getPixelForValue(i);
      const o = yScale.getPixelForValue(open[i]);
      const c = yScale.getPixelForValue(close[i]);
      const h = yScale.getPixelForValue(high[i]);
      const l = yScale.getPixelForValue(low[i]);
      const color = close[i] >= open[i] ? '#E24B4A' : '#1D9E75';
      // Wick
      ctx.strokeStyle = color;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.moveTo(x, l);
      ctx.lineTo(x, h);
      ctx.stroke();
      // Body
      ctx.fillStyle = color;
      const top = Math.min(o, c);
      const bottom = Math.max(o, c);
      ctx.fillRect(x - barWidth/2, top, barWidth, Math.max(bottom - top, 0.5));
    }
    ctx.restore();
  }
};

const commonOptions = { responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { grid: { display: false }, ticks: { maxTicksLimit: 18, font: { size: 10 }, autoSkip: true, maxRotation: 45 } },
  }
};

// ---- Main Chart: BB + Candlestick ----
new Chart(document.getElementById('mainChart'), {
  type: 'line',
  plugins: [candlestickPlugin],
  data: {
    labels: dates,
    datasets: [
      { data: close, borderColor: 'rgba(0,0,0,0)', pointRadius: 0 },
      { label: '上轨', data: bb_up, borderColor: '#B5D4F4', borderWidth: 1.2, pointRadius: 0, fill: false },
      { label: '中轨', data: bb_mid, borderColor: '#378ADD', borderWidth: 0.8, borderDash: [4,4], pointRadius: 0, fill: false },
      { label: '下轨', data: bb_dn, borderColor: '#B5D4F4', borderWidth: 1.2, pointRadius: 0, fill: {target: '+1', above: 'rgba(55,138,221,0.06)', below: 'rgba(55,138,221,0.06)'} },
      { label: 'EMA12', data: ema(close, 12), borderColor: '#534AB7', borderWidth: 0.8, pointRadius: 0, fill: false },
      { label: 'EMA26', data: ema(close, 26), borderColor: '#F0997B', borderWidth: 0.8, pointRadius: 0, fill: false },
    ]
  },
  options: {
    ...commonOptions,
    scales: {
      ...commonOptions.scales,
      y: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 }, callback: v => v.toFixed(0) } }
    },
    plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: { size: 11 }, filter: item => item.text !== '' } } }
  }
});

// ---- Volume Chart ----
new Chart(document.getElementById('volChart'), {
  type: 'bar',
  data: {
    labels: dates,
    datasets: [{ data: vol.map(v => v/10000), backgroundColor: csColors, borderWidth: 0 }]
  },
  options: {
    ...commonOptions,
    scales: { ...commonOptions.scales, y: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 }, callback: v => v.toFixed(0) } } }
  }
});

// ---- RSI ----
new Chart(document.getElementById('rsiChart'), {
  type: 'line',
  data: {
    labels: dates,
    datasets: [
      { label: 'RSI(14)', data: rsi, borderColor: '#534AB7', borderWidth: 1.5, pointRadius: 0, fill: false },
      { label: '超买 70', data: Array(dates.length).fill(70), borderColor: '#E24B4A', borderWidth: 0.8, borderDash: [4,4], pointRadius: 0, fill: false },
      { label: '超卖 30', data: Array(dates.length).fill(30), borderColor: '#1D9E75', borderWidth: 0.8, borderDash: [4,4], pointRadius: 0, fill: false },
    ]
  },
  options: {
    ...commonOptions,
    scales: {
      ...commonOptions.scales,
      y: { min: 0, max: 100, grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 }, stepSize: 20 } }
    },
    plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: { size: 10 }, filter: item => item.text !== '' } } }
  }
});

// ---- MACD ----
const macdColors = macd.map((v,i) => {
  if (i === 0) return v >= 0 ? '#E24B4A' : '#1D9E75';
  return v >= macd[i-1] ? '#E24B4A' : '#1D9E75';
});
new Chart(document.getElementById('macdChart'), {
  type: 'bar',
  data: {
    labels: dates,
    datasets: [
      { type: 'bar', label: 'MACD', data: macd, backgroundColor: macdColors, borderWidth: 0, order: 2 },
      { type: 'line', label: 'DIF', data: dif, borderColor: '#534AB7', borderWidth: 1.2, pointRadius: 0, fill: false, order: 1 },
      { type: 'line', label: 'DEA', data: dea, borderColor: '#F0997B', borderWidth: 1.2, pointRadius: 0, fill: false, order: 1 },
    ]
  },
  options: {
    ...commonOptions,
    scales: { ...commonOptions.scales, y: { grid: { color: '#f0f0f0' }, ticks: { font: { size: 10 } } } },
    plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: { size: 10 }, filter: item => item.text !== '' } } }
  }
});

// EMA helper
function ema(arr, period) {
  const k = 2 / (period + 1);
  const out = [arr[0]];
  for (let i = 1; i < arr.length; i++) { out.push(arr[i] * k + out[i-1] * (1 - k)); }
  return out;
}
</script>
</body>
</html>'''

html_path = 'outputs/ningde_era_interactive_dashboard.html'
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
print(f"  HTML: {html_path}")

print("\n" + "=" * 70)
print("  全部完成。")
print("=" * 70)
