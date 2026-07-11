# -*- coding: utf-8 -*-
"""
金发科技(600143.SH) 双均线策略完整分析
========================================
1) 通过 tushare 获取近一年交易数据并复权
2) 计算 MA5/MA15 均线
3) 生成金叉买入/死叉卖出信号
4) 可视化：股价+均线+买卖信号+成交量
5) 策略回测与量化指标计算
6) 输出 HTML 报告 + PDF 报告到 update/ 目录
"""

import os, sys, base64, warnings, tempfile
warnings.filterwarnings('ignore')
os.environ['MPLCONFIGDIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.matplotlib_cache')
from datetime import datetime, timedelta
from io import BytesIO

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch

# ===== 字体设置 =====
simsun_path = 'C:/Windows/Fonts/simsun.ttc'
fm.fontManager.addfont(simsun_path)
plt.rcParams['font.family'] = 'SimSun'
plt.rcParams['axes.unicode_minus'] = False

# ===== 输出目录 =====
OUT_DIR = 'D:/项目/北大BA/在线实习/update'
os.makedirs(OUT_DIR, exist_ok=True)

# ===== 参数配置 =====
STOCK_CODE = '600143.SH'
STOCK_NAME = '金发科技'
SHORT_WIN = 5     # 短期均线周期
LONG_WIN = 15     # 长期均线周期
INITIAL_CAPITAL = 1000000  # 初始资金 100万
RISK_FREE_RATE = 0.025     # 无风险利率 2.5%

print('=' * 60)
print(f'{STOCK_NAME}({STOCK_CODE}) 双均线策略完整分析')
print(f'均线参数: MA{SHORT_WIN} / MA{LONG_WIN}')
print('=' * 60)

# ============================================================
# 1. 获取数据
# ============================================================
print('\n【Step 1】获取数据...')
import tushare as ts
pro = ts.pro_api()

end_date = datetime.now().strftime('%Y%m%d')
start_date = (datetime.now() - timedelta(days=400)).strftime('%Y%m%d')  # 多取一些确保有足够数据

# 获取日线行情
df = pro.daily(ts_code=STOCK_CODE, start_date=start_date, end_date=end_date)
df.sort_values('trade_date', inplace=True)
df.reset_index(drop=True, inplace=True)

print(f'获取到 {len(df)} 条交易日数据')
print(f'日期范围: {df.trade_date.iloc[0]} ~ {df.trade_date.iloc[-1]}')
print(f'最新收盘价: {df.close.iloc[-1]:.2f}')

# 使用前复权数据 (qfq)
df_adj = pro.daily(ts_code=STOCK_CODE, start_date=start_date, end_date=end_date, adj='qfq')
df_adj.sort_values('trade_date', inplace=True)
df_adj.reset_index(drop=True, inplace=True)

# 使用复权价格替换原始价格
df['open_adj'] = df_adj['open']
df['close_adj'] = df_adj['close']
df['high_adj'] = df_adj['high']
df['low_adj'] = df_adj['low']

# 解析日期
df['date'] = pd.to_datetime(df['trade_date'])

# 只保留最近一年的数据用于分析和可视化的核心部分
one_year_ago = df['date'].max() - pd.DateOffset(days=365)
df_plot = df[df['date'] >= one_year_ago].copy()
df_plot.reset_index(drop=True, inplace=True)

print(f'近一年数据: {len(df_plot)} 条')
print(f'前复权价格范围: {df_plot["close_adj"].min():.2f} ~ {df_plot["close_adj"].max():.2f}')

# ============================================================
# 2. 计算均线
# ============================================================
print('\n【Step 2】计算均线...')
df_plot['MA_short'] = df_plot['close_adj'].rolling(window=SHORT_WIN).mean()
df_plot['MA_long']  = df_plot['close_adj'].rolling(window=LONG_WIN).mean()

print(f'MA{SHORT_WIN} 最新值: {df_plot["MA_short"].iloc[-1]:.2f}')
print(f'MA{LONG_WIN} 最新值: {df_plot["MA_long"].iloc[-1]:.2f}')

# ============================================================
# 3. 买卖信号
# ============================================================
print('\n【Step 3】计算买卖信号...')

# 金叉: 短期均线上穿长期均线 -> 买入(1)
# 死叉: 短期均线下穿长期均线 -> 卖出(-1)
df_plot['signal'] = 0
df_plot.loc[(df_plot['MA_short'] > df_plot['MA_long']) &
            (df_plot['MA_short'].shift(1) <= df_plot['MA_long'].shift(1)), 'signal'] = 1
df_plot.loc[(df_plot['MA_short'] < df_plot['MA_long']) &
            (df_plot['MA_short'].shift(1) >= df_plot['MA_long'].shift(1)), 'signal'] = -1

buy_signals  = df_plot[df_plot['signal'] == 1].copy()
sell_signals = df_plot[df_plot['signal'] == -1].copy()

print(f'买入信号(金叉): {len(buy_signals)} 次')
print(f'卖出信号(死叉): {len(sell_signals)} 次')

if len(buy_signals) > 0:
    print(f'首次买入信号: {buy_signals["trade_date"].iloc[0]}')
if len(sell_signals) > 0:
    print(f'首次卖出信号: {sell_signals["trade_date"].iloc[0]}')

# 当前持仓状态判断
latest_signal = df_plot['signal'].iloc[-1]
latest_ma_short = df_plot['MA_short'].iloc[-1]
latest_ma_long = df_plot['MA_long'].iloc[-1]
if latest_ma_short > latest_ma_long:
    print(f'当前状态: 多头市场 (MA{SHORT_WIN} > MA{LONG_WIN})')
else:
    print(f'当前状态: 空头市场 (MA{SHORT_WIN} <= MA{LONG_WIN})')

# ============================================================
# 4. 可视化
# ============================================================
print('\n【Step 4】生成可视化图表...')

# 创建图形 - 3行: 主图(价格+均线+信号), 成交量, 净值曲线
fig = plt.figure(figsize=(16, 12), facecolor='#f8f9fa')

# ---- 4a. 主图: 股价 + 均线 + 交易信号 ----
ax1 = fig.add_axes([0.07, 0.38, 0.88, 0.54])
ax1.set_facecolor('#ffffff')

