# -*- coding: utf-8 -*-
import urllib.request
import urllib.parse
import json
import os
import re
import time
from datetime import datetime, timedelta

SENDKEY = os.environ.get('SERVERCHAN_SENDKEY', 'SCT328691TqGJDJfpEgA5noR3meGMVrKJ7')

def http_get(url, headers=None, timeout=15):
    try:
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except:
        return None

def get_yahoo(symbol):
    """Yahoo Finance - 美股/港股/外汇/债券是实时的"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?interval=1d&range=2d"
    txt = http_get(url)
    if not txt: return None
    try:
        data = json.loads(txt)
        result = data.get('chart', {}).get('result', [{}])[0]
        meta = result.get('meta', {})
        price = meta.get('regularMarketPrice')
        prev = meta.get('previousClose')
        if not price: return None
        pct = ((price - prev) / prev * 100) if prev and prev > 0 else 0
        
        # 获取数据时间戳
        timestamp = result.get('timestamp', [])
        if timestamp:
            last_ts = timestamp[-1]
            data_time = datetime.fromtimestamp(last_ts).strftime("%m/%d %H:%M")
        else:
            data_time = datetime.now().strftime("%m/%d %H:%M")
        
        return {'price': round(price, 2), 'pct': round(pct, 2), 'time': data_time}
    except: return None

def get_yahoo_commodity(symbol):
    """Yahoo Finance 商品期货 - 显示交易时段"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?interval=1d&range=2d"
    txt = http_get(url)
    if not txt: return None
    try:
        data = json.loads(txt)
        result = data.get('chart', {}).get('result', [{}])[0]
        meta = result.get('meta', {})
        price = meta.get('regularMarketPrice')
        prev = meta.get('previousClose')
        if not price: return None
        pct = ((price - prev) / prev * 100) if prev and prev > 0 else 0
        
        # 商品期货交易时间
        now = datetime.now()
        hour = now.hour
        if 0 <= hour < 6:
            # 凌晨时段，显示前一天收盘
            data_time = "前日收盘"
        elif 6 <= hour < 9:
            # 早盘前
            data_time = "电子盘"
        elif 9 <= hour < 15:
            # 日间交易
            data_time = now.strftime("%m/%d %H:%M")
        elif 15 <= hour < 18:
            # 下午，可能已收盘
            data_time = now.strftime("%m/%d %H:%M")
        else:
            # 晚间交易
            data_time = now.strftime("%m/%d %H:%M")
        
        return {'price': round(price, 2), 'pct': round(pct, 2), 'time': data_time}
    except: return None

def get_em(secid):
    """东方财富 A股 - 15:00收盘，之后显示收盘价"""
    txt = http_get('https://push2.eastmoney.com/api/qt/stock/get?secid=' + secid + '&fields=f43,f170')
    if not txt: return None
    try:
        d = json.loads(txt).get('data', {})
        
        # A股交易时间判断
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # A股交易时段: 9:30-11:30, 13:00-15:00
        if hour < 9 or (hour == 9 and minute < 30):
            # 开盘前，显示昨收
            data_time = "昨收"
        elif (hour == 9 and minute >= 30) or (hour == 10) or (hour == 11 and minute <= 30):
            # 早盘
            data_time = now.strftime("%m/%d %H:%M")
        elif hour == 12 or (hour == 11 and minute > 30):
            # 午休
            data_time = "早盘收盘"
        elif hour == 13 or (hour == 14):
            # 午盘
            data_time = now.strftime("%m/%d %H:%M")
        elif hour == 15 and minute == 0:
            # 刚收盘
            data_time = "15:00收盘"
        elif hour >= 15:
            # 收盘后
            data_time = "收盘"
        else:
            data_time = now.strftime("%m/%d %H:%M")
        
        return {'price': round(d.get('f43', 0) / 100, 2), 'pct': round((d.get('f170') or 0) / 100, 2), 'time': data_time}
    except: return None

