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

# 新闻翻译字典（常见词汇）
TRANSLATE = {
    'Trump': '特朗普', 'Biden': '拜登', 'Fed': '美联储', 'Federal Reserve': '美联储',
    'China': '中国', 'Chinese': '中国', 'US': '美国', 'America': '美国', 'American': '美国',
    'Russia': '俄罗斯', 'Ukraine': '乌克兰', 'Iran': '伊朗', 'Israel': '以色列',
    'Europe': '欧洲', 'European': '欧洲', 'UK': '英国', 'Germany': '德国', 'France': '法国',
    'Japan': '日本', 'Japanese': '日本', 'Korea': '韩国', 'India': '印度',
    'stock': '股票', 'stocks': '股市', 'market': '市场', 'markets': '市场',
    'oil': '原油', 'gold': '黄金', 'bond': '债券', 'bonds': '债券',
    'rate': '利率', 'rates': '利率', 'interest': '利息', 'inflation': '通胀',
    'trade': '贸易', 'tariff': '关税', 'tariffs': '关税', 'tax': '税收',
    'bank': '银行', 'banks': '银行', 'economy': '经济', 'economic': '经济',
    'growth': '增长', 'recession': '衰退', 'crisis': '危机',
    'price': '价格', 'prices': '价格', 'cost': '成本',
    'deal': '协议', 'agreement': '协议', 'contract': '合同',
    'war': '战争', 'conflict': '冲突', 'tension': '紧张',
    'sanction': '制裁', 'sanctions': '制裁',
    'supply': '供应', 'demand': '需求',
    'production': '生产', 'output': '产出',
    'company': '公司', 'companies': '公司', 'firm': '公司',
    'investor': '投资者', 'investors': '投资者',
    'report': '报告', 'data': '数据', 'survey': '调查',
    'says': '表示', 'said': '表示', 'announced': '宣布',
    'warns': '警告', 'warned': '警告', 'expects': '预计',
    'rise': '上涨', 'rises': '上涨', 'rising': '上涨',
    'fall': '下跌', 'falls': '下跌', 'falling': '下跌',
    'drop': '下跌', 'drops': '下跌', 'dropped': '下跌',
    'gain': '上涨', 'gains': '上涨', 'surge': '飙升',
    'decline': '下降', 'declines': '下降', 'slump': '暴跌',
    'high': '高点', 'low': '低点', 'record': '纪录',
    'cut': '削减', 'cuts': '削减', 'reduce': '减少',
    'increase': '增加', 'increases': '增加', 'raise': '提高',
    'meeting': '会议', 'summit': '峰会', 'talk': '会谈', 'talks': '会谈',
    'president': '总统', 'minister': '部长', 'official': '官员',
    'central bank': '央行', 'government': '政府',
    'policy': '政策', 'policies': '政策',
    'decision': '决定', 'decision': '决议',
    'vote': '投票', 'election': '选举',
    'Supreme Court': '最高法院', 'Congress': '国会', 'Senate': '参议院',
    'Wall Street': '华尔街', 'White House': '白宫',
}

def translate_title(title):
    """翻译新闻标题"""
    result = title
    for en, zh in TRANSLATE.items():
        result = re.sub(r'\b' + en + r'\b', zh, result, flags=re.IGNORECASE)
    return result

def format_time(time_str):
    """格式化时间"""
    try:
        # 尝试解析各种时间格式
        for fmt in ['%a, %d %b %Y %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d %b %Y %H:%M:%S']:
            try:
                dt = datetime.strptime(time_str[:25], fmt)
                return dt.strftime('%m月%d日 %H:%M')
            except: pass
    except: pass
    return time_str[:16] if len(time_str) > 16 else ''

