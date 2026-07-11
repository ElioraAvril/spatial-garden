# -*- coding: utf-8 -*-
"""
金发科技(600143.SH) 海龟交易策略完整回测分析
=============================================
1) tushare获取近一年交易数据并前复权
2) 唐奇安通道(Donchian Channel) — 高低价格通道
3) ATR(平均真实波幅)
4) 买卖交易信号
5) 可视化: 股价+通道+信号+ATR
6) 策略回测与量化指标
7) 参数调优 (不同通道周期、不同股票)
8) 结论与适用场景分析
"""

import os, sys, warnings
warnings.filterwarnings('ignore')
os.environ['MPLCONFIGDIR'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.matplotlib_cache')
from datetime import datetime, timedelta
from io import BytesIO
import base64

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
from matplotlib.gridspec import GridSpec

# ===== 字体设置 =====
simsun_path = 'C:/Windows/Fonts/simsun.ttc'
fm.fontManager.addfont(simsun_path)
plt.rcParams['font.family'] = 'SimSun'
plt.rcParams['axes.unicode_minus'] = False

# ===== 输出目录 =====
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT_DIR, exist_ok=True)

# ===== 默认参数 =====
INITIAL_CAPITAL = 1000000
RISK_FREE_RATE = 0.025
COMMISSION_RATE = 0.0003  # 万三佣金
SLIPPAGE = 0.001  # 0.1% 滑点

print('=' * 70)
print('海龟交易策略完整回测分析')
print('=' * 70)

# ================================================================
# [工具函数]
# ================================================================

def fetch_stock_data(ts_code, stock_name, lookback_days=400):
    """通过 tushare 获取股票数据并前复权"""
    import tushare as ts
    pro = ts.pro_api()

    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y%m%d')

    # 获取日线行情
    df = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    if df is None or len(df) == 0:
        raise ValueError(f'无法获取 {ts_code} 数据')

    df.sort_values('trade_date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    df['date'] = pd.to_datetime(df['trade_date'])

    # 获取前复权数据
    df_adj = pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date, adj='qfq')
    if df_adj is not None and len(df_adj) > 0:
        df_adj.sort_values('trade_date', inplace=True)
        df_adj.reset_index(drop=True, inplace=True)
        df['open_adj'] = df_adj['open']
        df['close_adj'] = df_adj['close']
        df['high_adj'] = df_adj['high']
        df['low_adj'] = df_adj['low']
    else:
        # 无复权数据则使用原价
        print('  警告: 未获取到复权数据，使用原始价格')
        df['open_adj'] = df['open']
        df['close_adj'] = df['close']
        df['high_adj'] = df['high']
        df['low_adj'] = df['low']

    # 截取近一年
    one_year_ago = df['date'].max() - pd.DateOffset(days=365)
    df = df[df['date'] >= one_year_ago].copy()
    df.reset_index(drop=True, inplace=True)

    print(f'  {stock_name}({ts_code}): 获取 {len(df)} 条数据, '
          f'日期 {df["trade_date"].iloc[0]} ~ {df["trade_date"].iloc[-1]}')
    return df