# 价格线
ax1.plot(df_plot['date'], df_plot['close_adj'], color='#2c3e50', linewidth=1.0,
         alpha=0.6, label='复权收盘价', zorder=1)

# 均线
ax1.plot(df_plot['date'], df_plot['MA_short'], color='#e74c3c', linewidth=2.2,
         label=f'MA{SHORT_WIN} (短期均线)', zorder=2)
ax1.plot(df_plot['date'], df_plot['MA_long'], color='#2980b9', linewidth=2.2,
         label=f'MA{LONG_WIN} (长期均线)', zorder=2)

# 多头/空头区域填充
ax1.fill_between(df_plot['date'], df_plot['MA_short'], df_plot['MA_long'],
                 where=(df_plot['MA_short'] >= df_plot['MA_long']),
                 facecolor='#e74c3c', alpha=0.06, zorder=0, label='多头区域')
ax1.fill_between(df_plot['date'], df_plot['MA_short'], df_plot['MA_long'],
                 where=(df_plot['MA_short'] < df_plot['MA_long']),
                 facecolor='#2980b9', alpha=0.06, zorder=0, label='空头区域')

# 买入信号 (金叉) - 红色上箭头
ax1.scatter(buy_signals['date'], buy_signals['close_adj'],
            marker='^', s=220, color='#e74c3c', edgecolors='#c0392b',
            linewidths=1.5, zorder=5, label='买入信号(金叉)', alpha=0.95)

# 卖出信号 (死叉) - 绿色下箭头
ax1.scatter(sell_signals['date'], sell_signals['close_adj'],
            marker='v', s=220, color='#27ae60', edgecolors='#1e8449',
            linewidths=1.5, zorder=5, label='卖出信号(死叉)', alpha=0.95)

# 标注关键信号（首尾和部分中间信号）
annotated = 0
for idx, row in buy_signals.iterrows():
    if annotated < 2 or idx == buy_signals.index[-1]:
        ax1.annotate(' 买入', (row['date'], row['close_adj']),
                    xytext=(8, 12), textcoords='offset points',
                    fontsize=9, color='#c0392b', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='#c0392b', lw=0.8))
        annotated += 1

annotated = 0
for idx, row in sell_signals.iterrows():
    if annotated < 2 or idx == sell_signals.index[-1]:
        ax1.annotate(' 卖出', (row['date'], row['close_adj']),
                    xytext=(8, -18), textcoords='offset points',
                    fontsize=9, color='#1e8449', fontweight='bold',
                    arrowprops=dict(arrowstyle='->', color='#1e8449', lw=0.8))
        annotated += 1

ax1.set_title(f'{STOCK_NAME}({STOCK_CODE}) 双均线策略回测  MA{SHORT_WIN}/MA{LONG_WIN}',
              fontsize=16, fontweight='bold', pad=15, color='#2c3e50')
ax1.set_ylabel('价格 (元)', fontsize=12, color='#2c3e50')
ax1.legend(loc='upper left', fontsize=9, framealpha=0.9, edgecolor='#ddd', ncol=2)
ax1.grid(True, alpha=0.15, linestyle='--')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.tick_params(labelsize=9)

# ---- 4b. 副图1: 成交量 ----
ax2 = fig.add_axes([0.07, 0.24, 0.88, 0.12])
ax2.set_facecolor('#ffffff')
colors_vol = ['#e74c3c' if c < o else '#27ae60' for c, o in zip(df_plot['close_adj'], df_plot['open_adj'])]
ax2.bar(df_plot['date'], df_plot['vol'], color=colors_vol, alpha=0.4, width=0.8, label='成交量')
ax2.set_ylabel('成交量\n(手)', fontsize=10, color='#2c3e50')
ax2.legend(loc='upper left', fontsize=8)
ax2.grid(True, alpha=0.15, linestyle='--')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.tick_params(labelsize=8)
ax2.set_xticklabels([])

# ---- 4c. 副图2: 策略净值曲线 ----
# 先进行回测计算净值序列
position = 0
cash = INITIAL_CAPITAL
nav_series = []

for i in range(len(df_plot)):
    row = df_plot.iloc[i]
    price = row['close_adj']

    if row['signal'] == 1 and cash > 0:
        shares = int(cash / price / 100) * 100
        if shares > 0:
            cash -= shares * price
            position += shares
    elif row['signal'] == -1 and position > 0:
        cash += position * price
        position = 0

    nav = cash + position * price
    nav_series.append(nav)

df_plot['nav'] = nav_series

ax3 = fig.add_axes([0.07, 0.07, 0.88, 0.15])
ax3.set_facecolor('#ffffff')
ax3.plot(df_plot['date'], df_plot['nav'], color='#8e44ad', linewidth=1.8, label='策略净值', zorder=2)
ax3.fill_between(df_plot['date'], INITIAL_CAPITAL, df_plot['nav'],
                 where=(df_plot['nav'] >= INITIAL_CAPITAL),
                 facecolor='#e74c3c', alpha=0.12, label='盈利区域')
ax3.fill_between(df_plot['date'], INITIAL_CAPITAL, df_plot['nav'],
                 where=(df_plot['nav'] < INITIAL_CAPITAL),
                 facecolor='#27ae60', alpha=0.12, label='亏损区域')
ax3.axhline(y=INITIAL_CAPITAL, color='#7f8c8d', linestyle='--', linewidth=0.8, alpha=0.6)
ax3.set_ylabel('净值(万元)', fontsize=10, color='#2c3e50')
ax3.set_xlabel('交易日期', fontsize=11, color='#2c3e50')
ax3.legend(loc='upper left', fontsize=8)
ax3.grid(True, alpha=0.15, linestyle='--')
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)
ax3.tick_params(labelsize=8)

plt.xticks(rotation=30)

# 保存图表
chart_path = os.path.join(OUT_DIR, '金发科技_双均线策略回测图.png')
fig.savefig(chart_path, dpi=200, bbox_inches='tight', facecolor='#f8f9fa')
print(f'图表已保存: {chart_path}')

