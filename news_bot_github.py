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
        print("[ERROR]", url, e)
        return None

def get_yahoo_quote(symbol):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?interval=1d&range=1d"
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
    url = 'https://push2.eastmoney.com/api/qt/stock/get?secid=' + secid + '&fields=f43,f170,f171'
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
    if len(p) > 8:news = fetch_news()
    print("  Total:", len(news))

print("\n[2/4] Fetching market data ...")
    market = {}

    for sym, name in [('^DJI', '道琼斯工业'), ('^NDX', '纳斯达克100'), ('^GSPC', '标普500'), ('AAPL', '苹果')]:
        r = get_yahoo_quote(sym)
        if r:
            market[name] = {'price': r['price'], 'change_pct': r['change_pct'], 'src': 'Yahoo Finance'}
            print("  OK", name, ":", r['price'], "(" + str(r['change_pct']) + "%)")
        time.sleep(0.2)
for secid, name in [('1.000001', '上证指数'), ('1.000300', '沪深300')]:
        r = get_em_stock(secid)
        if r:
            market[name] = {**r, 'src': '东方财富'}
            print("  OK", name, ":", r['price'], "(" + str(r['change_pct']) + "%)")

r = get_sina_hk()
    if r:
        market['恒生指数'] = {**r, 'src': '新浪财经'}
        print("  OK 恒生指数 :", r['price'], "(" + str(r['change_pct']) + "%)")

for sym, name in [('GC=F', '黄金期货'), ('CL=F', 'WTI原油'), ('BZ=F', '布伦特原油')]:
        r = get_yahoo_quote(sym)
        if r:
            market[name] = {'price': r['price'], 'change_pct': r['change_pct'], 'src': 'Yahoo Finance'}
            print("  OK", name, ": $" + str(r['price']), "(" + str(r['change_pct']) + "%)")
        time.sleep(0.2)

print("\n  Total:", len(market), "items")

print("\n[3/4] Generating report ...")
    lines = ["## 财经新闻汇总\n", "**日期**: " + ds + "（" + wk + "）\n", "**时段**: " + ts8 + "-" + ts + "\n", "**编制**: 羊咩咩\n\n---\n\n## 一、重大事件\n"]

for i, n in enumerate(news[:12], 1):
        lines.append("**" + str(i) + ". " + n['title'] + "** — 信源: " + n['source'] + "\n\n")

lines.append("\n---\n\n## 二、市场摘要\n\n### 股指情况\n\n")
    for name in ['道琼斯工业', '纳斯达克100', '标普500', '苹果', '上证指数', '沪深300', '恒生指数']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['change_pct'], 2)) + "%" if d['change_pct'] >= 0 else str(round(d['change_pct'], 2)) + "%"
            lines.append(name + "：" + str(d['price']) + " (" + pct + ") — " + d['src'] + "\n")
lines.append("\n### 黄金市场\n\n")
    if '黄金期货' in market:
        d = market['黄金期货']
        pct = "+" + str(round(d['change_pct'], 2)) + "%" if d['change_pct'] >= 0 else str(round(d['change_pct'], 2)) + "%"
        lines.append("COMEX黄金期货：$" + str(d['price']) + "/盎司 (" + pct + ") — " + d['src'] + "\n")
    else:
        lines.append("COMEX黄金期货：暂无法获取\n")

lines.append("\n### 原油市场\n\n")
    for name in ['WTI原油', '布伦特原油']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['change_pct'], 2)) + "%" if d['change_pct'] >= 0 else str(round(d['change_pct'], 2)) + "%"
            lines.append(name + "：$" + str(d['price']) + "/桶 (" + pct + ") — " + d['src'] + "\n")
        else:
            lines.append(name + "：暂无法获取\n")

lines.append("\n### 外汇市场\n（暂不可用）\n")
    lines.append("\n### 债券市场\n（暂不可用）\n")
    lines.append("\n---\n")
    lines.append("\n*数据截至北京时间 " + ts + "*\n")

desp = ''.join(lines)
    title = "财经新闻汇总 " + ts

print("\n[4/4] Saving and pushing ...")
    os.makedirs('/tmp/reports', exist_ok=True)
    fp = '/tmp/reports/' + fn + '.md'
    with open(fp, 'w', encoding='utf-8') as f:
        f.write("# 财经新闻汇总 - " + ds + " " + ts + "\n\n")
        f.write(desp)
    print("  Saved:", fp)

url = "https://sctapi.ftqq.com/" + SENDKEY + ".send"
    data = urllib.parse.urlencode({'title': title, 'desp': desp}, encoding='utf-8').encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST', headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print("  Push result:", result)
    except Exception as e:
        pri
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
        print("  Fetching", source, "...")
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
    print("财经新闻汇总", ds, ts)
    print("=" * 50)

print("\n[1/4] Fetching news ...")