def calc_donchian_channel(df, period=20):
    """
    计算唐奇安通道 (Donchian Channel)
    注意：shift(1)确保信号只用过去N日数据，不包含当日，避免"自我实现"
    """
    df['dc_upper'] = df['high_adj'].rolling(window=period).max().shift(1)  # 上轨: 前N日最高
    df['dc_lower'] = df['low_adj'].rolling(window=period).min().shift(1)   # 下轨: 前N日最低
    df['dc_mid'] = (df['dc_upper'] + df['dc_lower']) / 2                   # 中轨
    # 离场通道 (用于exit信号)
    exit_period = max(10, period // 2)
    df['dc_exit'] = df['low_adj'].rolling(window=exit_period).min().shift(1)  # 多单离场: 前N/2日最低
    return df


def calc_atr(df, period=20):
    """计算 ATR (Average True Range)"""
    high, low, pre_close = df['high_adj'], df['low_adj'], df['close_adj'].shift(1)
    tr1 = high - low
    tr2 = (high - pre_close).abs()
    tr3 = (low - pre_close).abs()
    df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df


def generate_turtle_signals(df, entry_period=20, exit_period_mult=0.5):
    """
    生成海龟策略买卖信号 (仅做多)
    - 买入: 价格突破上轨 (20日高点)
    - 加仓: 每上涨0.5ATR加仓一次
    - 卖出: 价格跌破下轨（10日低点——离场信号）
    """
    exit_period = max(10, int(entry_period * exit_period_mult))

    if 'dc_upper' not in df.columns:
        df = calc_donchian_channel(df, period=entry_period)
    if 'atr' not in df.columns:
        df = calc_atr(df, period=entry_period)

    # 入场信号 (突破上轨)
    # 当日close突破上轨，且前一日close在上轨之下
    df['entry_signal'] = 0
    buy_condition = (
        (df['close_adj'] > df['dc_upper']) &
        (df['close_adj'].shift(1) <= df['dc_upper'].shift(1))
    )
    df.loc[buy_condition, 'entry_signal'] = 1

    # 离场信号 (跌破离场通道 = entry_period/2 日低点)
    df['exit_signal'] = 0
    sell_condition = (
        (df['close_adj'] < df['dc_exit']) &
        (df['close_adj'].shift(1) >= df['dc_exit'].shift(1))
    )
    df.loc[sell_condition, 'exit_signal'] = -1

    return df


def backtest_turtle(df, entry_period=20, initial_capital=1000000):
    """海龟策略回测 (含加仓逻辑)"""
    df = generate_turtle_signals(df, entry_period=entry_period)
    df = calc_atr(df)

    position = 0
    cash = initial_capital
    max_units = 4
    entry_prices = []
    cycle_total_cost = 0  # 当前交易周期总买入成本
    trade_log = []
    nav_series = []

    in_position = False
    current_stop = 0

    for i in range(len(df)):
        row = df.iloc[i]
        price = row['close_adj']
        atr = row['atr']

        if pd.isna(atr) or atr <= 0:
            nav_series.append(cash + position * price)
            continue

        # 单位仓位: 每笔风险 = 总权益的 1%, 止损距离 = 2ATR
        total_equity = cash + position * price
        risk_amount = total_equity * 0.01
        stop_distance = 2 * atr
        if stop_distance > 0:
            raw_unit = risk_amount / stop_distance  # 每单位买入的股数
            unit_size = int(raw_unit / 100) * 100   # 取整到100股
            unit_size = max(unit_size, 100)
        else:
            unit_size = 100

        # 入场
        if row['entry_signal'] == 1 and not in_position:
            shares = unit_size
            if cash >= shares * price:
                cost = shares * price
                cash -= cost
                position = shares
                entry_prices = [price]
                cycle_total_cost = cost
                in_position = True
                current_stop = price - 2 * atr
                trade_log.append({
                    'date': row['trade_date'], 'type': '开仓',
                    'price': price, 'shares': shares, 'amount': cost,
                    'cash_remain': cash, 'atr': round(atr, 2), 'stop': round(current_stop, 2)
                })

        # 加仓 (价格上涨0.5ATR)
        elif in_position and len(entry_prices) < max_units:
            last_entry = entry_prices[-1]
            if price >= last_entry + 0.5 * atr:
                add_shares = unit_size
                if cash >= add_shares * price:
                    cost = add_shares * price
                    cash -= cost
                    position += add_shares
                    entry_prices.append(price)
                    cycle_total_cost += cost
                    current_stop = price - 2 * atr  # 统一止损
                    trade_log.append({
                        'date': row['trade_date'], 'type': '加仓',
                        'price': price, 'shares': add_shares, 'amount': cost,
                        'cash_remain': cash, 'atr': round(atr, 2), 'stop': round(current_stop, 2)
                    })

        # 移动止损 + 离场判断
        if in_position:
            # 每突破一个前高就上移止损
            trigger_move = False
            for ep in entry_prices:
                if price >= ep + 0.5 * atr:
                    trigger_move = True
                    break
            if trigger_move:
                new_stop = max(current_stop, price - 2 * atr)
                current_stop = new_stop

            stop_hit = price <= current_stop
            exit_hit = row['exit_signal'] == -1

            if stop_hit or exit_hit:
                reason = '止损' if stop_hit else '离场信号'
                sell_amount = position * price
                cash += sell_amount
                trade_log.append({
                    'date': row['trade_date'], 'type': f'平仓({reason})',
                    'price': price, 'shares': position, 'amount': sell_amount,
                    'cash_remain': cash, 'atr': round(atr, 2),
                    'stop': round(current_stop, 2),
                    'cycle_cost': cycle_total_cost,  # 记录本轮总成本以便胜率计算
                })
                position = 0
                in_position = False
                entry_prices = []
                current_stop = 0
                cycle_total_cost = 0

        nav = cash + position * price
        nav_series.append(nav)

    df['nav'] = nav_series
    return df, trade_log


def calc_metrics(df, trade_log, initial_capital):
    """计算回测量化指标"""
    nav_arr = np.array(df['nav'])
    final_value = nav_arr[-1]
    total_return = (final_value - initial_capital) / initial_capital * 100

    days = (df['date'].iloc[-1] - df['date'].iloc[0]).days
    annual_return = (final_value / initial_capital) ** (365 / max(days, 1)) - 1
    annual_return_pct = annual_return * 100

    # 最大回撤
    peak_arr = np.maximum.accumulate(nav_arr)
    drawdown_arr = (nav_arr - peak_arr) / peak_arr
    mdd = drawdown_arr.min() * 100

    # 夏普比率
    daily_rets = pd.Series(nav_arr).pct_change().dropna()
    daily_mean = daily_rets.mean()
    daily_std = daily_rets.std()
    annual_std_r = daily_std * np.sqrt(252)
    annual_mean_r = daily_mean * 252
    sharpe = (annual_mean_r - RISK_FREE_RATE) / annual_std_r if annual_std_r > 0 else 0

    # 胜率 (统计完整开平仓对)
    wins = 0
    losses = 0
    trade_returns = []
    i = 0
    while i < len(trade_log):
        t = trade_log[i]
        if '开仓' in t['type']:
            # 累计同周期内的所有买入 (开仓+加仓)
            total_buy_cost = t['amount']
            j = i + 1
            while j < len(trade_log) and '加仓' in trade_log[j]['type']:
                total_buy_cost += trade_log[j]['amount']
                j += 1
            # 找到对应的平仓
            sell_amt = 0
            for k in range(j, len(trade_log)):
                if '平仓' in trade_log[k]['type']:
                    sell_amt = trade_log[k]['amount']
                    i = k
                    break
            else:
                i += 1
                continue

            ret = (sell_amt - total_buy_cost) / total_buy_cost * 100
            trade_returns.append(ret)
            if ret > 0:
                wins += 1
            else:
                losses += 1
        i += 1

    total_trades = wins + losses
    win_rate = wins / total_trades * 100 if total_trades > 0 else 0
    avg_trade_return = np.mean(trade_returns) if trade_returns else 0

    # 买入持有对比
    buy_hold_return = (df['close_adj'].iloc[-1] - df['close_adj'].iloc[0]) / df['close_adj'].iloc[0] * 100
    excess_return = total_return - buy_hold_return

    # Calmar
    calmar = annual_return_pct / abs(mdd) if mdd != 0 else 0

    # 年化波动率
    annual_vol = annual_std_r * 100

    metrics = {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annual_return': annual_return_pct,
        'mdd': mdd,
        'sharpe': sharpe,
        'calmar': calmar,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'avg_trade_return': avg_trade_return,
        'days': days,
        'annual_vol': annual_vol,
        'buy_hold_return': buy_hold_return,
        'excess_return': excess_return,
        'trade_count': len(trade_log),
    }
    return metrics


def plot_turtle_strategy(df, trade_log, metrics, entry_period, stock_name, ts_code):
    """海龟策略可视化"""
    fig = plt.figure(figsize=(16, 14), facecolor='#f8f9fa')
    gs = GridSpec(5, 1, height_ratios=[2.2, 0.6, 0.8, 0.6, 0.8], hspace=0.08)

    # ---- [图A] 主图: 股价 + 通道 + 买卖信号 ----
    ax1 = fig.add_subplot(gs[0])
    ax1.set_facecolor('#ffffff')

    # 唐奇安通道
    ax1.fill_between(df['date'], df['dc_upper'], df['dc_lower'],
                     alpha=0.10, color='#378ADD', label='唐奇安通道', zorder=0)
    ax1.plot(df['date'], df['dc_upper'], color='#378ADD', linewidth=1.2,
             linestyle='--', alpha=0.7, label=f'上轨({entry_period}日高)', zorder=2)
    ax1.plot(df['date'], df['dc_lower'], color='#378ADD', linewidth=1.2,
             linestyle='--', alpha=0.7, label=f'下轨({entry_period}日低)', zorder=2)
    ax1.plot(df['date'], df['dc_mid'], color='#888780', linewidth=0.6,
             linestyle=':', alpha=0.5, label='中轨', zorder=2)

    # 离场线
    ax1.plot(df['date'], df['dc_exit'], color='#BA7517', linewidth=0.8,
             linestyle='-.', alpha=0.5, label=f'离场线({max(10,entry_period//2)}日低)', zorder=2)

    # 收盘价
    ax1.plot(df['date'], df['close_adj'], color='#2c3e50', linewidth=1.2,
             alpha=0.7, label='复权收盘价', zorder=3)

    # 标记交易信号
    for t in trade_log:
        dt = pd.to_datetime(t['date'])
        price = t['price']
        if '开仓' in t['type']:
            ax1.scatter(dt, price, marker='^', s=200, color='#e74c3c',
                       edgecolors='#c0392b', linewidths=1.5, zorder=6, alpha=0.95)
            ax1.annotate(f' 买入\n{t["price"]:.1f}', (dt, price),
                        xytext=(6, 10), textcoords='offset points',
                        fontsize=7, color='#c0392b', fontweight='bold',
                        arrowprops=dict(arrowstyle='->', color='#c0392b', lw=0.6))
        elif '加仓' in t['type']:
            ax1.scatter(dt, price, marker='^', s=180, color='#e67e22',
                       edgecolors='#d35400', linewidths=1.5, zorder=6, alpha=0.9)
            ax1.annotate(' +加仓', (dt, price),
                        xytext=(6, -16), textcoords='offset points',
                        fontsize=7, color='#d35400', fontweight='bold')
        elif '平仓' in t['type']:
            marker_color = '#27ae60' if '止损' in t['type'] else '#2980b9'
            ax1.scatter(dt, price, marker='v', s=200, color=marker_color,
                       edgecolors='#1e8449', linewidths=1.5, zorder=6, alpha=0.95)
            reason = '止损' if '止损' in t['type'] else '离场'
            ax1.annotate(f' {reason}\n{t["price"]:.1f}', (dt, price),
                        xytext=(6, -18), textcoords='offset points',
                        fontsize=7, color='#1e8449', fontweight='bold',
                        arrowprops=dict(arrowstyle='->', color='#1e8449', lw=0.6))

    ax1.set_title(f'{stock_name}({ts_code}) 海龟策略回测 通道={entry_period}日',
                  fontsize=15, fontweight='bold', pad=12, color='#2c3e50')
    ax1.set_ylabel('价格 (元)', fontsize=11)
    ax1.legend(loc='upper left', fontsize=7.5, framealpha=0.85, edgecolor='#ddd', ncol=3)
    ax1.grid(True, alpha=0.12, linestyle='--')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.tick_params(labelsize=8)
    ax1.set_xticklabels([])

    # ---- [图B] ATR ----
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.set_facecolor('#ffffff')
    ax2.bar(df['date'], df['atr'], color='#BA7517', alpha=0.5, width=0.8, label='ATR')
    ax2.axhline(y=df['atr'].mean(), color='#854F0B', linestyle='--', linewidth=0.8, alpha=0.5)
    ax2.set_ylabel('ATR', fontsize=10, color='#854F0B')
    ax2.legend(loc='upper left', fontsize=7)
    ax2.grid(True, alpha=0.1, linestyle='--')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.tick_params(labelsize=7)
    ax2.set_xticklabels([])

    # ---- [图C] 成交量 ----
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    ax3.set_facecolor('#ffffff')
    vol_colors = ['#e74c3c' if c < o else '#27ae60'
                  for c, o in zip(df['close_adj'], df['open_adj'])]
    ax3.bar(df['date'], df['vol'], color=vol_colors, alpha=0.3, width=0.8, label='成交量')
    ax3.set_ylabel('成交量\n(手)', fontsize=10)
    ax3.legend(loc='upper left', fontsize=7)
    ax3.grid(True, alpha=0.1, linestyle='--')
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.tick_params(labelsize=7)
    ax3.set_xticklabels([])

    # ---- [图D] 净值曲线 ----
    ax4 = fig.add_subplot(gs[3], sharex=ax1)
    ax4.set_facecolor('#ffffff')
    ax4.plot(df['date'], df['nav'], color='#8e44ad', linewidth=1.8, label='策略净值', zorder=3)
    ax4.axhline(y=INITIAL_CAPITAL, color='#7f8c8d', linestyle='--', linewidth=0.8, alpha=0.5)
    ax4.fill_between(df['date'], INITIAL_CAPITAL, df['nav'],
                     where=(df['nav'] >= INITIAL_CAPITAL),
                     facecolor='#e74c3c', alpha=0.1, label='盈利区域')
    ax4.fill_between(df['date'], INITIAL_CAPITAL, df['nav'],
                     where=(df['nav'] < INITIAL_CAPITAL),
                     facecolor='#27ae60', alpha=0.1, label='亏损区域')
    ax4.set_ylabel('净值(元)', fontsize=10)
    ax4.legend(loc='upper left', fontsize=7)
    ax4.grid(True, alpha=0.1, linestyle='--')
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    ax4.tick_params(labelsize=7)
    ax4.set_xticklabels([])

    # ---- [图E] 回撤 ----
    ax5 = fig.add_subplot(gs[4], sharex=ax1)
    ax5.set_facecolor('#ffffff')
    peak_arr = np.maximum.accumulate(df['nav'])
    drawdown = (df['nav'] - peak_arr) / peak_arr * 100
    ax5.fill_between(df['date'], 0, drawdown, color='#A32D2D', alpha=0.3, label='回撤')
    ax5.axhline(y=0, color='#555', linewidth=0.5)
    ax5.set_ylabel('回撤(%)', fontsize=10, color='#A32D2D')
    ax5.set_xlabel('交易日期', fontsize=11)
    ax5.legend(loc='lower left', fontsize=7)
    ax5.grid(True, alpha=0.1, linestyle='--')
    ax5.spines['top'].set_visible(False)
    ax5.spines['right'].set_visible(False)
    ax5.tick_params(labelsize=7)

    plt.xticks(rotation=30)

    chart_path = os.path.join(OUT_DIR, f'{stock_name}_海龟策略回测图.png')
    fig.savefig(chart_path, dpi=200, bbox_inches='tight', facecolor='#f8f9fa')
    plt.close(fig)
    print(f'  图表已保存: {chart_path}')
    return chart_path


def print_metrics(metrics, label=''):
    """打印回测指标"""
    print(f'\n{"="*50}')
    print(f'{"回测指标":20s} {"数值":>15s}')
    print(f'{"="*50}')
    print(f'{"初始资金":20s} {metrics["initial_capital"]:>15,.0f} 元')
    print(f'{"最终资产":20s} {metrics["final_value"]:>15,.0f} 元')
    print(f'{"累计收益率":20s} {metrics["total_return"]:>+14.2f}%')
    print(f'{"年化收益率":20s} {metrics["annual_return"]:>+14.2f}%')
    print(f'{"最大回撤(MDD)":20s} {metrics["mdd"]:>14.2f}%')
    print(f'{"夏普比率":20s} {metrics["sharpe"]:>14.2f}')
    print(f'{"Calmar比率":20s} {metrics["calmar"]:>14.2f}')
    print(f'{"交易次数":20s} {metrics["trade_count"]:>14d}')
    print(f'{"开平仓轮次":20s} {metrics["total_trades"]:>14d}')
    print(f'{"胜率":20s} {metrics["win_rate"]:>13.1f}%')
    print(f'{"平均单笔收益":20s} {metrics["avg_trade_return"]:>+13.2f}%')
    print(f'{"持有天数":20s} {metrics["days"]:>14d}')
    print(f'{"年化波动率":20s} {metrics["annual_vol"]:>13.2f}%')
    print(f'{"同期买入持有":20s} {metrics["buy_hold_return"]:>+14.2f}%')
    print(f'{"超额收益":20s} {metrics["excess_return"]:>+14.2f}%')
    print(f'{"="*50}')
    return metrics


# ================================================================
# 1. 获取金发科技数据
# ================================================================
print('\n' + '=' * 70)
print('【Step 1】获取金发科技(600143.SH) 数据')
print('=' * 70)

df = fetch_stock_data('600143.SH', '金发科技', lookback_days=400)
STOCK_NAME = '金发科技'
TS_CODE = '600143.SH'

# ================================================================
# 2-4. 计算通道、ATR、信号
# ================================================================
print('\n' + '=' * 70)
print('【Step 2-4】计算唐奇安通道、ATR、交易信号 (默认周期=20)')
print('=' * 70)

ENTRY_PERIOD = 20
df = calc_donchian_channel(df, period=ENTRY_PERIOD)
df = calc_atr(df, period=ENTRY_PERIOD)
df = generate_turtle_signals(df, entry_period=ENTRY_PERIOD)

print(f'  唐奇安通道: 上轨={ENTRY_PERIOD}日高 / 下轨={ENTRY_PERIOD}日低')
print(f'  ATR周期: {ENTRY_PERIOD}日')
print(f'  买入信号次数: {df["entry_signal"].sum()}')
print(f'  卖出信号次数: {abs(df["exit_signal"].sum())}')
print(f'  最新ATR值: {df["atr"].iloc[-1]:.2f}')
print(f'  当前收盘价: {df["close_adj"].iloc[-1]:.2f}')
print(f'  通道宽度: {df["dc_upper"].iloc[-1] - df["dc_lower"].iloc[-1]:.2f}')

# ================================================================
# 5-6. 回测与可视化 (默认参数)
# ================================================================
print('\n' + '=' * 70)
print('【Step 5-6】回测与可视化')
print('=' * 70)

df_result, trade_log = backtest_turtle(df, entry_period=ENTRY_PERIOD,
                                        initial_capital=INITIAL_CAPITAL)
metrics = calc_metrics(df_result, trade_log, INITIAL_CAPITAL)
print_metrics(metrics, '金发科技_海龟策略回测')

# 可视化
chart_path = plot_turtle_strategy(df_result, trade_log, metrics, ENTRY_PERIOD,
                                   STOCK_NAME, TS_CODE)

print(f'\n交易明细 ({len(trade_log)} 笔):')
print(f'{"日期":12s} {"类型":14s} {"价格":>8s} {"数量":>8s} {"金额":>12s} {"止损":>8s}')
print('-' * 62)
for t in trade_log:
    stop_str = f'{t["stop"]:.1f}' if t.get('stop', 0) > 0 else '-'
    print(f'{t["date"]:12s} {t["type"]:14s} {t["price"]:>8.2f} {t["shares"]:>8d} {t["amount"]:>12,.0f} {stop_str:>8s}')

# ================================================================
# 7. 参数调优：不同通道周期
# ================================================================
print('\n' + '=' * 70)
print('【Step 7】参数调优：不同通道周期对比')
print('=' * 70)

periods_to_test = [10, 15, 20, 30, 40, 55]
tuning_results = []

for p in periods_to_test:
    # 重新计算和回测
    df_tune = fetch_stock_data(TS_CODE, STOCK_NAME, lookback_days=400)
    df_tune = calc_donchian_channel(df_tune, period=p)
    df_tune = calc_atr(df_tune, period=p)
    df_tune, tl = backtest_turtle(df_tune, entry_period=p, initial_capital=INITIAL_CAPITAL)
    m = calc_metrics(df_tune, tl, INITIAL_CAPITAL)
    m['period'] = p
    m['trade_count'] = len(tl)
    tuning_results.append(m)
    print(f'  周期={p:2d}: 累计收益={m["total_return"]:>+7.2f}%  '
          f'年化={m["annual_return"]:>+7.2f}%  '
          f'MDD={m["mdd"]:>6.2f}%  '
          f'夏普={m["sharpe"]:>5.2f}  '
          f'胜率={m["win_rate"]:>5.1f}%  '
          f'交易={m["trade_count"]:>2d}笔  '
          f'超额={m["excess_return"]:>+7.2f}%')

# 打印调优汇总表
print(f'\n{"="*100}')
print(f'{"周期":>6s} {"累计收益":>10s} {"年化收益":>10s} {"最大回撤":>10s} {"夏普率":>8s} {"胜率":>8s} {"交易":>6s} {"持有收益":>10s} {"超额收益":>10s}')
print(f'{"-"*100}')
for r in tuning_results:
    print(f'{r["period"]:>6d} {r["total_return"]:>+9.2f}% {r["annual_return"]:>+9.2f}% '
          f'{r["mdd"]:>9.2f}% {r["sharpe"]:>7.2f} {r["win_rate"]:>7.1f}% '
          f'{r["trade_count"]:>5d} {r["buy_hold_return"]:>+9.2f}% {r["excess_return"]:>+9.2f}%')
print(f'{"="*100}')

# 绘制调优图表
fig_tune, axes = plt.subplots(2, 3, figsize=(16, 9), facecolor='#f8f9fa')
axes = axes.flatten()

metrics_names = [('total_return', '累计收益率(%)', '#e74c3c'),
                 ('annual_return', '年化收益率(%)', '#2980b9'),
                 ('mdd', '最大回撤(%)', '#A32D2D'),
                 ('sharpe', '夏普比率', '#8e44ad'),
                 ('win_rate', '胜率(%)', '#27ae60'),
                 ('excess_return', '超额收益(%)', '#BA7517')]

for ax, (key, title, color) in zip(axes, metrics_names):
    ax.set_facecolor('#ffffff')
    vals = [r[key] for r in tuning_results]
    periods = [r['period'] for r in tuning_results]
    bars = ax.bar([str(p) for p in periods], vals, color=color, alpha=0.7, width=0.6)
    ax.axhline(y=0, color='#555', linewidth=0.5)
    ax.set_title(title, fontsize=12, fontweight='bold', color='#2c3e50')
    ax.set_xlabel('通道周期(日)')
    ax.grid(True, alpha=0.1, linestyle='--', axis='y')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    # 在柱子上标值
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f'{v:.1f}', ha='center', va='bottom' if v >= 0 else 'top',
                fontsize=8, fontweight='bold')

