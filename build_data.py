"""
Step 1: 获取宁德时代所有数据，输出为 outputs/ningde_data.json
"""
import urllib.request, json, os, math, sys
from datetime import datetime, timedelta

TOKEN = "YOUR_TUSHARE_TOKEN"  # 替换为你的 Tushare Token
API = "https://api.tushare.pro"
TS_CODE = "300750.SZ"

def tushare(name, params, fields=""):
    p = {"api_name": name, "token": TOKEN, "params": params}
    if fields: p["fields"] = fields
    d = json.dumps(p).encode()
    req = urllib.request.Request(API, data=d, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())
    if res.get("code") != 0:
        raise Exception(f"API error: {res.get('msg')}")
    return res["data"]["items"], res["data"]["fields"]

end = datetime.now().strftime("%Y%m%d")
start = (datetime.now() - timedelta(days=380)).strftime("%Y%m%d")
print(f"Fetching {TS_CODE} {start}~{end} ...")

# 1. Daily data
items, _ = tushare("daily", {"ts_code": TS_CODE, "start_date": start, "end_date": end},
    "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount")
items.sort(key=lambda x: x[1])

# 2. Adj factor
try:
    af, _ = tushare("adj_factor", {"ts_code": TS_CODE, "start_date": start, "end_date": end},
        "ts_code,trade_date,adj_factor")
    adj_map = {r[1]: float(r[2]) for r in af}
    print(f"  adj_factor: {len(adj_map)} rows")
except:
    adj_map = {}

# 3. Financial data
try:
    fina, _ = tushare("fina_indicator", {"ts_code": TS_CODE, "start_date": "20240101", "end_date": end},
        "ts_code,end_date,eps,roe,roe_yearly,netprofit_yoy,grossprofit_margin,netprofit_margin,revenue,total_revenue_ps,current_ratio,quick_ratio,debt_to_assets")
    fina.sort(key=lambda x: x[1], reverse=True)
    print(f"  fina_indicator: {len(fina)} rows")
except Exception as e:
    fina = []
    print(f"  fina_indicator: failed ({e})")

# 4. Income statement
try:
    income, _ = tushare("income", {"ts_code": TS_CODE, "start_date": "20230101", "end_date": end},
        "ts_code,end_date,revenue,total_cogs,operate_profit,total_profit,n_income,n_income_attr_p")
    income.sort(key=lambda x: x[1], reverse=True)
    print(f"  income: {len(income)} rows")
except:
    income = []

# 5. Balance sheet
try:
    bs, _ = tushare("balancesheet", {"ts_code": TS_CODE, "start_date": "20230101", "end_date": end},
        "ts_code,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int")
    bs.sort(key=lambda x: x[1], reverse=True)
    print(f"  balancesheet: {len(bs)} rows")
except:
    bs = []

# 6. News
try:
    news, _ = tushare("news", {
        "start_date": (datetime.now()-timedelta(days=30)).strftime("%Y%m%d"),
        "end_date": end, "src": "eastmoney,sina,10jqka"},
        "datetime,content,src")
    news.sort(key=lambda x: x[0], reverse=True)
    print(f"  news: {len(news)} total")
except:
    news = []

# ========== Parse ==========
tds = [r[1] for r in items]
dates_str = [f"{r[1][:4]}-{r[1][4:6]}-{r[1][6:]}" for r in items]
opens = [float(r[2]) for r in items]
highs = [float(r[3]) for r in items]
lows  = [float(r[4]) for r in items]
closes = [float(r[5]) for r in items]
pcts  = [float(r[8]) for r in items]
vols  = [float(r[9]) for r in items]
amts  = [float(r[10]) for r in items]

# Adj prices
adj_vals = [adj_map.get(td, 1.0) for td in tds]
la, fa = adj_vals[-1] if adj_vals else 1.0, adj_vals[0] if adj_vals else 1.0
cq  = [c*a/la for c,a in zip(closes, adj_vals)]
oqfq = [o*a/la for o,a in zip(opens, adj_vals)]
hqfq = [h*a/la for h,a in zip(highs, adj_vals)]
lqfq = [l*a/la for l,a in zip(lows, adj_vals)]
ch  = [c*a/fa for c,a in zip(closes, adj_vals)]
ohfq = [o*a/fa for o,a in zip(opens, adj_vals)]
hhfq = [h*a/fa for h,a in zip(highs, adj_vals)]
lhfq = [l*a/fa for l,a in zip(lows, adj_vals)]