# 同时保存为 base64 用于 HTML
buf = BytesIO()
fig.savefig(buf, dpi=180, bbox_inches='tight', facecolor='#f8f9fa', edgecolor='none')
buf.seek(0)
chart_b64 = base64.b64encode(buf.read()).decode('utf-8')
plt.close(fig)

# ============================================================
# 5. 策略回测与量化指标计算
# ============================================================
print('\n【Step 5】策略回测与量化指标计算...')

# 重新执行完整的回测（使用全量数据 df）
# 但为了保证准确性，使用 df_plot（近一年）
position = 0
cash = INITIAL_CAPITAL
trade_log = []

for i in range(len(df_plot)):
    row = df_plot.iloc[i]
    price = row['close_adj']

    if row['signal'] == 1 and cash > 0:
        shares = int(cash / price / 100) * 100
        if shares > 0:
            cost = shares * price
            cash -= cost
            position += shares
            trade_log.append({
                'date': row['trade_date'],
                'type': '买入',
                'price': price,
                'shares': shares,
                'amount': cost,
                'cash_remain': cash
            })

    elif row['signal'] == -1 and position > 0:
        amount = position * price
        cash += amount
        trade_log.append({
            'date': row['trade_date'],
            'type': '卖出',
            'price': price,
            'shares': position,
            'amount': amount,
            'cash_remain': cash
        })
        position = 0