def fetch_news():
    """抓取新闻"""
    sources = [
        ('https://feeds.reuters.com/reuters/businessNews', 'Reuters'),
        ('https://feeds.bbci.co.uk/news/business/rss.xml', 'BBC'),
        ('https://feeds.bloomberg.com/markets/news.rss', 'Bloomberg'),
        ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
        ('https://feeds.a.dj.com/rss/RSSMarketsMain.xml', 'WSJ'),
        ('https://www.ft.com/rss/home', 'FT'),
    ]
    
    all_news = []
    seen = set()
    
    for url, src in sources:
        print("  Fetching", src, "...")
        txt = http_get(url)
        if not txt:
            continue
            
        items = re.findall(r'<item>(.*?)</item>', txt, re.DOTALL)
        
        for item in items[:5]:  # 每个源取5条
            # 标题
            title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            if not title_m:
                continue
            title = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_m.group(1), flags=re.DOTALL)
            title = re.sub(r'<[^>]+>', '', title).strip()
            
            if len(title) < 20:
                continue
            
            # 过滤重复
            key = title[:40].lower()
            if key in seen:
                continue
            seen.add(key)
            
            # 发布时间
            time_m = re.search(r'<pubDate>(.*?)</pubDate>', item, re.DOTALL)
            pub_time = format_time(time_m.group(1).strip()) if time_m else ''
            
            # 翻译
            title_zh = translate_title(title)
            
            # 生成简要摘要（取标题前50字）
            summary = title_zh[:60] + '...' if len(title_zh) > 60 else title_zh
            
            all_news.append({
                'title': title_zh,
                'title_en': title,
                'source': src,
                'time': pub_time,
                'summary': summary
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

    # 1. 新闻
    print("\n[1/4] 获取新闻...")
    news = fetch_news()
    print("  共", len(news), "条")

    # 2. 市场数据
    print("\n[2/4] 获取市场数据...")
    market = {}

    for sym, name in [('^DJI', '道琼斯工业'), ('^NDX', '纳斯达克100'), ('^GSPC', '标普500'), ('AAPL', '苹果')]:
        r = get_yahoo(sym)
        if r:
            market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'Yahoo Finance'}
            print("  OK", name, ":", r['price'], "(" + str(r['pct']) + "%)")
        time.sleep(0.2)

    for secid, name in [('1.000001', '上证指数'), ('1.000300', '沪深300')]:
        r = get_em(secid)
        if r:
            market[name] = {**r, 'src': '东方财富'}
            print("  OK", name, ":", r['price'], "(" + str(r['pct']) + "%)")

    for sym, name in [('GC=F', '黄金期货'), ('CL=F', 'WTI原油'), ('BZ=F', '布伦特原油')]:
        r = get_yahoo(sym)
        if r:
            market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'Yahoo Finance'}
            print("  OK", name, ":", r['price'], "(" + str(r['pct']) + "%)")
        time.sleep(0.2)

    print("\n  共", len(market), "项")

    # 3. 生成报告
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
        time_str = " | " + n['time'] if n['time'] else ""
        lines.append("**" + str(i) + ". " + n['title'] + "**\n")
        lines.append("   信源: " + n['source'] + time_str + "\n\n")

    lines.append("\n---\n\n## 二、市场摘要\n\n### 📈 股指情况\n\n")

    for name in ['道琼斯工业', '纳斯达克100', '标普500', '苹果', '上证指数', '沪深300']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            lines.append(name + "：" + str(d['price']) + " (" + pct + ") — " + d['src'] + "\n")

    lines.append("\n### 🥇 黄金市场\n\n")
    if '黄金期货' in market:
        d = market['黄金期货']
        pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
        lines.append("COMEX黄金期货：$" + str(d['price']) + "/盎司 (" + pct + ") — " + d['src'] + "\n")

    lines.append("\n### 🛢️ 原油市场\n\n")
    for name in ['WTI原油', '布伦特原油']:
        if name in market:
            d = market[name]
            pct = "+" + str(round(d['pct'], 2)) + "%" if d['pct'] >= 0 else str(round(d['pct'], 2)) + "%"
            lines.append(name + "：$" + str(d['price']) + "/桶 (" + pct + ") — " + d['src'] + "\n")

    lines.append("\n### 💱 外汇市场\n（暂不可用）\n")
    lines.append("\n### 📊 债券市场\n（暂不可用）\n")
    lines.append("\n---\n")
    lines.append("\n*数据截至北京时间 " + ts + " | 投资有风险，入市需谨慎*\n")

    desp = ''.join(lines)
    title = "财经新闻汇总 " + ts

    # 4. 保存推送
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