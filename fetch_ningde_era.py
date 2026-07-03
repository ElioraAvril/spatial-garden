"""
获取宁德时代(300750.SZ)近一年日线行情，生成收盘价曲线、CSV、HTML面板
"""
import urllib.request
import json
import os
from datetime import datetime, timedelta

TOKEN = "YOUR_TUSHARE_TOKEN"  # 替换为你的 Tushare Token
API_URL = "https://api.tushare.pro"
TS_CODE = "300750.SZ"
STOCK_NAME = "宁德时代"

end_date = datetime.now().strftime("%Y%m%d")
start_date = (datetime.now() - timedelta(days=380)).strftime("%Y%m%d")

print(f"获取 {STOCK_NAME}({TS_CODE}) 从 {start_date} 到 {end_date} ...")

payload = json.dumps({
    "api_name": "daily",
    "token": TOKEN,
    "params": {"ts_code": TS_CODE, "start_date": start_date, "end_date": end_date},
    "fields": "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount"
}).encode("utf-8")

req = urllib.request.Request(API_URL, data=payload, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read().decode("utf-8"))

if result.get("code") != 0:
    print(f"API 错误: {result.get('msg')}")
    exit(1)

items = result["data"]["items"]
fields = result["data"]["fields"]
if not items:
    print("无数据"); exit(1)

items.sort(key=lambda x: x[1])

output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(output_dir, exist_ok=True)

# CSV
csv_path = os.path.join(output_dir, "ningde_era_daily.csv")
with open(csv_path, "w", encoding="utf-8-sig") as f:
    f.write(",".join(fields) + "\n")
    for row in items:
        f.write(",".join(str(v) for v in row) + "\n")
print(f"CSV: {csv_path}  |  {len(items)} 条  {items[0][1]}~{items[-1][1]}")

# 解析数据
dates = [f"{r[1][:4]}-{r[1][4:6]}-{r[1][6:]}" for r in items]
opens = [float(r[2]) for r in items]
highs = [float(r[3]) for r in items]
lows  = [float(r[4]) for r in items]
closes = [float(r[5]) for r in items]
pcts = [float(r[8]) for r in items]
vols  = [float(r[9]) for r in items]
amounts = [float(r[10]) for r in items]

# ──────────── 收盘价曲线 HTML ────────────
data_pairs = ", ".join(f"['{dates[i]}',{closes[i]:.2f}]" for i in range(len(dates)))
pct_pairs = ", ".join(f"{{value:{p:.2f},itemStyle:{{color:'{'#e53935' if p>=0 else '#43a047'}'}}}}" for p in pcts)

