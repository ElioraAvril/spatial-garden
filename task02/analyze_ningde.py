# -*- coding: utf-8 -*-
"""
宁德时代(300750.SZ) 日线数据诊断分析
- 缺失值检测
- 描述性统计量
- 数据质量评估
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np

# ============================================================
# 1. 读取数据
# ============================================================
df = pd.read_csv(
    'outputs/ningde_era_daily.csv',
    encoding='utf-8-sig',
    parse_dates=['trade_date']
)

print("=" * 70)
print("  宁德时代 (300750.SZ) 日线数据 --- 诊断分析报告")
print("=" * 70)

# ============================================================
# 2. 基本信息
# ============================================================
print("\n" + "-" * 70)
print("【一、数据概览】")
print("-" * 70)
print(f"  股票代码: {df['ts_code'].iloc[0]}")
print(f"  数据条数: {len(df)} 条")
print(f"  时间范围: {df['trade_date'].min().strftime('%Y-%m-%d')} 至 {df['trade_date'].max().strftime('%Y-%m-%d')}")
print(f"  变量个数: {len(df.columns)} 个")
print(f"  变量列表: {', '.join(df.columns.tolist())}")

print("\n  前 5 行预览:")
print(df.head().to_string(index=False))

print("\n  后 5 行预览:")
print(df.tail().to_string(index=False))

# ============================================================
# 3. 数据类型检查
# ============================================================
print("\n" + "-" * 70)
print("【二、数据类型检查】")
print("-" * 70)
dtype_df = pd.DataFrame({
    '变量': df.columns,
    '数据类型': df.dtypes.values,
    'Python类型': [str(df[c].dtype) for c in df.columns]
})
print(dtype_df.to_string(index=False))

# ============================================================
# 4. 缺失值分析
# ============================================================
print("\n" + "-" * 70)
print("【三、缺失值分析】")
print("-" * 70)

missing = df.isnull().sum()
missing_pct = (missing / len(df)) * 100
missing_df = pd.DataFrame({
    '变量': df.columns,
    '缺失数量': missing.values,
    '缺失比例(%)': missing_pct.values.round(2)
})
missing_df = missing_df[missing_df['缺失数量'] > 0]

if len(missing_df) == 0:
    print("  [OK] 未发现缺失值，所有变量数据完整。")
else:
    print("  [WARN] 发现缺失值! 详情如下:")
    print(missing_df.to_string(index=False))

# 检查空字符串
print("\n  [空字符串检查]")
for col in df.select_dtypes(include=['object']).columns:
    empty_count = (df[col] == '').sum() + (df[col].isnull()).sum()
    if empty_count > 0:
        print(f"  [WARN] {col}: {empty_count} 个空值/空字符串")
    else:
        print(f"  [OK] {col}: 无空值")

# ============================================================
# 5. 描述性统计量
# ============================================================
print("\n" + "-" * 70)
print("【四、描述性统计量 --- 价格类变量 (元)】")
print("-" * 70)

price_cols = ['open', 'high', 'low', 'close', 'pre_close']
price_stats = df[price_cols].describe()
print(price_stats.to_string())

print("\n" + "-" * 70)
print("【四、描述性统计量 --- 价格变化】")
print("-" * 70)
change_stats = df[['change', 'pct_chg']].describe()
print(change_stats.to_string())

print("\n" + "-" * 70)
print("【四、描述性统计量 --- 成交量和成交额】")
print("-" * 70)
vol_amt_stats = df[['vol', 'amount']].describe()
print(vol_amt_stats.to_string())
print("\n  注: vol 单位为手(100股), amount 单位为万元")

# ============================================================
# 6. 更多统计指标
# ============================================================
print("\n" + "-" * 70)
print("【五、补充统计指标 --- 收盘价】")
print("-" * 70)

close = df['close']
print(f"  均值 (Mean):          {close.mean():.2f} 元")
print(f"  中位数 (Median):       {close.median():.2f} 元")
print(f"  标准差 (Std):          {close.std():.2f} 元")
print(f"  方差 (Variance):       {close.var():.2f}")
print(f"  最小值 (Min):          {close.min():.2f} 元  ({df.loc[close.idxmin(), 'trade_date'].strftime('%Y-%m-%d')})")
print(f"  最大值 (Max):          {close.max():.2f} 元  ({df.loc[close.idxmax(), 'trade_date'].strftime('%Y-%m-%d')})")
print(f"  极差 (Range):          {close.max() - close.min():.2f} 元")
print(f"  偏度 (Skewness):       {close.skew():.4f}")
print(f"  峰度 (Kurtosis):       {close.kurtosis():.4f}")
print(f"  25% 分位数 (Q1):       {close.quantile(0.25):.2f} 元")
print(f"  75% 分位数 (Q3):       {close.quantile(0.75):.2f} 元")
print(f"  四分位距 (IQR):        {close.quantile(0.75) - close.quantile(0.25):.2f} 元")
print(f"  变异系数 (CV):         {close.std() / close.mean() * 100:.2f}%")

print("\n" + "-" * 70)
print("【五、补充统计指标 --- 涨跌幅(%)】")
print("-" * 70)
pct = df['pct_chg']
print(f"  均值 (Mean):          {pct.mean():.4f}%")
print(f"  中位数 (Median):       {pct.median():.4f}%")
print(f"  标准差 (Std):          {pct.std():.4f}%")
print(f"  最小跌幅:              {pct.min():.4f}%  ({df.loc[pct.idxmin(), 'trade_date'].strftime('%Y-%m-%d')})")
print(f"  最大涨幅:              {pct.max():.4f}%  ({df.loc[pct.idxmax(), 'trade_date'].strftime('%Y-%m-%d')})")
print(f"  偏度 (Skewness):       {pct.skew():.4f}")
print(f"  峰度 (Kurtosis):       {pct.kurtosis():.4f}")

# 涨跌天数统计
up_days = (df['change'] > 0).sum()
down_days = (df['change'] < 0).sum()
flat_days = (df['change'] == 0).sum()
print(f"\n  上涨天数: {up_days} ({up_days/len(df)*100:.1f}%)")
print(f"  下跌天数: {down_days} ({down_days/len(df)*100:.1f}%)")
print(f"  平盘天数: {flat_days} ({flat_days/len(df)*100:.1f}%)")

# ============================================================
# 7. 异常值检测 (基于 IQR 方法)
# ============================================================
print("\n" + "-" * 70)
print("【六、异常值检测 (IQR 方法, 收盘价)】")
print("-" * 70)
Q1 = close.quantile(0.25)
Q3 = close.quantile(0.75)
IQR = Q3 - Q1
lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR
print(f"  Q1 = {Q1:.2f}, Q3 = {Q3:.2f}, IQR = {IQR:.2f}")
print(f"  下界 = {lower:.2f}, 上界 = {upper:.2f}")

outliers = df[(close < lower) | (close > upper)]
if len(outliers) == 0:
    print("  [OK] 未发现 IQR 异常值。")
else:
    print(f"  发现 {len(outliers)} 个异常值:")
    for _, row in outliers.iterrows():
        print(f"    {row['trade_date'].strftime('%Y-%m-%d')}: 收盘价 {row['close']:.2f}")

# 3-sigma 异常值检测
print("\n  [3-Sigma 方法, 收盘价]")
mean_c = close.mean()
std_c = close.std()
sigma_upper = mean_c + 3 * std_c
sigma_lower = mean_c - 3 * std_c
print(f"  mu = {mean_c:.2f}, sigma = {std_c:.2f}")
print(f"  下界 = {sigma_lower:.2f}, 上界 = {sigma_upper:.2f}")
outliers_3s = df[(close < sigma_lower) | (close > sigma_upper)]
if len(outliers_3s) == 0:
    print("  [OK] 未发现 3-sigma 异常值。")
else:
    print(f"  发现 {len(outliers_3s)} 个异常值:")
    for _, row in outliers_3s.iterrows():
        print(f"    {row['trade_date'].strftime('%Y-%m-%d')}: 收盘价 {row['close']:.2f}")

# ============================================================
# 8. 日期连续性检查
# ============================================================
print("\n" + "-" * 70)
print("【七、交易日期连续性检查】")
print("-" * 70)
df_sorted = df.sort_values('trade_date').reset_index(drop=True)
gaps = []
for i in range(1, len(df_sorted)):
    diff = (df_sorted.loc[i, 'trade_date'] - df_sorted.loc[i-1, 'trade_date']).days
    if diff > 5:
        gaps.append((df_sorted.loc[i-1, 'trade_date'], df_sorted.loc[i, 'trade_date'], diff))

if gaps:
    print(f"  发现 {len(gaps)} 个较大交易间隔 (>5天):")
    for start, end, days in gaps:
        print(f"    {start.strftime('%Y-%m-%d')} -> {end.strftime('%Y-%m-%d')} (间隔 {days} 天)")
else:
    print("  [OK] 交易日期间隔均正常 (<=5天)。")

# ============================================================
# 9. 数据一致性校验
# ============================================================
print("\n" + "-" * 70)
print("【八、数据一致性校验】")
print("-" * 70)

# 检查 OHLC 逻辑: low <= open/close <= high
ohlc_ok = (
    (df['low'] <= df['open']) & (df['open'] <= df['high']) &
    (df['low'] <= df['close']) & (df['close'] <= df['high'])
).all()
print(f"  [OK] OHLC 价格逻辑 (low<=open/close<=high): {'通过' if ohlc_ok else '失败'}")

# 检查 change = close - pre_close
change_check = (df['change'].round(2) == (df['close'] - df['pre_close']).round(2)).all()
print(f"  [OK] change = close - pre_close: {'通过' if change_check else '失败'}")

# 检查 pct_chg ~ change / pre_close * 100
pct_check = (df['pct_chg'].round(4) == (df['change'] / df['pre_close'] * 100).round(4)).all()
print(f"  [OK] pct_chg = change / pre_close * 100: {'通过' if pct_check else '失败'}")

# 检查前一日收盘 = 当日 pre_close (考虑日期连续性)
df_sorted = df.sort_values('trade_date').reset_index(drop=True)
pre_close_match = 0
pre_close_mismatch = 0
for i in range(1, len(df_sorted)):
    if abs(df_sorted.loc[i, 'pre_close'] - df_sorted.loc[i-1, 'close']) < 0.01:
        pre_close_match += 1
    else:
        pre_close_mismatch += 1
print(f"  [OK] pre_close 与前一交易日 close 一致: {pre_close_match}/{pre_close_match+pre_close_mismatch} 条匹配")

print("\n" + "=" * 70)
print("  分析完成。")
print("=" * 70)
