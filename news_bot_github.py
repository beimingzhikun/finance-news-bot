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
    except Exception as e:
        print("[ERROR]", e)
        return None

def get_yahoo(symbol):
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
        now = datetime.now().strftime("%H:%M")
        return {'price': round(price, 2), 'pct': round(pct, 2), 'time': now}
    except: return None

def get_em(secid):
    txt = http_get('https://push2.eastmoney.com/api/qt/stock/get?secid=' + secid + '&fields=f43,f170')
    if not txt: return None
    try:
        d = json.loads(txt).get('data', {})
        now = datetime.now().strftime("%H:%M")
        return {'price': round(d.get('f43', 0) / 100, 2), 'pct': round((d.get('f170') or 0) / 100, 2), 'time': now}
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
    
    all_news = []
    seen = set()
    
    for url, src in sources:
        print("  Fetching", src, "...")
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
                if len(desc) > 200:
                    desc = desc[:197] + '...'
            
            time_m = re.search(r'<pubDate>(.*?)</pubDate>', item, re.DOTALL)
            pub_time = format_time(time_m.group(1).strip()) if time_m else ''
            
            all_news.append({
                'title': title,
                'desc': desc,
                'source': src,
                'time': pub_time
            })
        
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
    print("=" * 50)

    print("\n[1/4] 获取新闻...")
    news = fetch_news()
    print("  共", len(news), "条")

    print("\n[2/4] 获取市场数据...")
    market = {}

    for sym, name in [('^DJI', '道琼斯工业'), ('^NDX', '纳斯达克100'), ('^GSPC', '标普500'), ('AAPL', '苹果')]:
        r = get_yahoo(sym)
        if r:
            market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'Yahoo Finance', 'time': r['time']}
        time.sleep(0.2)

    for secid, name in [('1.000001', '上证指数'), ('1.000300', '沪深300')]:
        r = get_em(secid)
        if r:
            market[name] = {**r, 'src': '东方财富'}

    for sym, name in [('GC=F', '黄金期货'), ('CL=F', 'WTI原油'), ('BZ=F', '布伦特原油')]:
        r = get_yahoo(sym)
        if r:
            market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'Yahoo Finance', 'time': r['time']}
        time.sleep(0.2)

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

    lines.append("\n---\n\n## 二、市场摘要\n")
    lines.append("**数据采集时间**: " + ts + "（北京时间）\n\n")
    lines.append("### 📈 股指情况\n\n")

    for name in ['道琼斯工业', '纳斯达克100', '标普500', '苹果', '上证指数', '沪深300']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            t = " " + d.get('time', ts) if d.get('time') else " " + ts
            lines.append(name + "：" + str(d['price']) + " (" + pct + ") — " + d['src'] + t + "\n")

    lines.append("\n### 🥇 黄金市场\n\n")
    if '黄金期货' in market:
        d = market['黄金期货']
        pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
        t = " " + d.get('time', ts) if d.get('time') else " " + ts
        lines.append("COMEX黄金期货：$" + str(d['price']) + "/盎司 (" + pct + ") — " + d['src'] + t + "\n")

    lines.append("\n### 🛢️ 原油市场\n\n")
    for name in ['WTI原油', '布伦特原油']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            t = " " + d.get('time', ts) if d.get('time') else " " + ts
            lines.append(name + "：$" + str(d['price']) + "/桶 (" + pct + ") — " + d['src'] + t + "\n")

    lines.append("\n### 💱 外汇市场\n（暂不可用）\n")
    lines.append("\n### 📊 债券市场\n（暂不可用）\n")
    lines.append("\n---\n")
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