chart_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{STOCK_NAME}(300750.SZ) 收盘价曲线</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f6fa}}
.header{{background:linear-gradient(135deg,#1a237e,#283593);color:#fff;padding:20px 30px;text-align:center}}
.header h1{{font-size:22px;margin-bottom:4px}}.header .code{{font-size:13px;opacity:0.8}}
.container{{max-width:1200px;margin:0 auto;padding:20px}}
.card{{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:16px;overflow:hidden}}
.card-header{{padding:14px 20px;border-bottom:1px solid #e8e8e8;font-size:15px;font-weight:600}}
.chart-box{{width:100%;height:500px}}
.stats{{display:flex;justify-content:center;gap:30px;padding:16px 20px;flex-wrap:wrap}}
.stat-item{{text-align:center}}.stat-label{{font-size:12px;color:#999}}.stat-value{{font-size:20px;font-weight:700}}
.stat-value.up{{color:#e53935}}.stat-value.down{{color:#43a047}}
</style>
</head>
<body>
<div class="header"><h1>{STOCK_NAME} 收盘价曲线</h1><div class="code">300750.SZ · 创业板 · 新能源电池</div></div>
<div class="container">
<div class="stats" id="stats"></div>
<div class="card"><div class="card-header">每日收盘价走势</div><div class="chart-box" id="chart"></div></div>
<div class="card"><div class="card-header">每日涨跌幅</div><div class="chart-box" id="pctChart" style="height:300px"></div></div>
</div>
<script>
const DATA=[{data_pairs}];
const dateList=DATA.map(d=>d[0]),closeList=DATA.map(d=>d[1]);
const latest=closeList[closeList.length-1],first=closeList[0];
const totalChange=((latest-first)/first*100);
document.getElementById('stats').innerHTML=
 '<div class="stat-item"><div class="stat-label">最新收盘价</div><div class="stat-value '+(totalChange>=0?'up':'down')+'">¥'+latest.toFixed(2)+'</div></div>'+
 '<div class="stat-item"><div class="stat-label">区间涨跌</div><div class="stat-value '+(totalChange>=0?'up':'down')+'">'+(totalChange>=0?'+':'')+totalChange.toFixed(2)+'%</div></div>'+
 '<div class="stat-item"><div class="stat-label">最高价</div><div class="stat-value">¥'+Math.max(...closeList).toFixed(2)+'</div></div>'+
 '<div class="stat-item"><div class="stat-label">最低价</div><div class="stat-value">¥'+Math.min(...closeList).toFixed(2)+'</div></div>';
var c1=echarts.init(document.getElementById('chart'));
c1.setOption({{tooltip:{{trigger:'axis'}},grid:{{left:'8%',right:'4%',top:'5%',bottom:'5%'}},
 xAxis:{{type:'category',data:dateList,axisLabel:{{fontSize:11}}}},
 yAxis:{{type:'value',scale:true,axisLabel:{{formatter:'¥{{value}}'}}}},
 dataZoom:[{{type:'inside'}},{{type:'slider',bottom:5,height:22}}],
 series:[{{name:'收盘价',type:'line',data:closeList,lineStyle:{{color:'#1565c0',width:2}},itemStyle:{{color:'#1565c0'}},
 areaStyle:{{color:{{type:'linear',x:0,y:0,x2:0,y2:1,colorStops:[{{offset:0,color:'rgba(21,101,192,0.3)'}},{{offset:1,color:'rgba(21,101,192,0.02)'}}]}}}},
 markLine:{{silent:true,data:[{{yAxis:first,name:'起始价',lineStyle:{{color:'#999',type:'dashed'}}}}]}}}}]}});
var c2=echarts.init(document.getElementById('pctChart'));
c2.setOption({{tooltip:{{trigger:'axis'}},grid:{{left:'8%',right:'4%',top:'5%',bottom:'5%'}},
 xAxis:{{type:'category',data:dateList,axisLabel:{{fontSize:11}}}},
 yAxis:{{type:'value',axisLabel:{{formatter:'{{value}}%'}}}},
 dataZoom:[{{type:'inside'}},{{type:'slider',bottom:5,height:22}}],
 series:[{{name:'涨跌幅',type:'bar',data:[{pct_pairs}]}}]}});
window.addEventListener('resize',function(){{c1.resize();c2.resize()}});
</script></body></html>"""

chart_path = os.path.join(output_dir, f"{STOCK_NAME}_收盘价曲线.html")
with open(chart_path, "w", encoding="utf-8") as f:
    f.write(chart_html)
print(f"收盘价曲线: {chart_path}")

# ──────────── K线+成交量面板 HTML ────────────
kline = ", ".join(f"[{opens[i]:.2f},{closes[i]:.2f},{lows[i]:.2f},{highs[i]:.2f}]" for i in range(len(dates)))
vol_bars = ", ".join(f"{{value:{vols[i]:.0f},itemStyle:{{color:'{'#e53935' if closes[i]>=opens[i] else '#43a047'}'}}}}" for i in range(len(dates)))
dates_js = ", ".join(f"'{d}'" for d in dates)
opens_js = ", ".join(f"{o:.2f}" for o in opens)
closes_js = ", ".join(f"{c:.2f}" for c in closes)
highs_js = ", ".join(f"{h:.2f}" for h in highs)
lows_js = ", ".join(f"{l:.2f}" for l in lows)
pcts_js = ", ".join(f"{p:.2f}" for p in pcts)
amounts_js = ", ".join(f"{a:.0f}" for a in amounts)
vols_js = ", ".join(f"{v:.0f}" for v in vols)

dash_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{STOCK_NAME}(300750.SZ) K线图 & 成交量</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root{{--up:#e53935;--down:#43a047;--accent:#1565c0;--border:#e8e8e8}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f6fa;color:#1a1a2e;min-height:100vh}}
.header{{background:linear-gradient(135deg,#1a237e,#283593);color:#fff;padding:20px 30px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:15px}}
.header-left h1{{font-size:22px;font-weight:600;margin-bottom:4px}}
.header-left .code{{font-size:14px;opacity:0.85}}
.stats{{display:flex;gap:24px;flex-wrap:wrap}}
.stat-item{{text-align:center}}.stat-item .label{{font-size:12px;opacity:0.75}}.stat-item .value{{font-size:20px;font-weight:700}}
.container{{max-width:1400px;margin:0 auto;padding:20px}}
.card{{background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);margin-bottom:16px;overflow:hidden}}
.card-header{{padding:14px 20px;border-bottom:1px solid var(--border);font-size:15px;font-weight:600;display:flex;align-items:center;gap:8px}}
.card-header::before{{content:'';display:inline-block;width:4px;height:18px;background:var(--accent);border-radius:2px}}
.chart-box{{width:100%;height:500px}}.chart-box.vol{{height:280px}}
.legend-note{{display:flex;gap:16px;padding:8px 20px 16px;font-size:12px;color:#666}}
.legend-dot{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px;vertical-align:middle}}
.legend-dot.up{{background:var(--up)}}.legend-dot.down{{background:var(--down)}}
.tbl-wrapper{{overflow-x:auto;max-height:400px;overflow-y:auto}}
.tbl-wrapper table{{width:100%;border-collapse:collapse;font-size:13px}}
.tbl-wrapper th{{background:#f8f9fc;padding:10px 12px;text-align:center;font-weight:600;border-bottom:2px solid var(--border);position:sticky;top:0}}
.tbl-wrapper td{{padding:8px 12px;text-align:center;border-bottom:1px solid #f0f0f0}}
.tbl-wrapper tr:hover td{{background:#f5f7ff}}
.up{{color:var(--up);font-weight:600}}.down{{color:var(--down);font-weight:600}}
</style>
</head>
<body>
<div class="header">
<div class="header-left"><h1>{STOCK_NAME}</h1><div class="code">300750.SZ · 创业板 · 新能源电池</div></div>
<div class="stats" id="statsBar">
<div class="stat-item"><div class="label">最新价</div><div class="value" id="stP">--</div></div>
<div class="stat-item"><div class="label">涨跌幅</div><div class="value" id="stC">--</div></div>
<div class="stat-item"><div class="label">最高</div><div class="value" id="stH">--</div></div>
<div class="stat-item"><div class="label">最低</div><div class="value" id="stL">--</div></div>
<div class="stat-item"><div class="label">区间涨幅</div><div class="value" id="stR">--</div></div>
</div></div>
<div class="container">
<div class="card"><div class="card-header">K线图（日线）</div><div class="chart-box" id="kc"></div>
<div class="legend-note"><span><span class="legend-dot up"></span>上涨（阳线）</span><span><span class="legend-dot down"></span>下跌（阴线）</span></div></div>
<div class="card"><div class="card-header">成交量</div><div class="chart-box vol" id="vc"></div>
<div class="legend-note"><span><span class="legend-dot up"></span>收盘≥开盘</span><span><span class="legend-dot down"></span>收盘&lt;开盘</span></div></div>
<div class="card"><div class="card-header">数据明细</div><div class="tbl-wrapper"><table><thead><tr>
<th>日期</th><th>开盘</th><th>收盘</th><th>最高</th><th>最低</th><th>涨跌幅</th><th>成交量(手)</th><th>成交额(万)</th></tr></thead><tbody id="tb"></tbody></table></div></div>
</div>
<script>
var D=[{dates_js}],O=[{opens_js}],C=[{closes_js}],H=[{highs_js}],L=[{lows_js}],P=[{pcts_js}],A=[{amounts_js}],V=[{vols_js}];
var KL=[{kline}],VB=[{vol_bars}];
var n=D.length-1,lc=C[n],lp=P[n],tr=(lc-C[0])/C[0]*100;
function ss(id,v,c){{var e=document.getElementById(id);e.textContent=v;if(c)e.className='value '+c}}
ss('stP','¥'+lc.toFixed(2),lp>=0?'up':'down');ss('stC',(lp>=0?'+':'')+lp.toFixed(2)+'%',lp>=0?'up':'down');
ss('stH','¥'+Math.max.apply(null,H).toFixed(2));ss('stL','¥'+Math.min.apply(null,L).toFixed(2));
ss('stR',(tr>=0?'+':'')+tr.toFixed(2)+'%',tr>=0?'up':'down');
var tb='';for(var i=n;i>=0;i--){{ var cl=P[i]>=0?'up':'down',sg=P[i]>=0?'+':'';
tb+='<tr><td>'+D[i]+'</td><td>'+O[i].toFixed(2)+'</td><td class="'+cl+'">'+C[i].toFixed(2)+'</td><td>'+H[i].toFixed(2)+'</td><td>'+L[i].toFixed(2)+'</td><td class="'+cl+'">'+sg+P[i].toFixed(2)+'%</td><td>'+Math.round(V[i]/100)+'</td><td>'+Math.round(A[i]/10)+'</td></tr>'}}
document.getElementById('tb').innerHTML=tb;
function mc(id,o){{var c=echarts.init(document.getElementById(id));c.setOption(o);window.addEventListener('resize',function(){{c.resize()}})}}
mc('kc',{{tooltip:{{trigger:'axis',axisPointer:{{type:'cross'}}}},grid:{{left:'8%',right:'3%',top:'5%',bottom:'5%'}},
 xAxis:{{type:'category',data:D,axisLabel:{{fontSize:11}}}},
 yAxis:{{type:'value',scale:true}},
 dataZoom:[{{type:'inside',xAxisIndex:0}},{{type:'slider',xAxisIndex:0,bottom:5,height:22}}],
 series:[{{name:'K线',type:'candlestick',data:KL,itemStyle:{{color:'#e53935',color0:'#43a047',borderColor:'#e53935',borderColor0:'#43a047'}}}}]}});
mc('vc',{{tooltip:{{trigger:'axis',axisPointer:{{type:'shadow'}}}},grid:{{left:'8%',right:'3%',top:'5%',bottom:'5%'}},
 xAxis:{{type:'category',data:D,axisLabel:{{fontSize:11}}}},
 yAxis:{{type:'value',axisLabel:{{fontSize:11,formatter:function(v){{return (v/10000).toFixed(0)+'万'}}}}}},
 dataZoom:[{{type:'inside',xAxisIndex:0}},{{type:'slider',xAxisIndex:0,bottom:5,height:22}}],
 series:[{{name:'成交量',type:'bar',data:VB}}]}});
</script></body></html>"""

dash_path = os.path.join(output_dir, f"{STOCK_NAME}_K线面板.html")
with open(dash_path, "w", encoding="utf-8") as f:
    f.write(dash_html)
print(f"K线面板: {dash_path}")

print(f"\n=== 全部完成 ===")
print(f"  CSV: outputs/ningde_era_daily.csv")
print(f"  收盘价曲线: outputs/{STOCK_NAME}_收盘价曲线.html")
print(f"  K线面板: outputs/{STOCK_NAME}_K线面板.html")
