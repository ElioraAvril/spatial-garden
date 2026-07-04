# -*- coding: utf-8 -*-
"""
宁德时代(300750.SZ) 夏普比率 (Sharpe Ratio) 介绍、计算与可视化
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# 1. 加载数据
# ============================================================
df = pd.read_csv('outputs/ningde_era_daily.csv', encoding='utf-8-sig', parse_dates=['trade_date'])
df = df.sort_values('trade_date').reset_index(drop=True)
close = df['close'].values
dates = df['trade_date']
n = len(df)

df['daily_ret'] = df['close'].pct_change()
daily_ret = df['daily_ret'].dropna().values
ret_dates = dates[1:]
n_ret = len(daily_ret)

# ============================================================
# 2. 参数
# ============================================================
RISK_FREE_RATE = 0.015
TRADING_DAYS   = 252
ROLLING_WINDOW = 60
rf_daily = RISK_FREE_RATE / TRADING_DAYS

# ============================================================
# 3. 整体夏普比率
# ============================================================
mean_daily_ret = np.mean(daily_ret)
std_daily_ret  = np.std(daily_ret, ddof=1)
ann_ret  = mean_daily_ret * TRADING_DAYS
ann_vol  = std_daily_ret  * np.sqrt(TRADING_DAYS)
ann_excess = ann_ret - RISK_FREE_RATE
sharpe     = ann_excess / ann_vol

# ============================================================
# 4. 滚动夏普比率
# ============================================================
rolling_ann_ret = np.full(n, np.nan)
rolling_ann_vol = np.full(n, np.nan)
rolling_sharpe  = np.full(n, np.nan)
for i in range(ROLLING_WINDOW, n):
    win = daily_ret[i - ROLLING_WINDOW : i]
    mu  = np.mean(win)
    sig = np.std(win, ddof=1)
    r_ann = mu * TRADING_DAYS
    v_ann = sig * np.sqrt(TRADING_DAYS)
    rolling_ann_ret[i] = r_ann
    rolling_ann_vol[i] = v_ann
    rolling_sharpe[i]  = (r_ann - RISK_FREE_RATE) / v_ann if v_ann > 0 else np.nan

# ============================================================
# 5. 累计收益与回撤
# ============================================================
cum_ret  = np.cumprod(1 + daily_ret)
peak     = np.maximum.accumulate(cum_ret)
drawdown = (cum_ret - peak) / peak * 100
max_dd   = drawdown.min()

# ============================================================
# 6. 输出
# ============================================================
print("=" * 65)
print("  宁德时代 (300750.SZ)  夏普比率分析报告")
print("=" * 65)
print(f"\n  无风险利率 (Rf): {RISK_FREE_RATE*100:.2f}% / 年, 交易日/年: {TRADING_DAYS}")
print(f"  数据: {dates.min().strftime('%Y-%m-%d')} ~ {dates.max().strftime('%Y-%m-%d')} ({n_ret}条)")
print(f"\n  整体夏普比率:")
print(f"    年化收益率:     {ann_ret*100:+.2f}%")
print(f"    年化波动率:     {ann_vol*100:.2f}%")
print(f"    年化超额收益:    {ann_excess*100:+.2f}%")
print(f"    夏普比率:        {sharpe:.4f}")
print(f"\n  滚动夏普比率 ({ROLLING_WINDOW}日):")
print(f"    最新: {rolling_sharpe[-1]:.4f}, 最大: {np.nanmax(rolling_sharpe):.4f}, 最小: {np.nanmin(rolling_sharpe):.4f}")
idx_max = np.nanargmax(rolling_sharpe)
idx_min = np.nanargmin(rolling_sharpe)
print(f"    最大日: {dates.iloc[idx_max].strftime('%Y-%m-%d')}, 最小日: {dates.iloc[idx_min].strftime('%Y-%m-%d')}")
pos_ratio = (daily_ret > 0).sum() / n_ret * 100
neg_ratio = (daily_ret < 0).sum() / n_ret * 100
print(f"\n  风险指标:")
print(f"    最大回撤:         {max_dd:.2f}%")
print(f"    收益回撤比:        {ann_ret*100/abs(max_dd) if max_dd != 0 else 0:.4f}")
print(f"    正收益占比:        {pos_ratio:.1f}%")
print(f"    偏度:              {pd.Series(daily_ret).skew():.3f}")
print(f"    峰度:              {pd.Series(daily_ret).kurtosis():.3f}")

# ============================================================
# 7. Matplotlib 四面板可视化
# ============================================================
print("\n  绘制静态图表...")

RED, GREEN = '#E24B4A', '#1D9E75'
PURPLE, CORAL, GRAY, DARK = '#534AB7', '#F0997B', '#888780', '#2C2C2A'
BLUE_L, BLUE_M = '#B5D4F4', '#378ADD'

fig = plt.figure(figsize=(22, 15))
fig.patch.set_facecolor('#FAFAFA')
gs = fig.add_gridspec(4, 1, height_ratios=[1.2, 1.1, 1.0, 1.0],
                      hspace=0.18, left=0.06, right=0.98, top=0.945, bottom=0.04)

ax1 = fig.add_subplot(gs[0])
ax2 = fig.add_subplot(gs[1], sharex=ax1)
ax3 = fig.add_subplot(gs[2], sharex=ax1)
ax4 = fig.add_subplot(gs[3])

# Panel 1: 累计收益 + 回撤
c = RED if cum_ret[-1] >= 1.0 else GREEN
ax1.fill_between(ret_dates, 1.0, cum_ret, color=c, alpha=0.12)
ax1.plot(ret_dates, cum_ret, color=c, lw=1.8, label='cumulative return (base=1)')
ax1.axhline(y=1.0, color=GRAY, lw=0.5, ls='--', alpha=0.5)
ax1.set_ylabel('cumulative NAV', fontsize=11, color=DARK)
ax1.legend(loc='upper left', fontsize=9, framealpha=0.85)
ax1.tick_params(labelsize=9, colors=DARK)
ax1.grid(axis='y', alpha=0.22, lw=0.5)

ax1b = ax1.twinx()
ax1b.fill_between(ret_dates, drawdown, 0, color=RED, alpha=0.15)
ax1b.plot(ret_dates, drawdown, color=RED, lw=0.9, alpha=0.7, label='drawdown %')
ax1b.set_ylabel('drawdown %', fontsize=10, color=RED)
ax1b.tick_params(labelsize=9, colors=RED)
ax1b.legend(loc='upper right', fontsize=9, framealpha=0.85)

ax1.set_title('CATL 300750.SZ  Sharpe Ratio Analysis  |  Sharpe={:.4f}  |  Ann.Ret={:.2f}%  |  Ann.Vol={:.2f}%'.format(
    sharpe, ann_ret*100, ann_vol*100), fontsize=14, weight='500', color=DARK, pad=10)

# Panel 2: 滚动年化收益率 & 波动率
ax2.plot(dates, rolling_ann_ret*100, color=PURPLE, lw=1.2, label='rolling ann.ret. ({:d}d)'.format(ROLLING_WINDOW))
ax2.plot(dates, rolling_ann_vol*100, color=CORAL, lw=1.2, label='rolling ann.vol. ({:d}d)'.format(ROLLING_WINDOW))
ax2.axhline(y=ann_ret*100, color=PURPLE, lw=0.6, ls=':', alpha=0.5)
ax2.axhline(y=ann_vol*100, color=CORAL, lw=0.6, ls=':', alpha=0.5)
ax2.axhline(y=RISK_FREE_RATE*100, color=GRAY, lw=0.6, ls='--', alpha=0.5, label='Rf={:.1f}%'.format(RISK_FREE_RATE*100))
ax2.set_ylabel('%', fontsize=10, color=DARK)
ax2.legend(loc='upper left', fontsize=9, framealpha=0.85, ncol=3)
ax2.tick_params(labelsize=9, colors=DARK)
ax2.grid(axis='y', alpha=0.22, lw=0.5)

# Panel 3: 滚动夏普比率
ax3.plot(dates, rolling_sharpe, color=BLUE_M, lw=1.4, label='rolling Sharpe ({:d}d)'.format(ROLLING_WINDOW))
ax3.axhline(y=sharpe, color=BLUE_M, lw=0.7, ls='--', alpha=0.45, label='overall Sharpe={:.4f}'.format(sharpe))
ax3.axhline(y=0, color=GRAY, lw=0.5, alpha=0.4)
ax3.fill_between(dates, 0, np.maximum(rolling_sharpe, 0), color=GREEN, alpha=0.10)
ax3.fill_between(dates, 0, np.minimum(rolling_sharpe, 0), color=RED, alpha=0.10)
ax3.set_ylabel('Sharpe Ratio', fontsize=10, color=DARK)
ax3.legend(loc='upper left', fontsize=9, framealpha=0.85)
ax3.tick_params(labelsize=9, colors=DARK)
ax3.grid(axis='y', alpha=0.22, lw=0.5)

# Panel 4: 日收益率分布
dr_pct = daily_ret * 100
counts, bins, patches = ax4.hist(dr_pct, bins=40, color=BLUE_M, alpha=0.7, edgecolor='white', lw=0.3)
ax4.axvline(x=mean_daily_ret*100, color=PURPLE, lw=1.2, label='mean {:.3f}%'.format(mean_daily_ret*100))
ax4.axvline(x=mean_daily_ret*100+std_daily_ret*100, color=CORAL, lw=0.8, ls='--', label='+1 sigma')
ax4.axvline(x=mean_daily_ret*100-std_daily_ret*100, color=CORAL, lw=0.8, ls='--', label='-1 sigma')
ax4.axvline(x=rf_daily*100, color=GRAY, lw=0.7, ls=':', alpha=0.6, label='Rf daily {:.4f}%'.format(rf_daily*100))

xn = np.linspace(dr_pct.min(), dr_pct.max(), 200)
pdf = (1/(std_daily_ret*100*np.sqrt(2*np.pi))) * np.exp(-0.5*((xn-mean_daily_ret*100)/(std_daily_ret*100))**2)
ax4.plot(xn, pdf*counts.max()/pdf.max(), color=DARK, lw=1.0, alpha=0.5, label='normal fit')
ax4.set_xlabel('daily return %', fontsize=10, color=DARK)
ax4.set_ylabel('frequency', fontsize=10, color=DARK)
ax4.legend(loc='upper right', fontsize=8, framealpha=0.85)
ax4.tick_params(labelsize=9, colors=DARK)
ax4.grid(axis='y', alpha=0.22, lw=0.5)

t = 'mean={:.3f}% | std={:.3f}%\nskew={:.3f} | kurt={:.3f}\npos={:.1f}% | neg={:.1f}%'.format(
    mean_daily_ret*100, std_daily_ret*100, pd.Series(daily_ret).skew(), pd.Series(daily_ret).kurtosis(), pos_ratio, neg_ratio)
ax4.text(0.98, 0.95, t, transform=ax4.transAxes, fontsize=8, color=DARK, va='top', ha='right',
         bbox=dict(boxstyle='round,pad=0.4', fc='white', alpha=0.85, ec='#d0d0d0'))

for ax in [ax1, ax2, ax3]:
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.set_xlim(dates.iloc[0], dates.iloc[-1])

plt.setp([ax1.get_xticklabels(), ax2.get_xticklabels(), ax3.get_xticklabels()], visible=False)

png_path = 'outputs/ningde_era_sharpe_ratio.png'
plt.savefig(png_path, dpi=150, bbox_inches='tight', facecolor='#FAFAFA')
plt.close()
print("  saved: " + png_path)

# ============================================================
# 8. 构建 JSON 数据并写入 HTML
# ============================================================
print("  生成交互式 HTML...")

chart_data = []
for i in range(ROLLING_WINDOW, n):
    dr_i = i - 1
    chart_data.append({
        'date': dates.iloc[i].strftime('%Y-%m-%d'),
        'close': float(round(close[i], 2)),
        'dailyRet': float(round(daily_ret[dr_i]*100, 4)) if dr_i < n_ret else 0,
        'rollingRet': float(round(rolling_ann_ret[i]*100, 2)),
        'rollingVol': float(round(rolling_ann_vol[i]*100, 2)),
        'rollingSharpe': float(round(rolling_sharpe[i], 4)),
        'cumRet': float(round((cum_ret[dr_i]-1)*100, 2)) if dr_i < n_ret else 0,
        'drawdown': float(round(drawdown[dr_i], 2)) if dr_i < n_ret else 0,
    })

hist_vals = [round(float(v), 4) for v in dr_pct]

# 使用英文模板避免编码问题
# 但保留中文 title / label 由客户端 Chart.js 显示
stats = {
    'start_date': chart_data[0]['date'],
    'end_date': chart_data[-1]['date'],
    'window': ROLLING_WINDOW,
    'rf': RISK_FREE_RATE * 100,
    'ann_ret': round(ann_ret * 100, 2),
    'ann_vol': round(ann_vol * 100, 2),
    'sharpe': round(sharpe, 4),
    'max_dd': round(max_dd, 2),
    'max_sharpe': round(np.nanmax(rolling_sharpe), 4),
    'min_sharpe': round(np.nanmin(rolling_sharpe), 4),
    'pos_ratio': round(pos_ratio, 1),
    'cum_color': '#E24B4A' if cum_ret[-1] >= 1.0 else '#1D9E75',
    'mean_daily_ret': round(mean_daily_ret * 100, 4),
    'std_daily_ret': round(std_daily_ret * 100, 4),
}

template = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CATL 300750.SZ Sharpe Ratio</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Microsoft YaHei',sans-serif;background:#f5f5f5;color:#222}
.header{background:#fff;padding:18px 24px;border-bottom:1px solid #e0e0e0}
.header h1{font-size:18px;font-weight:500}
.header .meta{font-size:13px;color:#666;margin-top:4px}
.container{padding:14px;max-width:1400px;margin:0 auto;display:flex;flex-direction:column;gap:14px}
.card{background:#fff;border-radius:8px;border:1px solid #e8e8e8;padding:14px 16px}
.card h2{font-size:14px;font-weight:500;color:#333;margin-bottom:8px}
.chart-wrap{position:relative;width:100%}
.chart-cum{height:280px}
.chart-roll{height:250px}
.chart-dist{height:250px}
.stats{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:4px}
.stat{flex:1;min-width:100px;background:#f8f8f8;border-radius:6px;padding:12px 14px;text-align:center}
.stat .lbl{font-size:12px;color:#888;margin-bottom:4px}
.stat .val{font-size:22px;font-weight:500}
.stat .sub{font-size:11px;color:#aaa;margin-top:2px}
.formula{background:#f0f4ff;border-radius:6px;padding:12px 16px;font-size:13px;line-height:1.8;color:#333;margin-bottom:8px}
.formula code{background:#e8ecf4;padding:2px 6px;border-radius:3px;font-size:12px}
</style>
</head>
<body>
<div class="header">
<h1>Ningde Era (CATL) 300750.SZ &mdash; Sharpe Ratio Analysis</h1>
<div class="meta" id="headerMeta"></div>
</div>
<div class="container">
<div class="formula">
<strong>Sharpe Ratio = (R_p - R_f) / sigma_p</strong><br>
<code>R_p</code> = annualized return, <code>R_f</code> = risk-free rate, <code>sigma_p</code> = annualized volatility<br>
<span id="formulaSummary"></span>
</div>
<div id="statRow" class="stats"></div>
<div class="card">
<h2>Cumulative Return &amp; Drawdown</h2>
<div class="chart-wrap chart-cum"><canvas id="cumChart"></canvas></div>
</div>
<div class="card">
<h2>Rolling Annualized Return &amp; Volatility</h2>
<div class="chart-wrap chart-roll"><canvas id="rollChart"></canvas></div>
</div>
<div class="card">
<h2>Rolling Sharpe Ratio</h2>
<div class="chart-wrap chart-roll"><canvas id="sharpeChart"></canvas></div>
</div>
<div class="card">
<h2>Daily Return Distribution</h2>
<div class="chart-wrap chart-dist"><canvas id="distChart"></canvas></div>
</div>
</div>
<script>
var CHART = """ + json.dumps(chart_data) + """;
var HIST = """ + json.dumps(hist_vals) + """;

var dates = CHART.map(function(d){return d.date;});
var cumRet = CHART.map(function(d){return d.cumRet;});
var dd     = CHART.map(function(d){return d.drawdown;});
var rollRet = CHART.map(function(d){return d.rollingRet;});
var rollVol = CHART.map(function(d){return d.rollingVol;});
var rollSR  = CHART.map(function(d){return d.rollingSharpe;});
var stats  = """ + json.dumps(stats) + """;

document.getElementById('headerMeta').textContent =
  'Data: ' + CHART[0].date + ' ~ ' + CHART[CHART.length-1].date +
  ' | Rolling: ' + stats.window + 'd | Rf: ' + stats.rf + '%';

document.getElementById('formulaSummary').innerHTML =
  'Overall: Annualized Return = <strong>' + stats.ann_ret + '%</strong>, ' +
  'Annualized Vol = <strong>' + stats.ann_vol + '%</strong>, ' +
  'Sharpe = <strong>' + stats.sharpe + '</strong>';

document.getElementById('statRow').innerHTML =
  '<div class="stat"><div class="lbl">Ann.Return</div><div class="val" style="color:' + (stats.ann_ret>=0?'#E24B4A':'#1D9E75') + '">' + stats.ann_ret + '%</div></div>' +
  '<div class="stat"><div class="lbl">Ann.Volatility</div><div class="val">' + stats.ann_vol + '%</div></div>' +
  '<div class="stat"><div class="lbl">Sharpe Ratio</div><div class="val" style="color:#378ADD">' + stats.sharpe + '</div><div class="sub">overall</div></div>' +
  '<div class="stat"><div class="lbl">Max Drawdown</div><div class="val" style="color:#E24B4A">' + stats.max_dd + '%</div></div>' +
  '<div class="stat"><div class="lbl">Positive Days</div><div class="val">' + stats.pos_ratio + '%</div></div>';

var baseOpts = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: { x: { grid: { display: false }, ticks: { maxTicksLimit: 14, font: {size:10}, maxRotation:45 } } }
};

// Cumulative
new Chart(document.getElementById('cumChart'), {
  type: 'line',
  data: {
    labels: dates,
    datasets: [
      { label: 'Cumulative Return', data: cumRet, borderColor: stats.cum_color, borderWidth: 1.8, pointRadius: 0,
        fill: {target: 'origin', above: 'rgba(226,75,74,0.08)'}, yAxisID: 'y' },
      { label: 'Drawdown', data: dd, borderColor: '#E24B4A', borderWidth: 0.8, pointRadius: 0,
        fill: {target: 'origin', above: 'rgba(226,75,74,0.12)'}, yAxisID: 'y1' },
    ]
  },
  options: {
    ...baseOpts,
    scales: {
      x: baseOpts.scales.x,
      y:  { position:'left',  grid:{color:'#f0f0f0'}, ticks:{font:{size:10}, callback:function(v){return v.toFixed(0)+'%'}}, title:{display:true,text:'Cumulative Return %',font:{size:10}} },
      y1: { position:'right', grid:{display:false},    ticks:{font:{size:10}, callback:function(v){return v.toFixed(0)+'%'}}, title:{display:true,text:'Drawdown %',font:{size:10,color:'#E24B4A'}}, reverse:true, max:0 }
    },
    plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: {size:10} } } }
  }
});

// Rolling returns & vol
new Chart(document.getElementById('rollChart'), {
  type: 'line',
  data: {
    labels: dates,
    datasets: [
      { label: 'Rolling Ann.Ret.', data: rollRet, borderColor: '#534AB7', borderWidth: 1.2, pointRadius: 0, fill: false },
      { label: 'Rolling Ann.Vol.', data: rollVol, borderColor: '#F0997B', borderWidth: 1.2, pointRadius: 0, fill: false },
    ]
  },
  options: {
    ...baseOpts,
    scales: { x: baseOpts.scales.x, y: { grid:{color:'#f0f0f0'}, ticks:{font:{size:10}, callback:function(v){return v.toFixed(0)+'%'}} } },
    plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: {size:10} } } }
  }
});

// Rolling Sharpe
var srColors = rollSR.map(function(v){ return v >= 0 ? '#1D9E75' : '#E24B4A'; });
new Chart(document.getElementById('sharpeChart'), {
  type: 'bar',
  data: {
    labels: dates,
    datasets: [{ label: 'Rolling Sharpe', data: rollSR, backgroundColor: srColors, borderWidth: 0 }]
  },
  options: {
    ...baseOpts,
    scales: { x: baseOpts.scales.x, y: { grid:{color:'#f0f0f0'}, ticks:{font:{size:10}} } },
    plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: {size:10} } } }
  }
});

// Distribution
(function(){
  var mn = HIST.reduce(function(a,b){return Math.min(a,b);});
  var mx = HIST.reduce(function(a,b){return Math.max(a,b);});
  var binW = (mx-mn)/40;
  var counts = new Array(40).fill(0);
  var labels = new Array(40);
  for(var i=0;i<40;i++){ labels[i]=(mn + i*binW).toFixed(2)+'%'; }
  HIST.forEach(function(v){
    var idx = Math.min(Math.floor((v-mn)/binW), 39);
    counts[idx]++;
  });
  new Chart(document.getElementById('distChart'), {
    type: 'bar',
    data: { labels: labels, datasets: [{ label: 'Frequency', data: counts, backgroundColor: '#378ADD', borderRadius: 2 }] },
    options: {
      ...baseOpts,
      scales: { x: { ticks:{font:{size:9},maxTicksLimit:20,autoSkip:true,maxRotation:45}, grid:{display:false} }, y:{ grid:{color:'#f0f0f0'}, ticks:{font:{size:10}} } }
    }
  });
})();
</script>
</body>
</html>"""

with open('outputs/ningde_era_sharpe_ratio.html', 'w', encoding='utf-8') as f:
    f.write(template)

print("  saved: outputs/ningde_era_sharpe_ratio.html")
print("\n" + "=" * 65)
print("  Done.")
print("=" * 65)
