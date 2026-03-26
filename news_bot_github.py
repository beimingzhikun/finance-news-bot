python

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
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"[ERROR] {url}: {e}")
        return None

def get_yahoo_quote(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
    txt = http_get(url, {'User-Agent': 'Mozilla/5.0'})
    if not txt:
        return None
    try:
        data = json.loads(txt)
        result = data.get('chart', {}).get('result', [])
        if not result:
            return None
        meta = result[0].get('meta', {})
        price = meta.get('regularMarketPrice')
        prev_close = meta.get('previousClose')
        if not price:
            return None
        change = price - prev_close if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        return {'price': round(price, 2), 'change': round(change, 2), 'change_pct': round(change_pct, 2)}
    except:
        return None
def get_em_stock(secid):
    url = f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f170,f171'
    txt = http_get(url)
    if not txt:
        return None
    try:
        d = json.loads(txt)
        if not d.get('data') or not d['data'].get('f43'):
            return None
        return {'price': round(d['data']['f43'] / 100, 2), 'change_pct': round((d['data'].get('f170') or 0) / 100, 2)}
    except:
        return None

def get_sina_hk():
    txt = http_get('https://hq.sinajs.cn/list=rt_hkHSI', {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'})
    if not txt:
        return None
    m = re.search(r'hq_str_rt_hkHSI="([^"]+)"', txt)
    if not m:
        return None
    p = m.group(1).split(',')
    if len(p) > 8:
        try:
            return {'price': float(p[2]), 'change_pct': round(float(p[8]), 2), 'time': p[17] + ' ' + p[18][:8]}
        except:
            pass
    return None

NEWS_SOURCES = [
    ('https://feeds.reuters.com/reuters/businessNews', 'Reuters'),
    ('https://feeds.bbci.co.uk/news/business/rss.xml', 'BBC'),
    ('https://feeds.bloomberg.com/markets/news.rss', 'Bloomberg'),
    ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
]
def fetch_news():
    all_news = []
    seen = set()
    for url, source in NEWS_SOURCES:
        print(f"  Fetching {source}...")
        txt = http_get(url, {'User-Agent': 'Mozilla/5.0'})
        if not txt:
            continue
        items = re.findall(r'<item>(.*?)</item>', txt, re.DOTALL)
        for item in items[:3]:
            title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            if not title_m:
                continue
            title = title_m.group(1).strip()
            title = re.sub(r'<[^>]+>', '', title)
            if len(title) < 20:
                continue
            key = title[:30].lower()
            if key not in seen:
                seen.add(key)
                all_news.append({'title': title, 'source': source, 'link': ''})
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
    print(f"财经新闻汇总 {ds} {ts}")
    print("=" * 50)

print("\n[1/4] Fetching news...")
    news = fetch_news()
    print(f"  Total: {len(news)}")

print("\n[2/4] Fetching market data...")
    market = {}

# US stocks - Yahoo
    for sym, name in [('^DJI', '道琼斯工业'), ('^NDX', '纳斯达克100'), ('^GSPC', '标普500'), ('AAPL', '苹果')]:
        r = get_yahoo_quote(sym)
        if r:
            market[name] = {'price': r['price'], 'change_pct': r['change_pct'], 'src': 'Yahoo Finance'}
            print(f"  OK {name}: {r['price']} ({r['change_pct']:+.2f}%)")
        time.sleep(0.2)
# A股 - 东方财富
    for secid, name in [('1.000001', '上证指数'), ('1.000300', '沪深300')]:
        r = get_em_stock(secid)
        if r:
            market[name] = {**r, 'src': '东方财富'}
            print(f"  OK {name}: {r['price']:.2f} ({r['change_pct']:+.2f}%)")

# 港股 - 新浪
    r = get_sina_hk()
    if r:
        market['恒生指数'] = {**r, 'src': '新浪财经'}
        print(f"  OK 恒生指数: {r['price']:.2f} ({r['change_pct']:+.2f}%)")

# 黄金和原油 - Yahoo
    for sym, name in [('GC=F', '黄金期货'), ('CL=F', 'WTI原油'), ('BZ=F', '布伦特原油')]:
        r = get_yahoo_quote(sym)
        if r:
            market[name] = {'price': r['price'], 'change_pct': r['change_pct'], 'src': 'Yahoo Finance'}
            print(f"  OK {name}: ${r['price']:.2f} ({r['change_pct']:+.2f}%)")
        time.sleep(0.2)

print(f"\n  Total: {len(market)} items")

print("\n[3/4] Generating report...")
    lines = [f"## 财经新闻汇总\n", f"**日期**: {ds}（{wk}）\n", f"**时段**: {ts8}-{ts}\n", f"**编制**: 羊咩咩\n\n---\n\n## 一、重大事件\n"]

for i, n in enumerate(news[:12], 1):
        lines.append(f"**{i}. {n['title']}** — 信源: {n['source']}\n\n")

lines += ["\n---\n\n## 二、市场摘要\n\n### 股指情况\n\n"]
    for name in ['道琼斯工业', '纳斯达克100', '标普500', '苹果', '上证指数', '沪深300', '恒生指数']:
