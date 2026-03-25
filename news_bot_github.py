# -*- coding: utf-8 -*-
"""
财经新闻汇总 - GitHub Actions 版本
英文权威源采集 → 去重精选 → 翻译成中文推送
市场数据：COMEX黄金、LME铜、WTI+布伦特原油、铁矿石
"""
import urllib.request
import urllib.parse
import json
import os
import re
import time
from datetime import datetime

# ─── HTTP 通用 ───────────────────────────────────────────────
def http_get(url, headers=None, timeout=15):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print("  [网络错误] {}: {}".format(url[:70], e))
        return None

# ─── 请求头 ────────────────────────────────────────────────
H_SINA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://finance.sina.com.cn'
}
H_EM = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://www.eastmoney.com'
}
H_RSS = {
    'User-Agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*'
}

SENDKEY = os.environ.get('SERVERCHAN_SENDKEY', 'SCT328691TqGJDJfpEgA5noR3meGMVrKJ7')

# ═══════════════════════════════════════════════════════════════
# 第1部分：英文新闻采集 + 去重精选 + 翻译
# ═══════════════════════════════════════════════════════════════

# 英文权威财经新闻源（按优先级排列）
EN_SOURCES = [
    # 彭博
    ('https://feeds.bloomberg.com/markets/news.rss',          'Bloomberg'),
    # 金融时报
    ('https://www.ft.com/rss/home/uk',                        'Financial Times'),
    # 华尔街日报
    ('https://feeds.a.dj.com/rss/RSSMarketsMain.xml',         'WSJ Markets'),
    # CNBC
    ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
    # MarketWatch
    ('https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines', 'MarketWatch'),
    # BBC Business
    ('https://feeds.bbci.co.uk/news/business/rss.xml',        'BBC Business'),
    # Reuters Business
    ('https://feeds.reuters.com/reuters/businessNews',         'Reuters'),
    # The Economist
    ('https://www.economist.com/finance-and-economics/rss.xml','The Economist'),
]

# 去重用的关键词提取（取标题前几个核心词）
def extract_key(title):
    """提取标题关键词用于去重"""
    title = title.lower()
    # 去掉常见停用词
    stop = {'the','a','an','in','on','at','to','of','for','and','or','is','are',
            'was','were','with','by','as','from','that','this','it','be','has',
            'have','will','says','said','new','after','over','amid'}
    words = re.findall(r'[a-z]+', title)
    keywords = [w for w in words if w not in stop and len(w) > 2]
    return ' '.join(keywords[:5])  # 取前5个关键词

def parse_rss(feed_text, source_name, max_items=10):
    """通用 RSS 解析，返回英文 title + desc"""
    news = []
    items = re.findall(r'<item>(.*?)</item>', feed_text, re.DOTALL)
    for item in items:
        # 标题
        title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
        if not title_m:
            title_m = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item, re.DOTALL)
        # 摘要
        desc_m = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL)
        if not desc_m:
            desc_m = re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', item, re.DOTALL)
        # 链接
        link_m = re.search(r'<link>(https?://[^\s<"]+)</link>', item)

        title = title_m.group(1).strip() if title_m else ''
        title = re.sub(r'<[^>]+>', '', title).strip()
        desc  = desc_m.group(1).strip() if desc_m else ''
        desc  = re.sub(r'<[^>]+>', '', desc).strip()
        link  = link_m.group(1).strip() if link_m else ''

        # 过滤
        if not title or len(title) < 10:
            continue
        skip_kw = ['video', 'podcast', 'press release', 'advertisement', 'sponsored',
                   'subscribe', 'sign up', 'newsletter', 'quiz', 'crossword']
        if any(k in title.lower() for k in skip_kw):
            continue

        news.append({
            'title_en': title,
            'desc_en':  desc[:300] if desc else '',
            'source':   source_name,
            'link':     link
        })
        if len(news) >= max_items:
            break
    return news

def fetch_en_news(target=15):
    """从多个英文源采集，去重后精选 target 条"""
    raw = []
    seen_keys = set()

    for url, src in EN_SOURCES:
        if len(raw) >= target * 2:  # 采集足够多再精选
            break
        print("  抓取 {} ...".format(src))
        text = http_get(url, H_RSS)
        if not text:
            print("    -> 失败，跳过")
            continue
        items = parse_rss(text, src)
        added = 0
        for n in items:
            key = extract_key(n['title_en'])
            # 相似度去重：key 前3词相同视为重复
            key3 = ' '.join(key.split()[:3])
            if key3 and key3 not in seen_keys:
                seen_keys.add(key3)
                raw.append(n)
                added += 1
        print("    -> 新增 {} 条（累计 {}）".format(added, len(raw)))

    # 精选：优先保留有摘要的、来源多样的
    # 按来源分组，每个来源最多取3条
    source_count = {}
    selected = []
    for n in raw:
        src = n['source']
        if source_count.get(src, 0) < 3:
            source_count[src] = source_count.get(src, 0) + 1
            selected.append(n)
        if len(selected) >= target:
            break

    print("  精选 {} 条新闻".format(len(selected)))
    return selected

