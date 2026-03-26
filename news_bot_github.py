python

# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, json, os, re, time
from datetime import datetime, timedelta

SENDKEY = os.environ.get('SERVERCHAN_SENDKEY', 'SCT328691TqGJDJfpEgA5noR3meGMVrKJ7')

def http_get(url, headers=None, timeout=15):
    try:
        req = urllib.request.Request(url, headers=headers or {'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print("[ERROR]", e)
        return None

def get_yahoo(symbol):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?interval=1d&range=1d"
    txt = http_get(url)
    if not txt: return None
    try:
        data = json.loads(txt)
        meta = data.get('chart', {}).get('result', [{}])[0].get('meta', {})
        price = meta.get('regularMarketPrice')
        prev = meta.get('previousClose')
        if not price: return None
        pct = ((price - prev) / prev * 100) if prev else 0
        return {'price': round(price, 2), 'pct': round(pct, 2)}
    except: return None

def get_em(secid):
    txt = http_get('https://push2.eastmoney.com/api/qt/stock/get?secid=' + secid + '&fields=f43,f170')
    if not txt: return None
    try:
        d = json.loads(txt).get('data', {})
        return {'price': round(d.get('f43', 0) / 100, 2), 'pct': round((d.get('f170') or 0) / 100, 2)}
    except: return None
def fetch_news():
    sources = [
        ('https://feeds.reuters.com/reuters/businessNews', 'Reuters'),
        ('https://feeds.bbci.co.uk/news/business/rss.xml', 'BBC'),
        ('https://feeds.bloomberg.com/markets/news.rss', 'Bloomberg'),
    ]
    all_news, seen = [], set()
    for url, src in sources:
        txt = http_get(url)
        if txt:
            for item in re.findall(r'<item>(.*?)</item>', txt, re.DOTALL)[:3]:
                m = re.search(r'<title>(.*?)</title>', item)
                if m:
                    title = re.sub(r'<[^>]+>', '', m.group(1).strip())
                    if len(title) > 20:
                        key = title[:30].lower()
                        if key not in seen:
                            seen.add(key)
                            all_news.append({'title': title, 'source': src})
        time.sleep(0.3)
    return all_news

def main():
    now = datetime.now()
    ts, ds = now.strftime("%H:%M"), now.strftime("%Y%m%d")
    wk = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][now.weekday()]
    fn = now.strftime("%Y-%m-%d-%H-00")
    ts8 = (now - timedelta(hours=8)).strftime("%H:%M")

print("=" * 50)
    print("Finance News", ds, ts)
    print("=" * 50)

news = fetch_news()
    print("\n[1] News:", len(news))

market = {}
    for sym, name in [('^DJI', 'DJI'), ('^NDX', 'NDX'), ('^GSPC', 'SP500'), ('GC=F', 'Gold'), ('CL=F', 'WTI'), ('BZ=F', 'Brent')]:
        r = get_yahoo(sym)
        if r: market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'Yahoo'}
    for secid, name in [('1.000001', 'Shanghai'), ('1.000300', 'CSI300')]:
        r = get_em(secid)
        if r: market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'EM'}
    print("[2] Market:", len(market), "items")
lines = ["## Finance News\n", "**Date**: " + ds + " (" + wk + ")\n", "**Time**: " + ts8 + "-" + ts + "\n\n---\n\n## 1. News\n"]
    for i, n in enumerate(news[:12], 1):
        lines.append("**" + str(i) + ". " + n['title'] + "** - " + n['source'] + "\n\n")
    lines.append("---\n\n## 2. Market Data\n\n")
    for name in ['DJI','NDX','SP500','Gold','WTI','Brent','Shanghai','CSI300']:
        if name in market:
            d = market[name]
            pct = "+" + str(d['pct']) + "%" if d['pct'] >= 0 else str(d['pct']) + "%"
            lines.append(name + ": "+ str(d['price']) + " (" + pct + ") - " + d['src'] + "\n")
    lines.append("\n---\n")
    desp = ''.join(lines)

os.makedirs('/tmp/reports', exist_ok=True)
    with open('/tmp/reports/' + fn + '.md', 'w', encoding='utf-8') as f:
        f.write("# " + ds + " " + ts + "\n\n" + desp)

url = "https://sctapi.ftqq.com/" + SENDKEY + ".send"
    data = urllib.parse.urlencode({'title': "Finance " + ts, 'desp': desp}).encode('utf-8')
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=data, method='POST', headers={'Content-Type': 'application/x-www-form-urlencoded'}), timeout=15)
        print("[3] Pushed OK")
    except Exception as e:
        print("[3] Push fail:", e)

if __name__ == '__main__':
    main()
