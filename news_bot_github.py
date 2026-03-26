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
    """获取 Yahoo Finance 数据，包含涨跌幅"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?interval=1d&range=2d"
    txt = http_get(url)
    if not txt: return None
    try:
        data = json.loads(txt)
        result = data.get('chart', {}).get('result', [{}])[0]
        meta = result.get('meta', {})
        price = meta.get('regularMarketPrice')
        prev = meta.get('previousClose')
        
        # 尝试从历史数据获取涨跌幅
        indicators = result.get('indicators', {})
        quote = indicators.get('quote', [{}])[0] if indicators.get('quote') else {}
        close_prices = quote.get('close', [])
        
        if not price: return None
        
        # 计算涨跌幅
        if prev and prev > 0:
            pct = (price - prev) / prev * 100
        else:
            pct = 0
            
        return {'price': round(price, 2), 'pct': round(pct, 2)}
    except Exception as e:
        print("Yahoo error:", e)
        return None

def get_em(secid):
    txt = http_get('https://push2.eastmoney.com/api/qt/stock/get?secid=' + secid + '&fields=f43,f170')
    if not txt: return None
    try:
        d = json.loads(txt).get('data', {})
        return {'price': round(d.get('f43', 0) / 100, 2), 'pct': round((d.get('f170') or 0) / 100, 2)}
    except: return None

# 完整翻译词典
TRANS = {
    # 人名/机构
    'Trump': '特朗普', 'Biden': '拜登', 'Fed': '美联储', 'Federal Reserve': '美联储',
    'Nagel': '纳格尔', 'Barrett': '巴雷特', 'Gorsuch': '戈萨奇',
    'Henkel': '汉高', 'Olaplex': '欧拉普莱克斯', 'Meta': 'Meta', 'YouTube': 'YouTube',
    'Next': 'Next', 'H&M': 'H&M', 'ECB': '欧洲央行', 'NS&I': '英国国民储蓄银行',
    'Octopus': 'Octopus能源', 'Iran': '伊朗', 'Israel': '以色列',
    
    # 国家地区
    'China': '中国', 'Chinese': '中国', 'US': '美国', 'U.S.': '美国', 'America': '美国', 'American': '美国',
    'Russia': '俄罗斯', 'Ukraine': '乌克兰', 'Europe': '欧洲', 'European': '欧洲',
    'UK': '英国', 'Germany': '德国', 'France': '法国', 'Middle East': '中东',
    'Japan': '日本', 'Japanese': '日本', 'Korea': '韩国', 'India': '印度',
    
    # 金融术语
    'stock': '股票', 'stocks': '股市', 'market': '市场', 'markets': '市场',
    'oil': '原油', 'gold': '黄金', 'bond': '债券', 'bonds': '债券',
    'rate': '利率', 'rates': '利率', 'interest': '利息', 'inflation': '通胀',
    'trade': '贸易', 'tariff': '关税', 'tariffs': '关税', 'tax': '税收',
    'bank': '银行', 'banks': '银行', 'economy': '经济', 'economic': '经济',
    'growth': '增长', 'recession': '衰退', 'crisis': '危机',
    'price': '价格', 'prices': '价格', 'cost': '成本', 'costs': '成本',
    'deal': '协议', 'agreement': '协议', 'contract': '合同',
    'war': '战争', 'conflict': '冲突', 'tension': '紧张',
    'sanction': '制裁', 'sanctions': '制裁',
    'supply': '供应', 'demand': '需求',
    'production': '生产', 'output': '产出',
    'company': '公司', 'companies': '公司', 'firm': '公司',
    'investor': '投资者', 'investors': '投资者',
    'report': '报告', 'reports': '报告', 'data': '数据', 'survey': '调查',
    'profit': '利润', 'revenue': '营收', 'earnings': '盈利',
    'debt': '债务', 'loan': '贷款', 'credit': '信贷',
    
    # 动词
    'says': '表示', 'said': '表示', 'announced': '宣布', 'announces': '宣布',
    'warns': '警告', 'warned': '警告', 'expects': '预计', 'expected': '预计',
    'rise': '上涨', 'rises': '上涨', 'rising': '上涨', 'rose': '上涨',
    'fall': '下跌', 'falls': '下跌', 'falling': '下跌', 'fell': '下跌',
    'drop': '下跌', 'drops': '下跌', 'dropped': '下跌',
    'gain': '上涨', 'gains': '上涨', 'surge': '飙升', 'surged': '飙升',
    'decline': '下降', 'declines': '下降', 'slump': '暴跌', 'slumped': '暴跌',
    'cut': '削减', 'cuts': '削减', 'reduce': '减少', 'reduced': '减少',
    'increase': '增加', 'increases': '增加', 'raise': '提高', 'raised': '提高',
    'lift': '上调', 'lifts': '上调', 'lifted': '上调',
    'see': '预计', 'sees': '预计', 'saw': '预计',
    'review': '审议', 'reviewed': '审议',
    'squeeze': '施压', 'backfire': '适得其反',
    
    # 形容词/副词
    'high': '高点', 'low': '低点', 'record': '纪录',
    'weak': '疲软', 'strong': '强劲', 'major': '重大',
    'landmark': '里程碑式', 'cryptic': '神秘', 'prolonged': '长期',
    
    # 其他
    'meeting': '会议', 'summit': '峰会', 'talk': '会谈', 'talks': '会谈',
    'president': '总统', 'minister': '部长', 'official': '官员', 'analysts': '分析师',
    'central bank': '央行', 'government': '政府',
    'policy': '政策', 'policies': '政策',
    'decision': '决定', 'vote': '投票', 'election': '选举',
    'Supreme Court': '最高法院', 'Congress': '国会', 'Senate': '参议院', 'Justice': '大法官', 'Justices': '大法官',
    'Wall Street': '华尔街', 'White House': '白宫',
    'Treasury': '财政部', 'Securities': '证券',
    'Bitcoin': '比特币', 'crypto': '加密货币', 'cryptocurrency': '加密货币',
    'AI': '人工智能', 'technology': '科技', 'tech': '科技',
    'semiconductor': '半导体', 'chip': '芯片', 'chips': '芯片',
    'auto': '汽车', 'automaker': '汽车制造商', 'vehicle': '车辆',
    'energy': '能源', 'gas': '天然气', 'solar': '太阳能', 'panel': '电池板',
    'steel': '钢铁', 'metal': '金属', 'copper': '铜',
    'hair care': '护发', 'brand': '品牌',
    'compensation': '赔偿', 'customers': '客户', 'million': '百万', 'millions': '数百万',
    'addiction': '成瘾', 'trial': '审判', 'liable': '有责任',
    'speculation': '猜测', 'online': '网上', 'videos': '视频',
    'turbulence': '动荡', 'fly': '飞行', 'airlines': '航空公司',
    'contingency': '应急', 'plan': '计划', 'reopen': '重新开放',
    'sales': '销售', 'start': '开始', 'year': '年',
    'guidance': '业绩指引', 'costs': '成本', 'still': '仍',
    'option': '选项', 'April': '四月', 'hike': '加息',
    'advances': '上涨', 'conflicting': '相互矛盾', 'comments': '评论',
    'intention': '意图', 'hold': '举行', 'proposal': '提议', 'end': '结束',
    'sicken': '令人生厌', 'me': '我', 'ruling': '裁决',
    'backwardation': '现货溢价', 'means': '意味着',
    'troops': '军队', 'troop': '军队', 'more': '更多', 'but': '但', 'may': '可能',
    'nearing': '接近', 'disappoint': '不及预期', 'disappoints': '不及预期',
}

def translate(text):
    """翻译文本"""
    result = text
    # 按长度排序，先翻译长的词组
    for en, zh in sorted(TRANS.items(), key=lambda x: -len(x[0])):
        result = re.sub(r'\b' + re.escape(en) + r'\b', zh, result, flags=re.IGNORECASE)
    return result

def format_time(time_str):
    try:
        for fmt in ['%a, %d %b %Y %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%d %b %Y %H:%M:%S']:
            try:
                dt = datetime.strptime(time_str[:25], fmt)
                return dt.strftime('%m月%d日 %H:%M')
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
            title_en = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', title_m.group(1), flags=re.DOTALL)
            title_en = re.sub(r'<[^>]+>', '', title_en).strip()
            
            if len(title_en) < 20: continue
            
            key = title_en[:40].lower()
            if key in seen: continue
            seen.add(key)
            
            time_m = re.search(r'<pubDate>(.*?)</pubDate>', item, re.DOTALL)
            pub_time = format_time(time_m.group(1).strip()) if time_m else ''
            
            title_zh = translate(title_en)
            
            all_news.append({
                'title_en': title_en,
                'title_zh': title_zh,
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
            market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'Yahoo Finance'}
            print("  OK", name, r['price'], r['pct'])
        time.sleep(0.2)

    for secid, name in [('1.000001', '上证指数'), ('1.000300', '沪深300')]:
        r = get_em(secid)
        if r:
            market[name] = {**r, 'src': '东方财富'}
            print("  OK", name, r['price'], r['pct'])

    for sym, name in [('GC=F', '黄金期货'), ('CL=F', 'WTI原油'), ('BZ=F', '布伦特原油')]:
        r = get_yahoo(sym)
        if r:
            market[name] = {'price': r['price'], 'pct': r['pct'], 'src': 'Yahoo Finance'}
            print("  OK", name, r['price'], r['pct'])
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
        lines.append("**" + str(i) + ". " + n['title_en'] + "**\n")
        lines.append("   📌 " + n['title_zh'] + "\n")
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