# ─── 翻译（MyMemory 免费API，无需Key） ──────────────────────
def translate_zh(text, retries=2):
    """用 MyMemory 免费翻译 API 将英文翻译成简体中文"""
    if not text or not text.strip():
        return text
    # MyMemory 每天免费 5000 词
    encoded = urllib.parse.quote(text[:500])
    url = 'https://api.mymemory.translated.net/get?q={}&langpair=en|zh-CN'.format(encoded)
    for attempt in range(retries):
        try:
            resp = http_get(url, timeout=10)
            if resp:
                data = json.loads(resp)
                translated = data.get('responseData', {}).get('translatedText', '')
                # MyMemory 有时返回错误提示
                if translated and 'MYMEMORY WARNING' not in translated and len(translated) > 2:
                    return translated
        except Exception as e:
            print("    [翻译失败] {}: {}".format(text[:30], e))
        time.sleep(0.5)
    return text  # 翻译失败返回原文

def translate_news(news_list):
    """批量翻译新闻标题和摘要"""
    print("  翻译 {} 条新闻...".format(len(news_list)))
    for i, n in enumerate(news_list):
        print("    [{}/{}] {}...".format(i+1, len(news_list), n['title_en'][:40]))
        n['title_zh'] = translate_zh(n['title_en'])
        if n['desc_en']:
            # 摘要只取前200字符翻译，节省API配额
            n['desc_zh'] = translate_zh(n['desc_en'][:200])
        else:
            n['desc_zh'] = ''
        time.sleep(0.3)  # 避免触发频率限制
    return news_list

# ═══════════════════════════════════════════════════════════════
# 第2部分：市场数据采集
# ═══════════════════════════════════════════════════════════════

def safe_float(v, default=None):
    try:
        f = float(v)
        return f if abs(f) < 1e9 else default
    except (TypeError, ValueError):
        return default

def calc_pct(price, prev):
    p, pr = safe_float(price), safe_float(prev)
    if p is None or pr is None or pr == 0:
        return None
    return round((p - pr) / pr * 100, 2)

def fmt_pct(pct):
    if pct is None:
        return '—'
    return '{}{:.2f}%'.format('+' if pct >= 0 else '', pct)

# ─── 东方财富 A股 ────────────────────────────────────────────
def get_em_stock(secid):
    txt = http_get(
        'https://push2.eastmoney.com/api/qt/stock/get?secid={}&fields=f43,f170,f171'.format(secid),
        H_EM
    )
    if not txt: return None
    try:
        d = json.loads(txt).get('data')
        if not d or not d.get('f43'): return None
        return {'price': d['f43']/100, 'pct': (d.get('f170') or 0)/100}
    except: return None

# ─── 新浪期货行情 ────────────────────────────────────────────
def get_sina(sym):
    txt = http_get('https://hq.sinajs.cn/list={}'.format(sym), H_SINA)
    if not txt: return None
    m = re.search(r'hq_str_' + re.escape(sym) + r'="([^"]+)"', txt)
    if not m: return None
    return m.group(1).split(',')

def parse_futures(parts, price_idx=0, prev_idx=8):
    if not parts or len(parts) <= max(price_idx, prev_idx):
        return None, None
    price = safe_float(parts[price_idx])
    prev  = safe_float(parts[prev_idx])
    pct   = calc_pct(price, prev)
    return price, pct

# ─── 黄金（COMEX纽约金） ─────────────────────────────────────
def fetch_gold():
    p, pct = parse_futures(get_sina('hf_GC'))
    if p: return {'label': 'COMEX黄金期货（纽约）', 'price': p, 'pct': pct, 'unit': '美元/盎司'}
    p, pct = parse_futures(get_sina('hf_XAU'))
    if p: return {'label': '伦敦现货黄金', 'price': p, 'pct': pct, 'unit': '美元/盎司'}
    return None

# ─── 铜（LME伦敦金属交易所） ─────────────────────────────────
def fetch_copper():
    # COMEX铜 HG（美分/磅）
    p, pct = parse_futures(get_sina('hf_HG'))
    if p: return {'label': 'COMEX铜期货（纽约）', 'price': p, 'pct': pct, 'unit': '美分/磅'}
    return None