# 计算净值序列
nav_arr = np.array(nav_series)
final_value = nav_arr[-1]
total_return = (final_value - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

# ---- 年化收益率 ----
days = (df_plot['date'].iloc[-1] - df_plot['date'].iloc[0]).days
annual_return = (final_value / INITIAL_CAPITAL) ** (365 / max(days, 1)) - 1
annual_return_pct = annual_return * 100

# ---- 最大回撤 (MDD) ----
peak_arr = np.maximum.accumulate(nav_arr)
drawdown_arr = (nav_arr - peak_arr) / peak_arr
mdd = drawdown_arr.min() * 100
mdd_idx = int(np.argmin(drawdown_arr))

# ---- 夏普比率 ----
daily_rets = pd.Series(nav_arr).pct_change().dropna()
daily_mean = daily_rets.mean()
daily_std = daily_rets.std()
annual_mean_r = daily_mean * 252
annual_std_r = daily_std * np.sqrt(252)
sharpe_ratio = (annual_mean_r - RISK_FREE_RATE) / annual_std_r if annual_std_r > 0 else 0

# ---- 胜率 ----
wins = 0
losses = 0
trade_returns = []
for i in range(0, len(trade_log) - 1, 2):
    if i + 1 < len(trade_log) and trade_log[i]['type'] == '买入' and trade_log[i+1]['type'] == '卖出':
        buy_amt = trade_log[i]['amount']
        sell_amt = trade_log[i+1]['amount']
        ret = (sell_amt - buy_amt) / buy_amt * 100
        trade_returns.append(ret)
        if ret > 0:
            wins += 1
        else:
            losses += 1

total_trades = wins + losses
win_rate = wins / total_trades * 100 if total_trades > 0 else 0
avg_trade_return = np.mean(trade_returns) if trade_returns else 0

# ---- 基准对比 ----
buy_hold_return = (df_plot['close_adj'].iloc[-1] - df_plot['close_adj'].iloc[0]) / df_plot['close_adj'].iloc[0] * 100
excess_return = total_return - buy_hold_return

# ---- 交易频率 ----
trade_frequency = len(trade_log) / (days / 365) if days > 0 else 0

# ---- Calmar 比率 ----
calmar_ratio = annual_return_pct / abs(mdd) if mdd != 0 else 0

# 打印回测结果
print(f'\n{"="*50}')
print(f'{"回测指标":20s} {"数值":>15s}')
print(f'{"="*50}')
print(f'{"初始资金":20s} {INITIAL_CAPITAL:>15,.0f} 元')
print(f'{"最终资产":20s} {final_value:>15,.0f} 元')
print(f'{"累计收益率":20s} {total_return:>+14.2f}%')
print(f'{"年化收益率":20s} {annual_return_pct:>+14.2f}%')
print(f'{"最大回撤(MDD)":20s} {mdd:>14.2f}%')
print(f'{"夏普比率":20s} {sharpe_ratio:>14.2f}')
print(f'{"Calmar比率":20s} {calmar_ratio:>14.2f}')
print(f'{"交易次数":20s} {len(trade_log):>14d}')
print(f'{"胜率":20s} {win_rate:>13.1f}%')
print(f'{"平均单笔收益":20s} {avg_trade_return:>+13.2f}%')
print(f'{"持有天数":20s} {days:>14d}')
print(f'{"年化波动率":20s} {annual_std_r*100:>13.2f}%')
print(f'{"同期买入持有":20s} {buy_hold_return:>+14.2f}%')
print(f'{"超额收益":20s} {excess_return:>+14.2f}%')
print(f'{"="*50}')

# 交易记录
print(f'\n交易记录 ({len(trade_log)} 笔):')
print(f'{"日期":12s} {"类型":6s} {"价格":>8s} {"数量":>8s} {"金额":>12s} {"剩余现金":>12s}')
print('-' * 58)
for t in trade_log:
    print(f'{t["date"]:12s} {t["type"]:6s} {t["price"]:>8.2f} {t["shares"]:>8d} {t["amount"]:>12,.0f} {t["cash_remain"]:>12,.0f}')

# ============================================================
# 6. 生成 HTML 报告
# ============================================================
print('\n【Step 6】生成 HTML 报告...')

# 交易记录 HTML 行
trade_rows_html = ''
for i, t in enumerate(trade_log, 1):
    cls = 'signal-buy' if t['type'] == '买入' else 'signal-sell'
    trade_rows_html += (
        f'<tr>'
        f'<td>{i}</td>'
        f'<td>{t["date"]}</td>'
        f'<td class="{cls}">{t["type"]}</td>'
        f'<td>{t["price"]:.2f}</td>'
        f'<td>{t["shares"]:,}</td>'
        f'<td>{t["amount"]:,.0f}</td>'
        f'<td>{t["cash_remain"]:,.0f}</td>'
        f'</tr>\n'
    )

# 信号总结
signal_summary = ''
for t in trade_log:
    signal_summary += f'<li><strong>{t["date"]}</strong> {"🟢 买入" if t["type"]=="买入" else "🔴 卖出"} → 价格 {t["price"]:.2f} 元，金额 {t["amount"]:,.0f} 元</li>\n'

# 分析结论文本
if excess_return > 0:
    vs_text = f'策略跑赢大盘 <b style="color:#27ae60;">+{excess_return:.2f}%</b>'
    vs_color = '#27ae60'
else:
    vs_text = f'策略跑输大盘 <b style="color:#e74c3c;">{excess_return:.2f}%</b>'
    vs_color = '#e74c3c'

if sharpe_ratio > 1:
    sharpe_comment = f'夏普比率 {sharpe_ratio:.2f}，策略的风险调整后收益表现较好'
elif sharpe_ratio > 0:
    sharpe_comment = f'夏普比率 {sharpe_ratio:.2f}，策略的风险调整后收益一般'
else:
    sharpe_comment = f'夏普比率 {sharpe_ratio:.2f}，策略的风险调整后收益为负，需改进'

# 生成趋势描述
latest_close = df_plot['close_adj'].iloc[-1]
first_close = df_plot['close_adj'].iloc[0]
price_change = (latest_close - first_close) / first_close * 100
if price_change > 10:
    trend_desc = '单边上涨趋势'
elif price_change > 0:
    trend_desc = '震荡偏强走势'
elif price_change > -10:
    trend_desc = '震荡偏弱走势'
else:
    trend_desc = '单边下跌趋势'

# 构建完整 HTML
html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{STOCK_NAME} 双均线策略回测报告</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:"Microsoft YaHei","SimSun","PingFang SC",sans-serif; background:#f0f2f5; color:#333; padding:20px; }}
.container {{ max-width:1100px; margin:0 auto; }}
.header {{ background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460); color:#fff; padding:35px 40px; border-radius:14px; margin-bottom:24px; }}
.header h1 {{ font-size:26px; margin-bottom:8px; letter-spacing:1px; }}
.header p {{ font-size:14px; opacity:0.8; }}
.header .meta {{ margin-top:10px; display:flex; flex-wrap:wrap; gap:12px; }}
.header .meta span {{ background:rgba(255,255,255,0.15); padding:3px 12px; border-radius:20px; font-size:12px; }}
.card {{ background:#fff; border-radius:12px; padding:24px 28px; margin-bottom:20px; box-shadow:0 2px 12px rgba(0,0,0,0.06); }}
.card h2 {{ font-size:17px; color:#1a1a2e; margin-bottom:14px; padding-bottom:8px; border-bottom:2px solid #e8edf2; }}
.metrics {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:12px; }}
.metric {{ background:#f8f9fa; border-radius:10px; padding:14px 10px; text-align:center; transition:transform 0.2s; }}
.metric:hover {{ transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,0.08); }}
.metric .label {{ font-size:11px; color:#888; margin-bottom:4px; }}
.metric .value {{ font-size:22px; font-weight:bold; color:#1a1a2e; }}
.metric .value.red {{ color:#e74c3c; }}
.metric .value.green {{ color:#27ae60; }}
.metric .value.blue {{ color:#2980b9; }}
.chart {{ text-align:center; margin-top:10px; }}
.chart img {{ max-width:100%; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ background:#1a1a2e; color:#fff; padding:10px 12px; text-align:center; font-weight:500; font-size:12px; }}
td {{ padding:8px 12px; text-align:center; border-bottom:1px solid #eee; }}
tr:nth-child(even) {{ background:#f8f9fa; }}
tr:hover {{ background:#eef4fb; }}
.signal-buy {{ color:#e74c3c; font-weight:bold; }}
.signal-sell {{ color:#27ae60; font-weight:bold; }}
.signal-list {{ list-style:none; padding:0; }}
.signal-list li {{ padding:6px 0; border-bottom:1px solid #f0f0f0; font-size:13px; }}
.signal-list li:last-child {{ border:none; }}
.footer {{ text-align:center; font-size:12px; color:#999; padding:20px 0; }}
.conclusion p {{ line-height:1.9; font-size:14px; text-indent:2em; margin-bottom:8px; }}
.badge {{ display:inline-block; padding:2px 10px; border-radius:12px; font-size:12px; font-weight:bold; }}
.badge-buy {{ background:#fce4e4; color:#e74c3c; }}
.badge-sell {{ background:#e8f8ed; color:#27ae60; }}
.grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
@media (max-width:768px) {{ .grid-2 {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="container">

<!-- 页眉 -->
<div class="header">
<h1>{STOCK_NAME}({STOCK_CODE}) 双均线策略回测报告</h1>
<div class="meta">
<span>策略: 双均线金叉/死叉</span>
<span>均线: MA{SHORT_WIN} / MA{LONG_WIN}</span>
<span>回测周期: {df_plot["trade_date"].iloc[0]} ~ {df_plot["trade_date"].iloc[-1]}</span>
<span>数据: Tushare Pro</span>
<span>生成: {datetime.now().strftime("%Y-%m-%d %H:%M")}</span>
</div>
</div>

<!-- 回测指标概览 -->
<div class="card">
<h2>📊 回测指标概览</h2>
<div class="metrics">
<div class="metric"><div class="label">初始资金</div><div class="value blue">{INITIAL_CAPITAL:,}</div></div>
<div class="metric"><div class="label">最终资产</div><div class="value {"green" if final_value >= INITIAL_CAPITAL else "red"}">{final_value:,.0f}</div></div>
<div class="metric"><div class="label">累计收益率</div><div class="value {"green" if total_return >= 0 else "red"}">{total_return:+.2f}%</div></div>
<div class="metric"><div class="label">年化收益率</div><div class="value {"green" if annual_return_pct >= 0 else "red"}">{annual_return_pct:+.2f}%</div></div>
<div class="metric"><div class="label">最大回撤 (MDD)</div><div class="value red">{mdd:.2f}%</div></div>
<div class="metric"><div class="label">夏普比率</div><div class="value {"green" if sharpe_ratio > 1 else ("blue" if sharpe_ratio > 0 else "red")}">{sharpe_ratio:.2f}</div></div>
<div class="metric"><div class="label">Calmar比率</div><div class="value {"green" if calmar_ratio > 1 else "blue"}">{calmar_ratio:.2f}</div></div>
<div class="metric"><div class="label">交易总次数</div><div class="value blue">{len(trade_log)}</div></div>
<div class="metric"><div class="label">胜率</div><div class="value {"green" if win_rate >= 50 else "red"}">{win_rate:.1f}%</div></div>
<div class="metric"><div class="label">平均单笔收益</div><div class="value {"green" if avg_trade_return >= 0 else "red"}">{avg_trade_return:+.2f}%</div></div>
<div class="metric"><div class="label">年化波动率</div><div class="value blue">{annual_std_r*100:.2f}%</div></div>
<div class="metric"><div class="label">持有天数</div><div class="value blue">{days}</div></div>
<div class="metric"><div class="label">同期买入持有</div><div class="value {"green" if buy_hold_return >= 0 else "red"}">{buy_hold_return:+.2f}%</div></div>
<div class="metric"><div class="label">超额收益</div><div class="value {"green" if excess_return >= 0 else "red"}">{excess_return:+.2f}%</div></div>
</div>
</div>

<!-- 回测走势图 -->
<div class="card">
<h2>📈 回测走势图</h2>
<div class="chart">
<img src="data:image/png;base64,{chart_b64}" alt="回测走势图">
</div>
<p style="text-align:center;font-size:12px;color:#999;margin-top:6px;">上: 股价+均线+买卖信号 | 中: 成交量 | 下: 策略净值曲线</p>
</div>

<!-- 买卖信号汇总 -->
<div class="card">
<h2>🚦 交易信号汇总</h2>
<div class="grid-2">
<div>
<h3 style="font-size:14px;color:#e74c3c;margin-bottom:8px;">买入信号 ({len(buy_signals)} 次)</h3>
<ul class="signal-list">
{"".join(f'<li>📅 {row["trade_date"]} → 价格 <b>{row["close_adj"]:.2f}</b> 元</li>' for _, row in buy_signals.iterrows())}
</ul>
</div>
<div>
<h3 style="font-size:14px;color:#27ae60;margin-bottom:8px;">卖出信号 ({len(sell_signals)} 次)</h3>
<ul class="signal-list">
{"".join(f'<li>📅 {row["trade_date"]} → 价格 <b>{row["close_adj"]:.2f}</b> 元</li>' for _, row in sell_signals.iterrows())}
</ul>
</div>
</div>
</div>

<!-- 交易记录明细 -->
<div class="card">
<h2>📋 交易记录明细</h2>
<table>
<thead>
<tr>
<th>序号</th><th>日期</th><th>类型</th><th>价格(元)</th><th>数量(股)</th><th>金额(元)</th><th>剩余现金(元)</th>
</tr>
</thead>
<tbody>
{trade_rows_html}
</tbody>
</table>
</div>

<!-- 风险收益指标详解 -->
<div class="card">
<h2>📖 量化指标说明</h2>
<table>
<thead>
<tr><th>指标</th><th>数值</th><th>说明</th></tr>
</thead>
<tbody>
<tr><td><b>累计收益率</b></td><td class="{"green" if total_return >= 0 else "red"}">{total_return:+.2f}%</td><td>策略从开始到结束的总收益率</td></tr>
<tr><td><b>年化收益率</b></td><td class="{"green" if annual_return_pct >= 0 else "red"}">{annual_return_pct:+.2f}%</td><td>将总收益率年化后的收益率</td></tr>
<tr><td><b>最大回撤(MDD)</b></td><td class="red">{mdd:.2f}%</td><td>策略净值从峰值回落的最大幅度</td></tr>
<tr><td><b>夏普比率</b></td><td class="{"green" if sharpe_ratio > 1 else "blue"}">{sharpe_ratio:.2f}</td><td>每承担一单位风险获得的超额回报</td></tr>
<tr><td><b>Calmar比率</b></td><td>{calmar_ratio:.2f}</td><td>年化收益率与最大回撤之比</td></tr>
<tr><td><b>胜率</b></td><td>{win_rate:.1f}%</td><td>盈利交易次数占总交易次数比例</td></tr>
<tr><td><b>年化波动率</b></td><td>{annual_std_r*100:.2f}%</td><td>策略年化收益率的标准差</td></tr>
</tbody>
</table>
</div>

<!-- 分析结论 -->
<div class="card">
<h2>💡 分析结论</h2>
<div class="conclusion">
<p>
在过去一年的回测中，<b>{STOCK_NAME}</b> 双均线策略(MA{SHORT_WIN}/MA{LONG_WIN})累计收益为 <b style="color:{"#e74c3c" if total_return < 0 else "#27ae60"};">{total_return:+.2f}%</b>，
同期买入持有收益为 <b style="color:{"#e74c3c" if buy_hold_return < 0 else "#27ae60"};">{buy_hold_return:+.2f}%</b>，
{vs_text}。
</p>
<p>
{STOCK_NAME} 在过去一年整体呈现 <b>{trend_desc}</b>，
期间股价从 {first_close:.2f} 元变动至 {latest_close:.2f} 元（涨幅 {price_change:+.2f}%）。
{sharpe_comment}，
最大回撤 <b style="color:#e74c3c;">{mdd:.2f}%</b>，胜率 <b style="color:{"#27ae60" if win_rate >= 50 else "#e74c3c"};">{win_rate:.1f}%</b>，
共产生 <b>{len(trade_log)}</b> 笔交易。
</p>
<p>
<b>优化建议：</b>双均线策略在趋势行情中表现较好，但在震荡市中容易产生假信号。建议：
(1) 调整均线参数组合（如 MA10/MA30 或 MA20/MA60），参数越大信号越可靠但越滞后；
(2) 引入成交量过滤，当金叉出现时若成交量未放大则暂缓买入；
(3) 结合 RSI、MACD 等辅助指标过滤无效信号；
(4) 采用分批建仓策略，而非全仓买入，降低单次错误信号的影响。
</p>
</div>
</div>

<div class="footer">
<p>报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M")}  |  数据来源: Tushare Pro  |  🧑‍💻 分析工具: Python + Matplotlib</p>
</div>

</div>
</body>
</html>
'''

# 写入 HTML 文件
html_path = os.path.join(OUT_DIR, '金发科技_双均线策略回测报告.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
print(f'HTML 报告已生成: {html_path}')
print(f'文件大小: {os.path.getsize(html_path):,} 字节')

# ============================================================
# 7. 生成 PDF 报告
# ============================================================
print('\n【Step 7】生成 PDF 报告...')

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 注册字体
pdfmetrics.registerFont(TTFont('SimSun', simsun_path))

# 样式定义
FS = 10.5
LD = FS * 1.5
sty_body = ParagraphStyle('body', fontName='SimSun', fontSize=FS, leading=LD,
                          spaceAfter=0, spaceBefore=0, alignment=TA_JUSTIFY, firstLineIndent=21)
sty_h1 = ParagraphStyle('h1', fontName='SimSun', fontSize=16, leading=24,
                        spaceAfter=6, spaceBefore=12, alignment=TA_LEFT)
sty_h2 = ParagraphStyle('h2', fontName='SimSun', fontSize=13, leading=19,
                        spaceAfter=4, spaceBefore=8, alignment=TA_LEFT)
sty_h3 = ParagraphStyle('h3', fontName='SimSun', fontSize=11, leading=16,
                        spaceAfter=2, spaceBefore=6, alignment=TA_LEFT)
sty_caption = ParagraphStyle('caption', fontName='SimSun', fontSize=9, leading=12,
                             spaceAfter=4, spaceBefore=2, alignment=TA_CENTER)
sty_center = ParagraphStyle('center', fontName='SimSun', fontSize=10, leading=14,
                            spaceAfter=2, spaceBefore=2, alignment=TA_CENTER)
sty_title = ParagraphStyle('title', fontName='SimSun', fontSize=18, leading=27,
                           spaceAfter=6, spaceBefore=6, alignment=TA_CENTER)
sty_subtitle = ParagraphStyle('subtitle', fontName='SimSun', fontSize=11, leading=16,
                              spaceAfter=4, alignment=TA_CENTER)
sty_author = ParagraphStyle('author', fontName='SimSun', fontSize=11, leading=16,
                            spaceAfter=16, alignment=TA_CENTER)

def P(text, sty=sty_body):
    return Paragraph(text, sty)

def PN(text):
    return Paragraph(text, ParagraphStyle('x', parent=sty_body, firstLineIndent=0))

def H1(text):
    return Paragraph(text, sty_h1)

def H2(text):
    return Paragraph(text, sty_h2)

def H3(text):
    return Paragraph(text, sty_h3)

def CAP(text):
    return Paragraph(text, sty_caption)

def make_table_pdf(headers, rows, col_widths):
    data = [[Paragraph(h, ParagraphStyle('th', fontName='SimSun', fontSize=9, leading=12, alignment=TA_CENTER)) for h in headers]]
    for r in rows:
        data.append([Paragraph(str(c), ParagraphStyle('tc', fontName='SimSun', fontSize=9, leading=12, alignment=TA_CENTER)) for c in r])
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'SimSun'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BACKGROUND', (0,0), (-1,0), HexColor('#E6F1FB')),
        ('TEXTCOLOR', (0,0), (-1,0), HexColor('#0C447C')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, HexColor('#B4B2A9')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    return tbl

# 构建 PDF
pdf_path = os.path.join(OUT_DIR, '金发科技_双均线策略回测报告.pdf')
doc = SimpleDocTemplate(pdf_path, pagesize=A4,
                        topMargin=22*mm, bottomMargin=18*mm,
                        leftMargin=22*mm, rightMargin=18*mm)

story = []

# ---- 封面 ----
story.append(Spacer(1, 50))
story.append(Paragraph(f'{STOCK_NAME}({STOCK_CODE})', sty_title))
story.append(Paragraph('双均线策略回测报告', sty_title))
story.append(Spacer(1, 12))
story.append(Paragraph(f'MA{SHORT_WIN} / MA{LONG_WIN}  双均线金叉死叉策略', sty_subtitle))
story.append(Spacer(1, 20))
story.append(Paragraph('李婉霞', sty_author))
story.append(Spacer(1, 30))

# 报告信息表
info_data = [
    ['报告名称', f'{STOCK_NAME} 双均线策略回测报告'],
    ['策略类型', f'双均线金叉买入 / 死叉卖出'],
    ['均线参数', f'MA{SHORT_WIN} (短期) / MA{LONG_WIN} (长期)'],
    ['回测周期', f'{df_plot["trade_date"].iloc[0]} ~ {df_plot["trade_date"].iloc[-1]}'],
    ['初始资金', f'{INITIAL_CAPITAL:,} 元'],
    ['无风险利率', f'{RISK_FREE_RATE*100:.1f}%'],
    ['数据来源', 'Tushare Pro'],
    ['生成日期', datetime.now().strftime('%Y-%m-%d %H:%M')],
]
story.append(make_table_pdf(['项目', '内容'], info_data, [120, 340]))
story.append(PageBreak())

# ---- 第一部分：回测结果概览 ----
story.append(H1('一、回测结果概览'))
story.append(H2('1.1 核心指标'))

metrics_data = [
    ['指标', '数值'],
    ['累计收益率', f'{total_return:+.2f}%'],
    ['年化收益率', f'{annual_return_pct:+.2f}%'],
    ['最大回撤 (MDD)', f'{mdd:.2f}%'],
    ['夏普比率', f'{sharpe_ratio:.2f}'],
    ['Calmar 比率', f'{calmar_ratio:.2f}'],
    ['交易总次数', str(len(trade_log))],
    ['胜率', f'{win_rate:.1f}%'],
    ['平均单笔收益', f'{avg_trade_return:+.2f}%'],
    ['年化波动率', f'{annual_std_r*100:.2f}%'],
    ['持有天数', str(days)],
    ['同期买入持有', f'{buy_hold_return:+.2f}%'],
    ['超额收益', f'{excess_return:+.2f}%'],
]
story.append(make_table_pdf(['指标', '数值'], metrics_data, [150, 200]))
story.append(Spacer(1, 8))

# 回测图表
story.append(H2('1.2 回测走势图'))
story.append(Spacer(1, 4))

# 将图表保存到临时文件用于 PDF
tmp_img = os.path.join(tempfile.gettempdir(), 'jinfa_backtest.png')
fig2 = plt.figure(figsize=(8.5, 6.5), facecolor='white')
fig2.patch.set_facecolor('white')

# 简化版本用于 PDF
ax1_pdf = fig2.add_axes([0.08, 0.38, 0.87, 0.55])
ax1_pdf.set_facecolor('white')
ax1_pdf.plot(df_plot['date'], df_plot['close_adj'], color='#2c3e50', linewidth=0.8, alpha=0.6, label='复权收盘价', zorder=1)
ax1_pdf.plot(df_plot['date'], df_plot['MA_short'], color='#e74c3c', linewidth=1.8, label=f'MA{SHORT_WIN}', zorder=2)
ax1_pdf.plot(df_plot['date'], df_plot['MA_long'], color='#2980b9', linewidth=1.8, label=f'MA{LONG_WIN}', zorder=2)
ax1_pdf.fill_between(df_plot['date'], df_plot['MA_short'], df_plot['MA_long'],
                     where=(df_plot['MA_short'] >= df_plot['MA_long']),
                     facecolor='#e74c3c', alpha=0.06, zorder=0)
ax1_pdf.fill_between(df_plot['date'], df_plot['MA_short'], df_plot['MA_long'],
                     where=(df_plot['MA_short'] < df_plot['MA_long']),
                     facecolor='#2980b9', alpha=0.06, zorder=0)
ax1_pdf.scatter(buy_signals['date'], buy_signals['close_adj'],
                marker='^', s=120, color='#e74c3c', edgecolors='#c0392b', linewidths=1, zorder=5, label='买入')
ax1_pdf.scatter(sell_signals['date'], sell_signals['close_adj'],
                marker='v', s=120, color='#27ae60', edgecolors='#1e8449', linewidths=1, zorder=5, label='卖出')
ax1_pdf.set_title(f'{STOCK_NAME} 双均线策略  MA{SHORT_WIN}/{LONG_WIN}', fontsize=13, fontweight='bold', color='#2c3e50')
ax1_pdf.set_ylabel('价格(元)', fontsize=10)
ax1_pdf.legend(loc='upper left', fontsize=8, ncol=2)
ax1_pdf.grid(True, alpha=0.12, linestyle='--')
ax1_pdf.spines['top'].set_visible(False)
ax1_pdf.spines['right'].set_visible(False)
ax1_pdf.tick_params(labelsize=8)

# 成交量副图
ax2_pdf = fig2.add_axes([0.08, 0.25, 0.87, 0.11])
ax2_pdf.set_facecolor('white')
colors_vol2 = ['#e74c3c' if c < o else '#27ae60' for c, o in zip(df_plot['close_adj'], df_plot['open_adj'])]
ax2_pdf.bar(df_plot['date'], df_plot['vol'], color=colors_vol2, alpha=0.35, width=0.8, label='成交量')
ax2_pdf.set_ylabel('成交量(手)', fontsize=9)
ax2_pdf.legend(loc='upper left', fontsize=7)
ax2_pdf.grid(True, alpha=0.12, linestyle='--')
ax2_pdf.spines['top'].set_visible(False)
ax2_pdf.spines['right'].set_visible(False)
ax2_pdf.tick_params(labelsize=7)
ax2_pdf.set_xticklabels([])

# 净值副图
ax3_pdf = fig2.add_axes([0.08, 0.07, 0.87, 0.16])
ax3_pdf.set_facecolor('white')
ax3_pdf.plot(df_plot['date'], df_plot['nav'], color='#8e44ad', linewidth=1.5, label='策略净值')
ax3_pdf.axhline(y=INITIAL_CAPITAL, color='#7f8c8d', linestyle='--', linewidth=0.6, alpha=0.5)
ax3_pdf.fill_between(df_plot['date'], INITIAL_CAPITAL, df_plot['nav'],
                     where=(df_plot['nav'] >= INITIAL_CAPITAL), facecolor='#e74c3c', alpha=0.1)
ax3_pdf.fill_between(df_plot['date'], INITIAL_CAPITAL, df_plot['nav'],
                     where=(df_plot['nav'] < INITIAL_CAPITAL), facecolor='#27ae60', alpha=0.1)
ax3_pdf.set_ylabel('净值(元)', fontsize=9)
ax3_pdf.set_xlabel('交易日期', fontsize=10)
ax3_pdf.legend(loc='upper left', fontsize=7)
ax3_pdf.grid(True, alpha=0.12, linestyle='--')
ax3_pdf.spines['top'].set_visible(False)
ax3_pdf.spines['right'].set_visible(False)
ax3_pdf.tick_params(labelsize=7)

plt.xticks(rotation=30)
fig2.savefig(tmp_img, dpi=200, bbox_inches='tight', facecolor='white')
plt.close(fig2)

story.append(Image(tmp_img, width=470, height=360))
story.append(CAP('图1 金发科技双均线策略回测走势图'))
story.append(Spacer(1, 6))

# ---- 交易记录 ----
story.append(H2('1.3 交易记录明细'))
trade_headers = ['序号', '日期', '类型', '价格(元)', '数量(股)', '金额(元)']
trade_rows = []
for i, t in enumerate(trade_log, 1):
    trade_rows.append([str(i), t['date'], t['type'],
                      f'{t["price"]:.2f}', f'{t["shares"]:,}', f'{t["amount"]:,.0f}'])
if trade_rows:
    story.append(make_table_pdf(trade_headers, trade_rows, [30, 75, 50, 75, 80, 110]))
else:
    story.append(PN('无交易记录'))

story.append(Spacer(1, 6))

# ---- 买卖信号 ----
story.append(H2('1.4 买卖信号汇总'))
buy_dates = [r['trade_date'] for _, r in buy_signals.iterrows()]
sell_dates = [r['trade_date'] for _, r in sell_signals.iterrows()]
story.append(PN(f'买入信号(金叉): {len(buy_signals)} 次'))
story.append(PN(f'  日期: {", ".join(buy_dates)}'))
story.append(PN(f'卖出信号(死叉): {len(sell_signals)} 次'))
story.append(PN(f'  日期: {", ".join(sell_dates)}'))

story.append(PageBreak())

# ---- 第二部分：策略详解 ----
story.append(H1('二、双均线策略详解'))
story.append(H2('2.1 移动平均线 (MA)'))
story.append(P('移动平均线（Moving Average, MA）是技术分析中最基础的趋势指标。它将一段时间内的收盘价取算术平均值并连成曲线。短期均线（如MA5）反应灵敏，能迅速捕捉短期波动，但容易产生假信号；长期均线（如MA15）反应滞后，曲线平滑，信号可靠性更高，但会错过最佳交易时点。'))
story.append(H2('2.2 金叉与死叉'))
story.append(P('金叉（Golden Cross）：短期均线上穿长期均线，表明短期上涨动力超过长期平均水平，市场可能进入上涨通道，视为买入信号。'))
story.append(P('死叉（Death Cross）：短期均线下穿长期均线，表明短期下跌动能超过长期平均水平，市场可能进入下跌通道，视为卖出信号。'))
story.append(H2('2.3 策略交易规则'))
story.append(PN('（1）当短期均线上穿长期均线（金叉）时，触发买入信号，全仓买入。'))
story.append(PN('（2）当短期均线下穿长期均线（死叉）时，触发卖出信号，全仓卖出。'))
story.append(PN('（3）持仓期间不做任何其他操作，完全跟随趋势方向。'))
story.append(H2('2.4 策略优缺点'))
adv_disadv = [
    ['优点', '缺点'],
    ['逻辑简单清晰，易于理解和实现', '在震荡市中频繁产生假信号'],
    ['能有效抓住大的单边趋势行情', '具有天然滞后性，无法买在最低/卖在最高'],
    ['适用于任何时间周期', '参数选择对回测结果影响较大'],
]
story.append(make_table_pdf(['类别', '说明'], adv_disadv[1:], [100, 320]))
story.append(CAP('表1 双均线策略优缺点'))

story.append(PageBreak())

# ---- 第三部分：量化指标详解 ----
story.append(H1('三、量化指标详解'))
story.append(H2('3.1 累计收益率 (Cumulative Return)'))
story.append(P(f'累计收益率是衡量策略盈利能力最直观的指标。本回测累计收益率为 {total_return:+.2f}%，初始 {INITIAL_CAPITAL:,} 元，最终 {final_value:,.0f} 元。'))
story.append(H2('3.2 年化收益率 (Annualized Return)'))
story.append(P(f'年化收益率将总收益率按持有时间折算为年度收益率，便于不同周期的策略对比。本回测年化收益率为 {annual_return_pct:+.2f}%。'))
story.append(H2('3.3 最大回撤 (Maximum Drawdown)'))
story.append(P(f'最大回撤指策略净值从历史最高点回落到之后最低点的最大跌幅，衡量策略的历史最大亏损幅度。本回测最大回撤为 {mdd:.2f}%，意味着历史上最多亏损了 {abs(mdd):.1f}%。'))
story.append(H2('3.4 夏普比率 (Sharpe Ratio)'))
story.append(P(f'夏普比率衡量每承担一单位风险（收益率波动）能获得多少超额回报。本回测夏普比率为 {sharpe_ratio:.2f}。'))
sharpe_ref = [
    ['夏普比率范围', '评价'],
    ['> 2.0', '优秀'],
    ['1.0 ~ 2.0', '良好'],
    ['0 ~ 1.0', '一般'],
    ['< 0', '不佳（跑输无风险利率）'],
]
story.append(make_table_pdf(sharpe_ref[0], sharpe_ref[1:], [120, 100]))
story.append(CAP('表2 夏普比率评估标准'))
story.append(H2('3.5 Calmar 比率'))
story.append(P(f'Calmar 比率 = 年化收益率 / |最大回撤|，衡量每单位回撤产生的年化收益。本回测 Calmar 比率为 {calmar_ratio:.2f}。该值越大，说明策略在承担同等回撤风险时产生的收益越高。'))
story.append(H2('3.6 胜率与平均单笔收益'))
story.append(P(f'胜率 = 盈利交易次数 / 总交易次数。本回测胜率为 {win_rate:.1f}%（{wins}胜{losses}负），平均单笔收益为 {avg_trade_return:+.2f}%。'))

import re
story.append(PageBreak())

# ---- 第四部分：结论与建议 ----
story.append(H1('四、结论与优化建议'))

def strip_html(html_text):
    """Strip HTML tags for PDF plain text usage."""
    text = re.sub(r'<[^>]+>', '', html_text)
    return text

conclusion_1 = f'在过去一年的回测中，{STOCK_NAME} 双均线策略(MA{SHORT_WIN}/MA{LONG_WIN})累计收益 {total_return:+.2f}%，同期买入持有收益 {buy_hold_return:+.2f}%，{strip_html(vs_text)}。'
story.append(P(conclusion_1))
story.append(P(f'{sharpe_comment}，最大回撤 {mdd:.2f}%，胜率 {win_rate:.1f}%，共 {len(trade_log)} 笔交易。'))
story.append(H2('4.1 优化建议'))
story.append(PN('（1）调整均线参数组合（如 MA10/MA30 或 MA20/MA60），参数越大信号越可靠。'))
story.append(PN('（2）引入成交量过滤，金叉出现时若成交量未放大则暂缓买入。'))
story.append(PN('（3）结合 RSI、MACD 等辅助指标过滤无效信号。'))
story.append(PN('（4）采用分批建仓策略，降低单次错误信号的影响。'))
story.append(PN('（5）在震荡市中暂停策略，加入波动率过滤器（如 ATR）。'))

# 构建 PDF
doc.build(story)
print(f'PDF 报告已生成: {pdf_path}')
print(f'文件大小: {os.path.getsize(pdf_path):,} 字节')

# ===== 完成 =====
print('\n' + '=' * 60)
print('全部完成! 输出文件:')
print(f'  1. HTML 报告: {html_path}')
print(f'  2. PDF 报告:  {pdf_path}')
print(f'  3. 回测图表:  {chart_path}')
print('=' * 60)