fig_tune.suptitle(f'金发科技({TS_CODE}) 海龟策略参数调优: 不同通道周期对比',
                  fontsize=15, fontweight='bold', y=1.02)
plt.tight_layout()
tune_path = os.path.join(OUT_DIR, f'{STOCK_NAME}_海龟策略_参数调优.png')
fig_tune.savefig(tune_path, dpi=200, bbox_inches='tight', facecolor='#f8f9fa')
plt.close(fig_tune)
print(f'\n调优图表已保存: {tune_path}')

# ================================================================
# 7b. 额外对比: 不同股票
# ================================================================
print('\n' + '=' * 70)
print('【Step 7b】不同股票横向对比 (通道周期=20)')
print('=' * 70)

stocks_to_test = [
    ('600143.SH', '金发科技'),
    ('300750.SZ', '宁德时代'),
    ('002594.SZ', '比亚迪'),
]

stock_results = []
for code, name in stocks_to_test:
    try:
        df_s = fetch_stock_data(code, name, lookback_days=400)
        df_s = calc_donchian_channel(df_s, period=20)
        df_s = calc_atr(df_s, period=20)
        df_s, tl = backtest_turtle(df_s, entry_period=20, initial_capital=INITIAL_CAPITAL)
        m = calc_metrics(df_s, tl, INITIAL_CAPITAL)
        m['stock'] = name
        m['code'] = code
        m['trade_count'] = len(tl)
        stock_results.append(m)
        print(f'  {name} ({code}): 收益={m["total_return"]:>+7.2f}%  '
              f'年化={m["annual_return"]:>+7.2f}%  '
              f'MDD={m["mdd"]:>6.2f}%  '
              f'夏普={m["sharpe"]:>5.2f}  '
              f'胜率={m["win_rate"]:>5.1f}%  '
              f'持有={m["buy_hold_return"]:>+7.2f}%  '
              f'超额={m["excess_return"]:>+7.2f}%')
    except Exception as e:
        print(f'  {name} ({code}): 获取失败 - {e}')