def format_time(time_str):
    try:
        for fmt in ['%a, %d %b %Y %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d %b %Y %H:%M:%S']:
            try:
                dt = datetime.strptime(time_str[:25], fmt)
                return dt.strftime('%m/%d %H:%M')
            except: pass
    except: pass
    return ''

def fetch_news():
    sources = [
        ('https://feeds.reuters.com/reuters/businessNews', 'Reuters'),
        ('https://feeds.bbci.co.uk/news/business/rss.xml', 'BBC'),
        ('https://feeds.bloomberg.com/markets/news.rss', 'Bloomberg'),
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
        ('https://feeds.a.dj.com/rss/RSSMarketsMain.xml', 'WSJ'),
    ]
    all_news, seen = [], set()
    for url, src in sources:
        txt = http_get(url)
        if not txt: continue
        items = re.findall(r'<item>(.*?)</item>', txt, re.DOTALL)
        for item in items[:5]:
            title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            if not title_m: continue
            title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_m.group(1), flags=re.DOTALL)
            title = re.sub(r'<[^>]+>', '', title).strip()
            if len(title) < 20: continue
            key = title[:40].lower()
            if key in seen: continue
            seen.add(key)
            desc_m = re.search(r'<description>(.*?)</description>', item, re.DOTALL)
            desc = ''
            if desc_m:
                desc = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', desc_m.group(1), flags=re.DOTALL)
                desc = re.sub(r'<[^>]+>', '', desc).strip()
                if len(desc) > 200: desc = desc[:197] + '...'
            time_m = re.search(r'<pubDate>(.*?)</pubDate>', item, re.DOTALL)
            pub_time = format_time(time_m.group(1).strip()) if time_m else ''
            all_news.append({'title': title, 'desc': desc, 'source': src, 'time': pub_time})
        time.sleep(0.3)
    return all_news