# Technical indicators
def ma(data, n):
    return [None if i < n-1 else sum(data[i-n+1:i+1])/n for i in range(len(data))]

def rsi(data, n=14):
    g, l = [max(data[i]-data[i-1], 0) for i in range(1, len(data))], [max(data[i-1]-data[i], 0) for i in range(1, len(data))]
    rs = [None]*(n+1)
    ag, al = sum(g[:n])/n, sum(l[:n])/n
    rs.append(100-(100/(1+ag/al)) if al > 0 else 100)
    for i in range(n, len(g)):
        ag, al = (ag*13+g[i])/14, (al*13+l[i])/14
        rs.append(100-(100/(1+ag/al)) if al > 0 else 100)
    return rs

def macd(data, fast=12, slow=26, signal=9):
    ema_f = [data[0]]; ema_s = [data[0]]
    for i in range(1, len(data)):
        ema_f.append(data[i]*2/(fast+1) + ema_f[-1]*(fast-1)/(fast+1))
        ema_s.append(data[i]*2/(slow+1) + ema_s[-1]*(slow-1)/(slow+1))
    dif = [f - s for f, s in zip(ema_f, ema_s)]
    dea = [sum(dif[:signal])/signal]
    for i in range(signal, len(dif)):
        dea.append(dif[i]*2/(signal+1) + dea[-1]*(signal-1)/(signal+1))
    hist = [2*(dif[i] - dea[i]) for i in range(len(dea))]
    dif2 = dif[:len(dea)]
    return dif2, dea, hist

def boll(data, n=20, k=2):
    mb = [None]*(n-1)
    up = [None]*(n-1)
    dn = [None]*(n-1)
    for i in range(n-1, len(data)):
        chunk = data[i-n+1:i+1]
        m = sum(chunk)/n
        std = math.sqrt(sum((x-m)**2 for x in chunk)/n)
        mb.append(m); up.append(m+k*std); dn.append(m-k*std)
    return mb, up, dn

ma5, ma10, ma20, ma60 = ma(closes,5), ma(closes,10), ma(closes,20), ma(closes,60)
rsi14 = rsi(closes)
dif, dea, macd_hist = macd(closes)
boll_mb, boll_up, boll_dn = boll(closes)

# Volatility
vol20 = [None]*19
for i in range(19, len(pcts)):
    chunk = pcts[i-19:i+1]; m = sum(chunk)/20
    vol20.append(math.sqrt(sum((x-m)**2 for x in chunk)/20))

n_idx = len(dates_str) - 1
high_52w = max(highs[-250:]) if len(highs) >= 250 else max(highs)
low_52w = min(lows[-250:]) if len(lows) >= 250 else min(lows)
avg_vol = sum(vols[-60:])/len(vols[-60:])/100

# MA trend
if ma5[n_idx] and ma10[n_idx] and ma20[n_idx]:
    if ma5[n_idx] > ma10[n_idx] > ma20[n_idx]:
        ma_trend = "多头排列"
    elif ma5[n_idx] < ma10[n_idx] < ma20[n_idx]:
        ma_trend = "空头排列"
    else:
        ma_trend = "交叉震荡"
else:
    ma_trend = "--"

# Financial metrics
fin_data = {}
if fina:
    for row in fina:
        dt = row[1]
        fin_data[dt] = {
            "eps": row[2], "roe": row[3], "roe_yearly": row[4],
            "np_yoy": row[5], "gross_margin": row[6], "net_margin": row[7],
            "revenue": row[8], "rev_ps": row[9],
            "current_ratio": row[10], "quick_ratio": row[11], "debt_ratio": row[12]
        }

# Income / BS
inc_data = {}
for row in income:
    inc_data[row[1]] = {"revenue": row[2], "cogs": row[3], "op_profit": row[4], "total_profit": row[5], "net_income": row[6], "net_income_p": row[7]}