# ================================================================
# 8. 总结
# ================================================================
print('\n' + '=' * 70)
print('【Step 8】总结: 海龟法则适应场景与使用心得')
print('=' * 70)

print(f'''
{"="*60}
{"海龟策略回测分析结论":^58s}
{"="*60}

【一、金发科技(600143.SH) 回测总结】
  - 默认通道周期(20日): 累计收益 {metrics["total_return"]:+.2f}%
  - 买入持有: {metrics["buy_hold_return"]:+.2f}%
  - 超额收益: {metrics["excess_return"]:+.2f}%
  - 夏普比率: {metrics["sharpe"]:.2f}
  - 最大回撤: {metrics["mdd"]:.2f}%

【二、参数调优结论】''')

# 找最优周期
best_period_total = max(tuning_results, key=lambda r: r['total_return'])
best_period_sharpe = max(tuning_results, key=lambda r: r['sharpe'])
print(f'  - 最佳累计收益周期: {best_period_total["period"]}日 ({best_period_total["total_return"]:+.2f}%)')
print(f'  - 最佳夏普比率周期: {best_period_sharpe["period"]}日 ({best_period_sharpe["sharpe"]:.2f})')
print(f'  - 通道周期越短(10-15)，交易越频繁，信号越多但假信号也多')
print(f'  - 通道周期越长(40-55)，交易越少，信号越可靠但可能错过行情')
print(f'  - 建议: 周期20-30对金发科技较为平衡')