def main():
    now = datetime.now()
    ts = now.strftime("%H:%M")
    ds = now.strftime("%Y年%m月%d日")
    wk = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()]
    fn = now.strftime("%Y-%m-%d-%H-00")
    ago = now - timedelta(hours=8)
    ts8 = ago.strftime("%H:%M")

    print("=" * 50)
    print("财经新闻汇总", ds, ts)

    print("\n[1/4] 获取新闻...")
    news = fetch_news()
    print("  共", len(news), "条")

    print("\n[2/4] 获取市场数据...")
    market = {}
    
    # 美股（实时）
    for sym, name in [('^DJI', '道琼斯'), ('^NDX', '纳斯达克100'), ('^GSPC', '标普500')]:
        r = get_yahoo(sym)
        if r: market[name] = r
        time.sleep(0.2)
    for sym, name in [('AAPL', '苹果'), ('MSFT', '微软'), ('GOOGL', '谷歌'), ('AMZN', '亚马逊'), 
                       ('NVDA', '英伟达'), ('TSLA', '特斯拉'), ('META', 'Meta'), ('JPM', '摩根大通')]:
        r = get_yahoo(sym)
        if r: market[name] = r
        time.sleep(0.2)
    
    # A股（收盘）
    for secid, name in [('1.000001', '上证指数'), ('1.000300', '沪深300'), ('0.399001', '深证成指'), ('0.399006', '创业板指')]:
        r = get_em(secid)
        if r: market[name] = r
    for secid, name in [('1.600519', '贵州茅台'), ('1.601318', '中国平安'), ('1.000858', '五粮液'), 
                        ('1.600036', '招商银行'), ('1.000333', '美的集团'), ('1.002594', '比亚迪')]:
        r = get_em(secid)
        if r: market[name] = r
    
    # 港股（实时，但16:00收盘）
    for sym, name in [('^HSI', '恒生指数'), ('^HSCE', '国企指数')]:
        r = get_yahoo(sym)
        if r: market[name] = r
        time.sleep(0.2)
    
    # 黄金/贵金属（商品期货）
    for sym, name in [('GC=F', 'COMEX黄金'), ('SI=F', 'COMEX白银'), ('HG=F', 'LME铜')]:
        r = get_yahoo_commodity(sym)
        if r: market[name] = r
        time.sleep(0.2)
    
    # 原油（商品期货）
    for sym, name in [('CL=F', 'WTI原油'), ('BZ=F', '布伦特原油')]:
        r = get_yahoo_commodity(sym)
        if r: market[name] = r
        time.sleep(0.2)
    
    # 外汇（24小时）
    for sym, name in [('DX-Y.NYB', '美元指数'), ('CNY=X', '美元/人民币'), ('EURUSD=X', '欧元/美元'), 
                       ('GBPUSD=X', '英镑/美元'), ('USDJPY=X', '美元/日元')]:
        r = get_yahoo(sym)
        if r: market[name] = r
        time.sleep(0.2)
    
    # 债券（实时）
    for sym, name in [('^TNX', '美国10年期国债'), ('^FVX', '美国5年期国债'), ('^TYX', '美国30年期国债')]:
        r = get_yahoo(sym)
        if r: market[name] = r
        time.sleep(0.2)
    
    print("\n  共", len(market), "项")

    print("\n[3/4] 生成报告...")
    
    lines = [
        "## 📰 财经新闻汇总\n",
        "**日期**: " + ds + "（" + wk + "）\n",
        "**时段**: " + ts8 + "-" + ts + "（过去8小时）\n",
        "**编制**: 羊咩咩 🐏\n\n",
        "---\n\n",
        "## 一、重大事件\n\n"
    ]

    for i, n in enumerate(news[:15], 1):
        time_str = " " + n['time'] if n['time'] else ""
        lines.append("**" + str(i) + ". " + n['title'] + "**\n")
        if n['desc']:
            lines.append("   " + n['desc'] + "\n")
        lines.append("   — " + n['source'] + time_str + "\n\n")

    lines.append("\n---\n\n## 二、市场摘要\n\n")
    
    # ----- 美股 -----
    us_time = market.get('道琼斯', {}).get('time', ts)
    lines.append("### 📈 美股市场\n")
    lines.append("*采集时间: " + us_time + " | 数据源: Yahoo Finance*\n\n")
    if '道琼斯' in market or '纳斯达克100' in market or '标普500' in market:
        idx_str = []
        for name in ['道琼斯', '纳斯达克100', '标普500']:
            if name in market:
                d = market[name]
                pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
                idx_str.append(name + ": " + str(d['price']) + " (" + pct + ")")
        lines.append("**指数**: " + " | ".join(idx_str) + "\n\n")
    
    tech = ['苹果', '微软', '谷歌', '亚马逊', '英伟达', '特斯拉', 'Meta']
    tech_str = []
    for name in tech:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            tech_str.append(name + ": $" + str(d['price']) + " (" + pct + ")")
    if tech_str:
        lines.append("**科技股**: " + " | ".join(tech_str) + "\n\n")
    
    fin = ['摩根大通']
    fin_str = []
    for name in fin:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            fin_str.append(name + ": $" + str(d['price']) + " (" + pct + ")")
    if fin_str:
        lines.append("**金融股**: " + " | ".join(fin_str) + "\n\n")
    
    # ----- A股 -----
    cn_time = market.get('上证指数', {}).get('time', '收盘')
    lines.append("### 📈 A股市场\n")
    lines.append("*采集时间: " + cn_time + " | 数据源: 东方财富*\n\n")
    if '上证指数' in market or '沪深300' in market:
        idx_str = []
        for name in ['上证指数', '深证成指', '沪深300', '创业板指']:
            if name in market:
                d = market[name]
                pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
                idx_str.append(name + ": " + str(d['price']) + " (" + pct + ")")
        lines.append("**指数**: " + " | ".join(idx_str) + "\n\n")
    
    weights = ['贵州茅台', '中国平安', '五粮液', '招商银行', '美的集团', '比亚迪']
    weight_str = []
    for name in weights:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            weight_str.append(name + ": " + str(d['price']) + "元 (" + pct + ")")
    if weight_str:
        lines.append("**权重股**: " + " | ".join(weight_str) + "\n\n")
    
    # ----- 港股 -----
    hk_time = market.get('恒生指数', {}).get('time', ts)
    lines.append("### 📈 港股市场\n")
    lines.append("*采集时间: " + hk_time + " | 数据源: Yahoo Finance*\n\n")
    if '恒生指数' in market:
        idx_str = []
        for name in ['恒生指数', '国企指数']:
            if name in market:
                d = market[name]
                pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
                idx_str.append(name + ": " + str(d['price']) + " (" + pct + ")")
        lines.append("**指数**: " + " | ".join(idx_str) + "\n\n")
    
    # ----- 黄金/贵金属 -----
    metal_time = market.get('COMEX黄金', {}).get('time', ts)
    lines.append("### 🥇 黄金/贵金属\n")
    lines.append("*采集时间: " + metal_time + " | 数据源: Yahoo Finance*\n\n")
    metal_str = []
    for name in ['COMEX黄金', 'COMEX白银', 'LME铜']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            if '黄金' in name or '白银' in name:
                metal_str.append(name + ": $" + str(d['price']) + "/盎司 (" + pct + ")")
            else:
                metal_str.append(name + ": $" + str(d['price']) + "/磅 (" + pct + ")")
    if metal_str:
        lines.append(" | ".join(metal_str) + "\n\n")
    else:
        lines.append("（暂不可用）\n\n")
    
    # ----- 原油 -----
    oil_time = market.get('WTI原油', {}).get('time', ts)
    lines.append("### 🛢️ 原油市场\n")
    lines.append("*采集时间: " + oil_time + " | 数据源: Yahoo Finance*\n\n")
    oil_str = []
    for name in ['WTI原油', '布伦特原油']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            oil_str.append(name + ": $" + str(d['price']) + "/桶 (" + pct + ")")
    if oil_str:
        lines.append(" | ".join(oil_str) + "\n\n")
    else:
        lines.append("（暂不可用）\n\n")
    
    # ----- 外汇 -----
    fx_time = market.get('美元指数', {}).get('time', ts)
    lines.append("### 💱 外汇市场\n")
    lines.append("*采集时间: " + fx_time + " | 数据源: Yahoo Finance*\n\n")
    fx_str = []
    for name in ['美元指数', '美元/人民币', '欧元/美元', '英镑/美元', '美元/日元']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            fx_str.append(name + ": " + str(d['price']) + " (" + pct + ")")
    if fx_str:
        lines.append(" | ".join(fx_str) + "\n\n")
    else:
        lines.append("（暂不可用）\n\n")
    
    # ----- 债券 -----
    bond_time = market.get('美国10年期国债', {}).get('time', ts)
    lines.append("### 📊 债券市场（收益率）\n")
    lines.append("*采集时间: " + bond_time + " | 数据源: Yahoo Finance*\n\n")
    bond_str = []
    for name in ['美国10年期国债', '美国5年期国债', '美国30年期国债']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            bond_str.append(name + ": " + str(d['price']) + "% (" + pct + ")")
    if bond_str:
        lines.append(" | ".join(bond_str) + "\n\n")
    else:
        lines.append("（暂不可用）\n\n")

    lines.append("---\n")
    lines.append("\n*数据截至北京时间 " + ts + " | 投资有风险，入市需谨慎*\n")

    desp = ''.join(lines)
    title = "财经新闻汇总 " + ts

    print("\n[4/4] 保存并推送...")
    os.makedirs('/tmp/reports', exist_ok=True)
    with open('/tmp/reports/' + fn + '.md', 'w', encoding='utf-8') as f:
        f.write("# 财经新闻汇总 - " + ds + " " + ts + "\n\n" + desp)

    url = "https://sctapi.ftqq.com/" + SENDKEY + ".send"
    data = urllib.parse.urlencode({'title': title, 'desp': desp}).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST', headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print("  推送成功:", result)
    except Exception as e:
        print("  推送失败:", e)

if __name__ == '__main__':
    main()