# ─── 原油（WTI + 布伦特） ────────────────────────────────────
def fetch_oil():
    results = []
    p, pct = parse_futures(get_sina('hf_CL'))
    if p: results.append({'label': 'NYMEX WTI原油', 'price': p, 'pct': pct, 'unit': '美元/桶'})
    p, pct = parse_futures(get_sina('hf_BZ'))
    if p: results.append({'label': 'ICE布伦特原油', 'price': p, 'pct': pct, 'unit': '美元/桶'})
    if not results:
        p, pct = parse_futures(get_sina('hf_OIL'))
        if p: results.append({'label': '布伦特原油', 'price': p, 'pct': pct, 'unit': '美元/桶'})
    return results

# ─── 铁矿石 ──────────────────────────────────────────────────
def fetch_iron_ore():
    results = []
    # 大商所铁矿石期货（国内基准）
    p, pct = parse_futures(get_sina('hf_I'))
    if p: results.append({'label': '大商所铁矿石期货', 'price': p, 'pct': pct, 'unit': '人民币/吨', 'note': '国内基准'})
    # 普氏62%Fe指数（澳大利亚/巴西现货基准）
    # 通过东方财富获取铁矿石现货指数
    txt = http_get(
        'https://push2.eastmoney.com/api/qt/stock/get?secid=113.SCBPI&fields=f43,f170',
        H_EM
    )
    if txt:
        try:
            d = json.loads(txt).get('data')
            if d and d.get('f43'):
                p2 = d['f43'] / 100
                pct2 = (d.get('f170') or 0) / 100
                results.append({'label': '普氏铁矿石62%Fe指数', 'price': p2, 'pct': pct2, 'unit': '美元/吨', 'note': '澳大利亚/巴西现货'})
        except: pass
    return results