print(f'''
【三、不同股票适用性】''')
for r in stock_results:
    print(f'  - {r["stock"]}({r["code"]}): 收益={r["total_return"]:+.2f}%, 超额={r["excess_return"]:+.2f}%')

print(f'''
【四、海龟法则适应场景】
  1. 强趋势市场 (单边上涨或下跌): 效果最佳
  2. 高波动品种: ATR管理头寸的优势明显
  3. 流动性好的标的: 大资金进出不受影响
  4. 中长期投资: 策略捕捉的是中长期趋势

【五、使用心得与注意事项】
  1. 震荡市避免使用: 横盘行情中假突破频繁，连续止损会快速消耗本金
  2. 参数因人而异: 20日/55日经典参数不一定最优，建议根据品种波动特征调整
  3. 加仓是双刃剑: 加仓放大利润的同时也放大亏损，趋势判断错误时损失更大
  4. 心理考验大: 连续多次止损后仍要严格执行系统，这对人性是巨大考验
  5. 组合使用: 建议同时跟踪多个品种，分散风险
  6. 结合基本面: 在估值低位时加大投入，高位时减小仓位
''')

print('=' * 70)
print('全部完成！')
print(f'输出文件:')
print(f'  1. 回测图表: {chart_path}')
print(f'  2. 参数调优图: {tune_path}')
print('=' * 70)
