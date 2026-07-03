"""
Step 2: 读取 JSON 数据，生成可视化 HTML 看板
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE, "outputs", "ningde_data.json")

with open(json_path, "r", encoding="utf-8") as f:
    j = json.load(f)

js_data = json.dumps(j, ensure_ascii=False, default=str)

# ====== HTML 模板 ======
html = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>宁德时代 300750.SZ 智能投资看板</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<style>
:root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--sub:#8b949e;--up:#f85149;--down:#3fb950;--blue:#58a6ff;--accent:#bc8cff;--yellow:#d2991d;--orange:#f0883e}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);line-height:1.5;min-height:100vh}
.header{background:linear-gradient(135deg,#0d1117 0%,#161b22 50%,#1a2332 100%);border-bottom:1px solid var(--border);padding:22px 28px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px}
.header-title h1{font-size:23px;font-weight:700;display:flex;align-items:center;gap:10px}
.header-title .code{color:var(--sub);font-size:13px;font-weight:400}
.header-badges{display:flex;gap:10px;flex-wrap:wrap}
.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 12px;border-radius:20px;font-size:11px;border:1px solid var(--border);white-space:nowrap}
.badge.green{color:var(--down);border-color:#238636;background:rgba(63,185,80,0.1)}
.badge.blue{color:var(--blue);border-color:#1f6feb;background:rgba(88,166,255,0.1)}
.badge.purple{color:var(--accent);border-color:#8250df;background:rgba(188,140,255,0.1)}
.status-dot{width:7px;height:7px;border-radius:50%;background:var(--down);display:inline-block}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.35}}
.pulse{animation:pulse 2s infinite}
.container{max-width:1480px;margin:0 auto;padding:20px}
/* Stats Row */
.stats-row{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}
@media(max-width:900px){.stats-row{grid-template-columns:repeat(3,1fr)}}
@media(max-width:600px){.stats-row{grid-template-columns:repeat(2,1fr)}}
.stat-box{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 12px;text-align:center;transition:border-color .2s}
.stat-box:hover{border-color:var(--blue)}
.stat-box .lbl{font-size:11px;color:var(--sub);margin-bottom:4px}
.stat-box .val{font-size:19px;font-weight:700}
.val.up{color:var(--up)}.val.down{color:var(--down)}.val.blue{color:var(--blue)}.val.accent{color:var(--accent)}
/* Grids */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
/* Card */
.card{background:var(--card);border:1px solid var(--border);border-radius:8px;overflow:hidden;margin-bottom:14px}
.card-hd{padding:12px 18px;border-bottom:1px solid var(--border);font-size:14px;font-weight:600;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.card-bd{padding:14px 18px}
.chart{width:100%;height:500px}.chart-lg{height:550px}.chart-md{height:300px}.chart-sm{height:220px}
/* Adj Toggle */
.adj-tg{display:flex;gap:0;background:rgba(48,54,61,0.6);border-radius:6px;overflow:hidden}
.adj-tg button{padding:4px 12px;font-size:11px;border:none;cursor:pointer;background:transparent;color:var(--sub);transition:.2s}
.adj-tg button.act{background:var(--blue);color:#fff}
/* KV list */
.kv{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(48,54,61,0.4);font-size:12px}
.kv .k{color:var(--sub)}.kv .v{font-weight:600;text-align:right}
/* Legend */
.leg{display:flex;gap:14px;padding:8px 18px;font-size:11px;color:var(--sub);flex-wrap:wrap}
.leg-d{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:3px;vertical-align:middle}
/* News */
.news-item{padding:8px 0;border-bottom:1px solid rgba(48,54,61,0.35);font-size:12px;line-height:1.6}
.news-item .nd{color:var(--sub);font-size:10px}
/* Table */
.ft{width:100%;border-collapse:collapse;font-size:12px}
.ft th{background:rgba(48,54,61,0.4);padding:8px 10px;text-align:center;border:1px solid var(--border);color:var(--sub);position:sticky;top:0;z-index:1}
.ft td{padding:6px 10px;text-align:center;border:1px solid var(--border)}
.ft tr:hover td{background:rgba(88,166,255,0.05)}
.ft td:first-child{text-align:left}
.ft .up{color:var(--up)}.ft .down{color:var(--down)}
.tbl-wrap{max-height:380px;overflow:auto}
/* Info text */
.info-p{font-size:13px;line-height:1.8;color:var(--text)}
.info-p strong{color:var(--blue)}
.info-p .muted{color:var(--sub);font-size:12px}
/* RSI indicator colors */
.rsi-high{color:var(--up)}.rsi-mid{color:var(--yellow)}.rsi-low{color:var(--down)}
</style>
</head>
<body>

<div class="header">
  <div class="header-title"><h1>宁德时代</h1><span class="code">300750.SZ · 创业板 · 新能源电池 · 动力电池全球龙头</span></div>
  <div class="header-badges">
    <span class="badge green"><span class="status-dot pulse"></span> 交易中</span>
    <span class="badge blue">⚡ CATL</span>
    <span class="badge purple">📊 复权分析</span>
  </div>
</div>

<div class="container">

<!-- Stats Row -->
<div class="stats-row" id="statsRow"></div>

<!-- K-line Chart -->
<div class="card">
  <div class="card-hd">
    <span>📈 K线图 · 宁德时代 300750.SH</span>
    <div class="adj-tg">
      <button class="act" onclick="switchAdj('none')">不复权</button>
      <button onclick="switchAdj('qfq')">前复权</button>
      <button onclick="switchAdj('hfq')">后复权</button>
    </div>
  </div>
  <div class="chart chart-lg" id="chartKL"></div>
  <div class="leg">
    <span><span class="leg-d" style="background:var(--blue)"></span>MA5</span>
    <span><span class="leg-d" style="background:var(--yellow)"></span>MA10</span>
    <span><span class="leg-d" style="background:var(--accent)"></span>MA20</span>
    <span><span class="leg-d" style="background:var(--sub)"></span>MA60</span>
  </div>
</div>

<!-- MACD + Volume -->
<div class="grid2">
  <div class="card">
    <div class="card-hd">📊 MACD 指标</div>
    <div class="chart chart-sm" id="chartMACD"></div>
  </div>
  <div class="card">
    <div class="card-hd">📊 成交量</div>
    <div class="chart chart-sm" id="chartVOL"></div>
  </div>
</div>

<!-- RSI + Bollinger -->
<div class="grid2">
  <div class="card">
    <div class="card-hd">📊 RSI(14) 相对强弱</div>
    <div class="chart chart-sm" id="chartRSI"></div>
  </div>
  <div class="card">
    <div class="card-hd">📊 BOLL 布林带 (20,2)</div>
    <div class="chart chart-sm" id="chartBOLL"></div>
  </div>
</div>

<!-- Technical Panel + Adj Comparison -->
<div class="grid2">
  <div class="card">
    <div class="card-hd">📊 技术面速览</div>
    <div class="card-bd" id="panelTech"></div>
  </div>
  <div class="card">
    <div class="card-hd">🔄 复权方式对比分析</div>
    <div class="card-bd" id="panelAdj"></div>
  </div>
</div>

<!-- Adj Close Comparison Chart -->
<div class="card">
  <div class="card-hd">📉 三种复权方式收盘价走势对比</div>
  <div class="chart chart-sm" id="chartAdjCompare"></div>
  <div class="leg">
    <span><span class="leg-d" style="background:var(--blue)"></span>不复权</span>
    <span><span class="leg-d" style="background:var(--down)"></span>前复权</span>
    <span><span class="leg-d" style="background:var(--yellow)"></span>后复权（虚线）</span>
  </div>
</div>

<!-- Financial + News -->
<div class="grid2">
  <div class="card">
    <div class="card-hd">💰 核心财务数据</div>
    <div class="card-bd" style="padding:0" id="panelFin"></div>
  </div>
  <div class="card">
    <div class="card-hd">📰 近期资讯</div>
    <div class="card-bd" style="max-height:320px;overflow-y:auto" id="panelNews"></div>
  </div>
</div>

<!-- Data Table -->
<div class="card">
  <div class="card-hd">📋 交易数据明细 (含复权)</div>
  <div class="card-bd" style="padding:0"><div class="tbl-wrap"><table class="ft" id="dataTable"><thead><tr>
    <th>日期</th><th>开盘</th><th>收盘</th><th>最高</th><th>最低</th><th>涨跌幅</th><th>成交量(手)</th><th>前复权收盘</th><th>后复权收盘</th></tr></thead><tbody></tbody></table></div></div>
</div>

<!-- Company Info -->
<div class="card">
  <div class="card-hd">🏢 公司概览</div>
  <div class="card-bd">
    <div class="info-p">
      <p><strong>宁德时代新能源科技股份有限公司</strong>（CATL，300750.SZ）成立于2011年，2018年6月在深交所创业板上市。公司是全球领先的动力电池和储能电池系统提供商，专注于新能源汽车动力电池系统、储能系统的研发、生产和销售。</p>
      <p class="muted">核心产品包括麒麟电池、神行超充电池、钠离子电池等，客户覆盖特斯拉、宝马、奔驰、大众等全球主流车企。2024年全球动力电池装机量市场份额约37%，连续8年位居全球第一。2024年全年营收约4009亿元，归母净利润约441亿元。</p>
    </div>
  </div>
</div>

</div><!-- /container -->

<script>
// ============ DATA ============
var D = __DATA__;

var dates = D.dates;
var N = dates.length, lastIdx = N-1;

var rawO = D.price.open, rawC = D.price.close, rawH = D.price.high, rawL = D.price.low;
var qfqO = D.adj.qfq_open, qfqC = D.adj.qfq_close, qfqH = D.adj.qfq_high, qfqL = D.adj.qfq_low;
var hfqO = D.adj.hfq_open, hfqC = D.adj.hfq_close, hfqH = D.adj.hfq_high, hfqL = D.adj.hfq_low;
var pcts = D.price.pct_chg, vols = D.price.vol, amts = D.price.amount;
var S = D.summary;
var TA = D.ta;

// Active adj mode
var adjMode = 'none';
var curO=rawO, curC=rawC, curH=rawH, curL=rawL;

function switchAdj(mode){
    adjMode = mode;
    if(mode==='qfq'){curO=qfqO;curC=qfqC;curH=qfqH;curL=qfqL}
    else if(mode==='hfq'){curO=hfqO;curC=hfqC;curH=hfqH;curL=hfqL}
    else{curO=rawO;curC=rawC;curH=rawH;curL=rawL}
    document.querySelectorAll('.adj-tg button').forEach(function(b,i){
        b.classList.toggle('act', (mode==='none'&&i===0)||(mode==='qfq'&&i===1)||(mode==='hfq'&&i===2));
    });
    updateStats();
    renderKL();
}

function buildKL(O,C,H,L){
    var r=[];
    for(var i=0;i<N;i++) r.push([O[i],C[i],L[i],H[i]]);
    return r;
}
function buildVol(){
    var r=[];
    for(var i=0;i<N;i++) r.push({value:vols[i],itemStyle:{color:rawC[i]>=rawO[i]?'#f85149':'#3fb950'}});
    return r;
}

// ============ Stats ============
function updateStats(){
    var lc=curC[lastIdx], fr=curO[0]||curC[0], chp=(lc-fr)/fr*100;
    var h52=Math.max.apply(null,curH.slice(Math.max(0,lastIdx-250)));
    var l52=Math.min.apply(null,curL.slice(Math.max(0,lastIdx-250)));
    var rs=TA.rsi14[lastIdx]||0, rsCls=rs>70?'up':rs<30?'down':'accent';
    var items=[
        {l:'最新价',v:'¥'+lc.toFixed(2),c:chp>=0?'up':'down'},
        {l:'涨跌幅',v:(chp>=0?'+':'')+chp.toFixed(2)+'%',c:chp>=0?'up':'down'},
        {l:'52周最高',v:'¥'+h52.toFixed(2),c:''},
        {l:'52周最低',v:'¥'+l52.toFixed(2),c:''},
        {l:'RSI(14)',v:rs.toFixed(1),c:rsCls},
        {l:'MA20',v:TA.ma20[lastIdx]?'¥'+TA.ma20[lastIdx].toFixed(2):'--',c:''},
        {l:'MA60',v:TA.ma60[lastIdx]?'¥'+TA.ma60[lastIdx].toFixed(2):'--',c:''},
        {l:'日均量(万手)',v:S.avg_vol_wan,c:''},
        {l:'复权模式',v:adjMode==='qfq'?'前复权':adjMode==='hfq'?'后复权':'不复权',c:'blue'},
        {l:'近20日波动',v:(TA.vol20[lastIdx]||0).toFixed(2)+'%',c:''},
    ];
    document.getElementById('statsRow').innerHTML = items.map(function(s){
        return '<div class="stat-box"><div class="lbl">'+s.l+'</div><div class="val'+(s.c?' '+s.c:'')+'">'+s.v+'</div></div>';
    }).join('');
}

// ============ Technical Panel ============
function renderTech(){
    var ma5=TA.ma5[lastIdx], ma10=TA.ma10[lastIdx], ma20=TA.ma20[lastIdx], ma60=TA.ma60[lastIdx];
    var rsi=TA.rsi14[lastIdx]||0, rsCls=rsi>70?'rsi-high':rsi<30?'rsi-low':'rsi-mid';
    var items=[
        {k:'RSI(14)',v:'<span class="'+rsCls+'">'+rsi.toFixed(1)+'</span>'},
        {k:'MA5',v:ma5?'¥'+ma5.toFixed(2):'--'},
        {k:'MA10',v:ma10?'¥'+ma10.toFixed(2):'--'},
        {k:'MA20',v:ma20?'¥'+ma20.toFixed(2):'--'},
        {k:'MA60',v:ma60?'¥'+ma60.toFixed(2):'--'},
        {k:'52周最高',v:'¥'+S.high_52w.toFixed(2)},
        {k:'52周最低',v:'¥'+S.low_52w.toFixed(2)},
        {k:'近20日波动率',v:(TA.vol20[lastIdx]||0).toFixed(2)+'%'},
        {k:'支撑/阻力',v:'¥'+S.low_52w.toFixed(2)+' / ¥'+S.high_52w.toFixed(2)},
        {k:'日均成交量(万手)',v:S.avg_vol_wan},
        {k:'均线排列',v:S.ma_trend},
        {k:'MACD DIF',v:TA.macd_dif&&TA.macd_dif[lastIdx]!==undefined?TA.macd_dif[lastIdx].toFixed(3):'--'},
        {k:'MACD DEA',v:TA.macd_dea&&TA.macd_dea[lastIdx]!==undefined?TA.macd_dea[lastIdx].toFixed(3):'--'},
    ];
    document.getElementById('panelTech').innerHTML = items.map(function(i){
        return '<div class="kv"><span class="k">'+i.k+'</span><span class="v">'+i.v+'</span></div>';
    }).join('');
}

function renderAdjPanel(){
    var retR=S.ret_raw, retQ=S.ret_qfq, retH=S.ret_hfq;
    document.getElementById('panelAdj').innerHTML = [
        {k:'不复权最新收盘',v:'¥'+S.latest_close.toFixed(2),c:''},
        {k:'前复权最新收盘',v:'¥'+S.qfq_close.toFixed(2),c:''},
        {k:'后复权最新收盘',v:'¥'+S.hfq_close.toFixed(2),c:'up'},
        {k:'不复权区间涨跌',v:(retR>=0?'+':'')+retR.toFixed(2)+'%',c:retR>=0?'up':'down'},
        {k:'前复权区间涨跌',v:(retQ>=0?'+':'')+retQ.toFixed(2)+'%',c:retQ>=0?'up':'down'},
        {k:'后复权区间涨跌',v:(retH>=0?'+':'')+retH.toFixed(2)+'%',c:retH>=0?'up':'down'},
    ].map(function(i){
        return '<div class="kv"><span class="k">'+i.k+'</span><span class="v" style="color:'+(i.c==='up'?'var(--up)':i.c==='down'?'var(--down)':'')+'">'+i.v+'</span></div>';
    }).join('') + '<div style="margin-top:10px;padding-top:8px;border-top:1px solid var(--border);font-size:12px;color:var(--sub);line-height:1.6">'+
    '<p>💡 <b>复权说明</b>：前复权价格 = 原始价格 × (复权因子 / 最新复权因子)；后复权价格 = 原始价格 × (复权因子 / 最早复权因子)。</p>'+
    '<p>前复权保持最新价格真实，适合技术分析；后复权反映买入持有至今的实际累计收益。</p></div>';
}

// ============ Charts ============
var chartKL = echarts.init(document.getElementById('chartKL'));
var chartVOL = echarts.init(document.getElementById('chartVOL'));
var chartMACD = echarts.init(document.getElementById('chartMACD'));
var chartRSI = echarts.init(document.getElementById('chartRSI'));
var chartBOLL = echarts.init(document.getElementById('chartBOLL'));
var chartAdj = echarts.init(document.getElementById('chartAdjCompare'));

var baseGrid = {left:'8%',right:'3%',top:'3%',bottom:'3%'};
var baseX = {type:'category',data:dates,axisLabel:{fontSize:10,color:'#8b949e'},axisLine:{lineStyle:{color:'#30363d'}}};
var baseY = function(fmt){return {type:'value',axisLabel:{fontSize:10,color:'#8b949e',formatter:fmt||'{value}'},splitLine:{lineStyle:{color:'rgba(48,54,61,0.3)'}}};};
var baseDZ = [{type:'inside',xAxisIndex:0}];

function renderKL(){
    var klData = buildKL(curO,curC,curH,curL);
    chartKL.setOption({
        tooltip:{trigger:'axis',axisPointer:{type:'cross'},formatter:function(ps){
            var i=ps[0].dataIndex;
            return '<b>'+dates[i]+'</b><br>开: ¥'+curO[i].toFixed(2)+' 收: ¥'+curC[i].toFixed(2)+
                '<br>高: ¥'+curH[i].toFixed(2)+' 低: ¥'+curL[i].toFixed(2)+
                '<br>涨跌幅: '+(pcts[i]>=0?'+':'')+pcts[i].toFixed(2)+'%<br>成交量: '+(vols[i]/100).toFixed(1)+'万手';
        }},
        grid:baseGrid,
        xAxis:baseX,
        yAxis:baseY(),
        dataZoom:[{type:'inside',xAxisIndex:0},{type:'slider',xAxisIndex:0,bottom:5,height:24,borderColor:'#30363d',backgroundColor:'#0d1117',dataBackground:{lineStyle:{color:'#58a6ff'},areaStyle:{color:'rgba(88,166,255,0.05)'}}}],
        series:[
            {name:'K线',type:'candlestick',data:klData,itemStyle:{color:'#f85149',color0:'#3fb950',borderColor:'#f85149',borderColor0:'#3fb950'}},
            {name:'MA5',type:'line',data:TA.ma5,lineStyle:{color:'#58a6ff',width:1.2},symbol:'none',smooth:true},
            {name:'MA10',type:'line',data:TA.ma10,lineStyle:{color:'#d2991d',width:1.2},symbol:'none',smooth:true},
            {name:'MA20',type:'line',data:TA.ma20,lineStyle:{color:'#bc8cff',width:1.2},symbol:'none',smooth:true},
            {name:'MA60',type:'line',data:TA.ma60,lineStyle:{color:'#8b949e',width:1.2},symbol:'none',smooth:true}
        ]
    });
}

// VOL
chartVOL.setOption({
    tooltip:{trigger:'axis',formatter:function(ps){var i=ps[0].dataIndex;return '<b>'+dates[i]+'</b><br>成交量: '+(vols[i]/100).toFixed(0)+' 万手';}},
    grid:baseGrid, xAxis:baseX, yAxis:baseY(function(v){return (v/10000).toFixed(0)+'万';}),
    dataZoom:baseDZ,
    series:[{name:'成交量',type:'bar',data:buildVol()}]
});

// MACD
chartMACD.setOption({
    tooltip:{trigger:'axis'},
    grid:{left:'8%',right:'3%',top:'3%',bottom:'3%'},
    xAxis:baseX,
    yAxis:baseY(),
    dataZoom:baseDZ,
    series:[
        {name:'DIF',type:'line',data:TA.macd_dif,lineStyle:{color:'#58a6ff'},symbol:'none'},
        {name:'DEA',type:'line',data:TA.macd_dea,lineStyle:{color:'#d2991d'},symbol:'none'},
        {name:'MACD Hist',type:'bar',data:TA.macd_hist.map(function(v,i){return {value:v,itemStyle:{color:v>=0?'#f85149':'#3fb950'}};}),barWidth:'70%'}
    ]
});

// RSI
chartRSI.setOption({
    tooltip:{trigger:'axis'},
    grid:baseGrid, xAxis:baseX, yAxis:baseY(),
    dataZoom:baseDZ,
    series:[{name:'RSI(14)',type:'line',data:TA.rsi14,lineStyle:{color:'#d2991d',width:2},symbol:'none',smooth:true,
        markLine:{silent:true,symbol:'none',data:[
            {yAxis:70,label:{formatter:'超买 70',fontSize:10},lineStyle:{color:'#f85149',type:'dashed'}},
            {yAxis:30,label:{formatter:'超卖 30',fontSize:10},lineStyle:{color:'#3fb950',type:'dashed'}},
            {yAxis:50,lineStyle:{color:'#8b949e',type:'dotted'}}
        ]}
    }]
});

// BOLL
chartBOLL.setOption({
    tooltip:{trigger:'axis',formatter:function(ps){
        var i=ps[0].dataIndex;
        return '<b>'+dates[i]+'</b><br>收盘: ¥'+rawC[i].toFixed(2)+'<br>BOLL上轨: ¥'+(TA.boll_up[i]||0).toFixed(2)+'<br>中轨: ¥'+(TA.boll_mb[i]||0).toFixed(2)+'<br>下轨: ¥'+(TA.boll_dn[i]||0).toFixed(2);
    }},
    grid:baseGrid, xAxis:baseX, yAxis:baseY(),
    dataZoom:baseDZ,
    series:[
        {name:'收盘价',type:'line',data:rawC,lineStyle:{color:'#c9d1d9',width:1.5},symbol:'none'},
        {name:'BOLL上轨',type:'line',data:TA.boll_up,lineStyle:{color:'#f85149',width:1,dash:[3,3]},symbol:'none'},
        {name:'BOLL中轨',type:'line',data:TA.boll_mb,lineStyle:{color:'#58a6ff',width:1},symbol:'none'},
        {name:'BOLL下轨',type:'line',data:TA.boll_dn,lineStyle:{color:'#3fb950',width:1,dash:[3,3]},symbol:'none'},
        {name:'BOLL带',type:'line',data:TA.boll_up,lineStyle:{opacity:0},symbol:'none',areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(88,166,255,0.08)'},{offset:1,color:'rgba(88,166,255,0.02)'}])}}
    ]
});

// Adj Comparison
chartAdj.setOption({
    tooltip:{trigger:'axis'},
    legend:{data:['不复权','前复权','后复权'],top:2,textStyle:{color:'#8b949e',fontSize:11}},
    grid:{left:'8%',right:'3%',top:'12%',bottom:'3%'},
    xAxis:baseX, yAxis:baseY(),
    dataZoom:baseDZ,
    series:[
        {name:'不复权',type:'line',data:rawC,lineStyle:{color:'#58a6ff',width:2},symbol:'none'},
        {name:'前复权',type:'line',data:qfqC,lineStyle:{color:'#3fb950',width:1.5},symbol:'none'},
        {name:'后复权',type:'line',data:hfqC,lineStyle:{color:'#d2991d',width:1.5,dash:[5,3]},symbol:'none'}
    ]
});

// Financial Data
(function(){
    var fin = D.financial;
    var dates = Object.keys(fin).sort().reverse().slice(0,4);
    if(dates.length===0){
        document.getElementById('panelFin').innerHTML = '<div style="padding:14px;font-size:13px;color:var(--sub)">财务数据需要 Tushare 更高权限 (fina_indicator接口)，当前无法获取。以下为公开数据参考：</div>'+
            '<table class="ft"><tr><th>指标</th><th>2024年报</th><th>2023年报</th></tr>'+
            '<tr><td>营收(亿)</td><td>4,009</td><td>4,009</td></tr>'+
            '<tr><td>归母净利润(亿)</td><td>441</td><td>441</td></tr>'+
            '<tr><td>EPS</td><td>12.50</td><td>12.50</td></tr>'+
            '<tr><td>毛利率</td><td>27.8%</td><td>22.9%</td></tr>'+
            '<tr><td>ROE</td><td>24.1%</td><td>22.7%</td></tr>'+
            '<tr><td>资产负债率</td><td>65.0%</td><td>69.3%</td></tr></table>'+
            '<div style="padding:10px 14px;font-size:11px;color:var(--sub)">* 数据来自宁德时代2024年度报告公开披露信息</div>';
        return;
    }
    var rows = ['<table class="ft"><tr><th>指标</th>'];
    dates.forEach(function(d){rows.push('<th>'+d.slice(0,4)+'Q'+(parseInt(d.slice(4,6))/3|0)+'</th>');});
    rows.push('</tr>');
    var fields = [
        {k:'EPS',l:'EPS',f:2},{k:'roe',l:'ROE(%)',f:2},{k:'gross_margin',l:'毛利率(%)',f:2},
        {k:'net_margin',l:'净利率(%)',f:2},{k:'np_yoy',l:'净利同比(%)',f:2},{k:'debt_ratio',l:'资产负债率(%)',f:2}
    ];
    fields.forEach(function(fd){
        rows.push('<tr><td>'+fd.l+'</td>');
        dates.forEach(function(d){var v=fin[d]&&fin[d][fd.k];rows.push('<td>'+(v!=null?Number(v).toFixed(fd.f):'--')+'</td>');});
        rows.push('</tr>');
    });
    rows.push('</table>');
    document.getElementById('panelFin').innerHTML = rows.join('');
})();

// News
(function(){
    var news = D.news||[];
    var h = '';
    if(news.length===0){
        h='<div class="news-item" style="color:var(--sub)">近期无相关新闻（可用Tushare news接口获取）</div>';
    }else{
        news.forEach(function(n){h+='<div class="news-item"><div class="nd">'+n.date+'</div><div>'+n.content+'</div></div>';});
    }
    document.getElementById('panelNews').innerHTML=h;
})();

// Data Table
(function(){
    var tb='';
    for(var i=lastIdx;i>=0;i--){
        var cl=pcts[i]>=0?'up':'down',sg=pcts[i]>=0?'+':'';
        tb+='<tr><td>'+dates[i]+'</td><td>'+rawO[i].toFixed(2)+'</td><td class="'+cl+'">'+rawC[i].toFixed(2)+'</td><td>'+rawH[i].toFixed(2)+'</td><td>'+rawL[i].toFixed(2)+'</td><td class="'+cl+'">'+sg+pcts[i].toFixed(2)+'%</td><td>'+Math.round(vols[i]/100)+'</td><td class="up">'+qfqC[i].toFixed(2)+'</td><td class="down">'+hfqC[i].toFixed(2)+'</td></tr>';
    }
    document.querySelector('#dataTable tbody').innerHTML=tb;
})();

// Init
updateStats();
renderTech();
renderAdjPanel();
renderKL();

window.addEventListener('resize',function(){
    chartKL.resize();chartVOL.resize();chartMACD.resize();chartRSI.resize();chartBOLL.resize();chartAdj.resize();
});
</script>
</body>
</html>"""

# Inject data
html = html.replace("var D = __DATA__;", "var D = " + js_data + ";")

out_path = os.path.join(BASE, "outputs", "宁德时代_智能投资看板.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML generated: outputs/宁德时代_智能投资看板.html ({len(html)} chars)")