# ═══════════════════════════════════════════════════════════════
# 第3部分：主程序
# ═══════════════════════════════════════════════════════════════
def main():
    now = datetime.now()
    ts  = now.strftime("%H:%M")
    ds  = now.strftime("%Y年%m月%d日")
    wk  = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
    fn  = now.strftime("%Y-%m-%d-%H-00")
    ha  = (now.hour - 8) % 24
    ts8 = '{:02d}:{:02d}'.format(ha, now.minute)

    print('=' * 55)
    print('开始生成报告 {} {}'.format(ds, ts))
    print('=' * 55)

    # ── 1. 采集英文新闻 ──────────────────────────────────────
    print('\n[1/4] 采集英文新闻...')
    en_news = fetch_en_news(target=12)

    # ── 2. 翻译成中文 ────────────────────────────────────────
    print('\n[2/4] 翻译成简体中文...')
    news = translate_news(en_news)

    # ── 3. 采集市场数据 ──────────────────────────────────────
    print('\n[3/4] 采集市场数据...')

    # A股
    sh = get_em_stock('1.000001')
    hs300 = get_em_stock('1.000300')
    sz = get_em_stock('0.399001')

    # 恒生
    hsi_parts = get_sina('rt_hkHSI')
    hsi = None
    if hsi_parts and len(hsi_parts) > 9:
        p = safe_float(hsi_parts[2])
        pct = safe_float(hsi_parts[8])
        if p: hsi = {'price': p, 'pct': pct}

    gold   = fetch_gold()
    copper = fetch_copper()
    oils   = fetch_oil()
    iron   = fetch_iron_ore()

    print('  黄金: {}'.format('OK' if gold else '无数据'))
    print('  铜:   {}'.format('OK' if copper else '无数据'))
    print('  原油: {} 条'.format(len(oils)))
    print('  铁矿: {} 条'.format(len(iron)))

    # ── 4. 生成报告 ──────────────────────────────────────────
    print('\n[4/4] 生成报告并推送...')
    lines = []

    lines.append('## 📰 全球财经新闻汇总\n\n')
    lines.append('**日期**：{}（{}）\n'.format(ds, wk))
    lines.append('**时段**：{} — {}（北京时间）\n'.format(ts8, ts))
    lines.append('**编制**：羊咩咩 🐏\n')
    lines.append('**说明**：新闻来源 Bloomberg / FT / WSJ / CNBC / BBC / Reuters，英文原文翻译为简体中文\n')
    lines.append('\n---\n\n')

    # 一、重大事件
    lines.append('## 一、重大事件\n\n')
    for i, n in enumerate(news, 1):
        title_zh = n.get('title_zh') or n['title_en']
        desc_zh  = n.get('desc_zh') or n.get('desc_en', '')
        src      = n['source']
        link     = n['link']

        lines.append('**{}. {}**\n'.format(i, title_zh))
        if desc_zh:
            lines.append('> {}\n'.format(desc_zh))
        ref = '信源：{}'.format(src)
        if link:
            ref += ' · [原文]({})\n'.format(link)
        else:
            ref += '\n'
        lines.append(ref)
        lines.append('\n')

    lines.append('\n---\n\n')

    # 二、市场摘要
    lines.append('## 二、市场摘要\n\n')

    # 股指
    lines.append('### 📈 全球股指\n\n')
    idx_data = [
        ('上证指数', sh),
        ('沪深300', hs300),
        ('深证成指', sz),
        ('恒生指数', hsi),
    ]
    any_idx = False
    for name, d in idx_data:
        if d:
            p = safe_float(d.get('price'))
            pct = safe_float(d.get('pct'))
            if p:
                lines.append('- **{}**：{:.2f}（{}）\n'.format(name, p, fmt_pct(pct)))
                any_idx = True
    if not any_idx:
        lines.append('- 暂无数据\n')
    lines.append('\n')

    # 黄金
    lines.append('### 🥇 黄金（COMEX纽约商品交易所）\n\n')
    if gold:
        p = gold['price']
        lines.append('- **{}**：${:.2f} {}（{}）\n'.format(
            gold['label'], p, gold['unit'], fmt_pct(gold['pct'])))
    else:
        lines.append('- 暂无数据\n')
    lines.append('\n')

    # 铜
    lines.append('### 🔩 铜（LME伦敦金属交易所）\n\n')
    if copper:
        p = copper['price']
        lines.append('- **{}**：{:.2f} {}（{}）\n'.format(
            copper['label'], p, copper['unit'], fmt_pct(copper['pct'])))
    else:
        lines.append('- 暂无数据\n')
    lines.append('\n')

    # 原油
    lines.append('### 🛢️ 原油\n\n')
    if oils:
        for oil in oils:
            lines.append('- **{}**：${:.2f} {}（{}）\n'.format(
                oil['label'], oil['price'], oil['unit'], fmt_pct(oil['pct'])))
        lines.append('\n*WTI：纽约商业交易所（NYMEX）；布伦特：洲际交易所（ICE）*\n')
    else:
        lines.append('- 暂无数据\n')
    lines.append('\n')

    # 铁矿石
    lines.append('### ⚙️ 铁矿石\n\n')
    if iron:
        for ore in iron:
            note = '（{}）'.format(ore['note']) if ore.get('note') else ''
            lines.append('- **{}**{}：{:.2f} {}（{}）\n'.format(
                ore['label'], note, ore['price'], ore['unit'], fmt_pct(ore['pct'])))
        lines.append('\n*普氏62%Fe指数为澳大利亚/巴西现货基准价*\n')
    else:
        lines.append('- 暂无数据\n')
    lines.append('\n')

    # 外汇（简单展示）
    lines.append('### 💱 外汇\n\n')
    cny_parts = get_sina('USDCNY')
    if not cny_parts:
        cny_parts = get_sina('fx_susdcny')
    if cny_parts and len(cny_parts) > 3:
        p = safe_float(cny_parts[1]) or safe_float(cny_parts[0])
        if p:
            lines.append('- **美元/人民币（USD/CNY）**：{:.4f}\n'.format(p))
    else:
        lines.append('- 暂无数据\n')
    lines.append('\n')

    # 页脚
    lines.append('\n---\n')
    lines.append('*数据截至北京时间{} | 仅供参考，投资有风险，入市需谨慎*\n'.format(ts))
    lines.append('*由羊咩咩 🐏 自动生成*\n')

    desp = ''.join(lines)
    print('  报告 {} 字符'.format(len(desp)))

    # ── 推送 Server酱 ────────────────────────────────────────
    title = '财经新闻汇总 {} {}'.format(ds, ts)
    url = 'https://sctapi.ftqq.com/{}.send'.format(SENDKEY)
    data = urllib.parse.urlencode({'title': title, 'desp': desp}, encoding='utf-8').encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print('  推送结果: code={} {}'.format(result.get('code'), result.get('message', '')))
    except Exception as e:
        print('  推送失败: {}'.format(e))

    # ── 本地保存 ─────────────────────────────────────────────
    try:
        reports_dir = '/tmp/reports' if os.path.exists('/tmp') else r'C:\Users\84351\.qclaw\workspace\reports'
        os.makedirs(reports_dir, exist_ok=True)
        fp = os.path.join(reports_dir, fn + '.md')
        with open(fp, 'w', encoding='utf-8') as f:
            f.write('# 财经新闻汇总 - {} {}\n\n'.format(ds, ts))
            f.write(desp)
        print('  已保存: {}'.format(fp))
    except Exception as e:
        print('  保存失败: {}'.format(e))

if __name__ == '__main__':
    main()