bs_data = {}
for row in bs:
    bs_data[row[1]] = {"total_assets": row[2], "total_liab": row[3], "equity": row[4]}

# News filter
relevant_news = []
kw_list = ["宁德", "电池", "新能源", "CATL", "300750", "动力电池", "储能"]
for n in news:
    content = n[1]
    if any(kw in content for kw in kw_list):
        relevant_news.append({"date": n[0][:10], "content": content[:120], "src": n[2]})
    if len(relevant_news) >= 6: break

# ====== Build JSON ======
data = {
    "meta": {
        "ts_code": TS_CODE, "name": "宁德时代", "sector": "创业板", "industry": "新能源电池",
        "data_count": len(items), "date_range": [tds[0], tds[-1]],
    },
    "dates": dates_str, "trade_dates": tds,
    "price": {
        "open": opens, "high": highs, "low": lows, "close": closes, "pct_chg": pcts,
        "vol": vols, "amount": amts, "adj_factor": [round(x,6) for x in adj_vals],
    },
    "adj": {
        "qfq_open": oqfq, "qfq_close": cq, "qfq_high": hqfq, "qfq_low": lqfq,
        "hfq_open": ohfq, "hfq_close": ch, "hfq_high": hhfq, "hfq_low": lhfq,
    },
    "ta": {
        "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
        "rsi14": rsi14, "vol20": vol20,
        "macd_dif": dif, "macd_dea": dea, "macd_hist": macd_hist,
        "boll_mb": boll_mb, "boll_up": boll_up, "boll_dn": boll_dn,
    },
    "summary": {
        "latest_close": closes[-1], "latest_pct": pcts[-1],
        "high_52w": high_52w, "low_52w": low_52w,
        "avg_vol_wan": round(avg_vol, 1),
        "ma_trend": ma_trend,
        "rsi": rsi14[-1] if rsi14[-1] else None,
        "vol20": vol20[-1] if vol20[-1] else None,
        "qfq_close": cq[-1], "hfq_close": ch[-1],
        "ret_raw": (closes[-1] - closes[0]) / closes[0] * 100,
        "ret_qfq": (cq[-1] - cq[0]) / cq[0] * 100,
        "ret_hfq": (ch[-1] - ch[0]) / ch[0] * 100,
    },
    "financial": fin_data,
    "income": {k: {"revenue": v["revenue"], "net_income": v["net_income_p"]} for k,v in inc_data.items()},
    "balance": {k: {"assets": v["total_assets"], "liab": v["total_liab"], "equity": v["equity"]} for k,v in bs_data.items()},
    "news": relevant_news,
}

out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(out_dir, exist_ok=True)
json_path = os.path.join(out_dir, "ningde_data.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, default=str)

# Save adj CSV too
csv_path = os.path.join(out_dir, "ningde_era_adj.csv")
with open(csv_path, "w", encoding="utf-8-sig") as f:
    f.write("trade_date,open,high,low,close,pct_chg,vol,amount,adj_factor,open_qfq,close_qfq,high_qfq,low_qfq,open_hfq,close_hfq,high_hfq,low_hfq\n")
    for i in range(len(items)):
        f.write(f"{tds[i]},{opens[i]:.2f},{highs[i]:.2f},{lows[i]:.2f},{closes[i]:.2f},{pcts[i]:.2f},{vols[i]:.0f},{amts[i]:.0f},{adj_vals[i]:.6f},{oqfq[i]:.2f},{cq[i]:.2f},{hqfq[i]:.2f},{lqfq[i]:.2f},{ohfq[i]:.2f},{ch[i]:.2f},{hhfq[i]:.2f},{lhfq[i]:.2f}\n")

print(f"\nDone!")
print(f"  JSON: outputs/ningde_data.json ({len(items)} records)")
print(f"  CSV:  outputs/ningde_era_adj.csv")
print(f"  Latest close: {closes[-1]:.2f}, pct: {pcts[-1]:.2f}%")
print(f"  QFQ close: {cq[-1]:.2f}, HFQ close: {ch[-1]:.2f}")
