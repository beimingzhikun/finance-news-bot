# -*- coding: utf-8 -*-
"""
财经新闻汇总 - GitHub Actions 版本
全部内容中文推送：国际新闻标题+摘要、黄金(COMEX)、铜(LME)、原油(WTI+布伦特)、铁矿石
"""
import urllib.request
import urllib.parse
import json
import os
import re
from datetime import datetime

# ─── HTTP 通用 ───────────────────────────────────────────────
def http_get(url, headers=None, timeout=15):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print("  [网络错误] {}: {}".format(url[:60], e))
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
H_NEWS = {
    'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
}
H_TRADING = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/xml, text/xml, application/rss+xml'
}

SENDKEY = os.environ.get('SERVERCHAN_SENDKEY', 'SCT328691TqGJDJfpEgA5noR3meGMVrKJ7')

# ═══════════════════════════════════════════════════════════════
# 第1部分：新闻采集（中文标题+摘要）
# ═══════════════════════════════════════════════════════════════
def parse_rss_news(feed_text, source_name, max_items=8):
    """通用 RSS 解析：返回 title + description 列表"""
    news = []
    items = re.findall(r'<item>(.*?)</item>', feed_text, re.DOTALL)
    for item in items:
        title_m = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item)
        if not title_m:
            title_m = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item, re.DOTALL)
        desc_m = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item, re.DOTALL)
        if not desc_m:
            desc_m = re.search(r'<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>', item, re.DOTALL)
        link_m = re.search(r'<link>(https?://[^\s<]+)</link>', item)

        title = title_m.group(1).strip() if title_m else ''
        desc = desc_m.group(1).strip() if desc_m else ''
        # 去掉 HTML 标签
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = desc.strip()
        link = link_m.group(1).strip() if link_m else ''

        if title and len(title) > 5:
            # 跳过视频/音频/PR 内容
            if any(k in title.lower() for k in ['video', 'podcast', 'press release']):
                continue
            news.append({
                'title': title,
                'desc': desc[:200] if desc else '',
                'source': source_name,
                'link': link
            })
        if len(news) >= max_items:
            break
    return news

def fetch_chinese_news():
    """采集中文财经新闻（标题+摘要）"""
    all_news = []
    seen_keys = set()

    # 数据源（中文为主，英文为辅）
    sources = [
        # 新浪财经国际新闻 RSS
        ('https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2517&k=&num=10&page=1', '新浪财经'),
        # 华尔街见闻中文（需实测是否可访问）
        ('https://wallstreetcn.com/rss', '华尔街见闻'),
        # 彭博中文
        ('https://www.bloomberg.com/feed/podcast/etf-report.xml', 'Bloomberg'),
        # BBC 中文
        ('https://feeds.bbci.co.uk/zhongwen/simp/rss.xml', 'BBC中文'),
        # 纽约时报中文
        ('https://cn.nytimes.com/rss.html', '纽约时报中文'),
        # 经济学人中文
        ('https://www.ecofin.cn/feed', '经济学人中文'),
        # 金融时报中文
        ('https://www.ft.com/rss/china', '金融时报中文'),
    ]

    for url, src in sources:
        if len(all_news) >= 15:
            break
        print("  抓取: {} ...".format(src))
        text = http_get(url, H_NEWS)
        if not text:
            # 备用：英文 Reuters 走翻译
            text = http_get('https://feeds.reuters.com/reuters/businessNews', H_TRADING)
            if text:
                items = parse_rss_news(text, 'Reuters')
                for n in items:
                    key = n['title'][:25]
                    if key not in seen_keys:
                        seen_keys.add(key)
                        all_news.append(n)
            continue
        items = parse_rss_news(text, src)
        print("    -> 获得 {} 条".format(len(items)))
        for n in items:
            key = n['title'][:25]
            if key not in seen_keys:
                seen_keys.add(key)
                all_news.append(n)

    return all_news

# ═══════════════════════════════════════════════════════════════
# 第2部分：市场数据采集
# ═══════════════════════════════════════════════════════════════

def safe_float(v, default=None):
    """安全转浮点数"""
    try:
        f = float(v)
        # 数据异常检测：绝对值超过合理范围视为脏数据
        if abs(f) > 1e9:
            return default
        return f
    except (TypeError, ValueError):
        return default

def calc_pct(price, prev):
    """计算涨跌幅"""
    p = safe_float(price)
    pr = safe_float(prev)
    if p is None or pr is None or pr == 0:
        return None
    return round((p - pr) / pr * 100, 2)

# ─── 东方财富 A股行情 ────────────────────────────────────────
def get_em_stock(secid):
    txt = http_get(
        'https://push2.eastmoney.com/api/qt/stock/get?secid={}&fields=f43,f170,f171,f47,f48'.format(secid),
        H_EM
    )
    if not txt:
        return None
    try:
        d = json.loads(txt)
        if not d.get('data') or not d['data'].get('f43'):
            return None
        return {
            'price': d['data']['f43'] / 100,
            'pct': (d['data'].get('f170') or 0) / 100,
            'chg': (d['data'].get('f171') or 0) / 100
        }
    except:
        return None

# ─── 新浪大宗商品行情 ────────────────────────────────────────
def get_sina_futures(sym):
    """新浪期货/外盘行情接口"""
    txt = http_get('https://hq.sinajs.cn/list={}'.format(sym), H_SINA)
    if not txt:
        return None
    m = re.search(r'hq_str_' + re.escape(sym) + r'="([^"]+)"', txt)
    if not m:
        return None
    parts = m.group(1).split(',')
    return parts

def format_futures(name, parts, price_idx=0, prev_idx=8, unit='美元', unit_name=''):
    """格式化期货数据"""
    if len(parts) <= max(price_idx, prev_idx):
        return None
    price = safe_float(parts[price_idx])
    prev = safe_float(parts[prev_idx])
    pct = calc_pct(price, prev)
    if price is None:
        return None
    return {'name': name, 'price': price, 'pct': pct, 'unit': unit, 'unit_name': unit_name}

# ─── COMEX 黄金（纽约商品交易所） ───────────────────────────
def fetch_gold():
    """COMEX 黄金期货（纽约金）"""
    # 主合约：GC 主连
    parts = get_sina_futures('hf_GC')
    if parts:
        f = format_futures('COMEX黄金期货', parts, price_idx=0, prev_idx=8, unit='美元/盎司')
        if f:
            return f
    # 备用：伦敦金 XAU
    parts2 = get_sina_futures('hf_XAU')
    if parts2:
        f = format_futures('伦敦现货金', parts2, price_idx=0, prev_idx=8, unit='美元/盎司')
        if f:
            return f
    return None

# ─── COMEX 铜（伦敦金属交易所） ──────────────────────────────
def fetch_copper():
    """COMEX 铜期货（纽约商交所）+ LME 铜参考"""
    # COMEX 铜主合约 HG
    parts = get_sina_futures('hf_HG')
    if parts:
        f = format_futures('COMEX铜期货', parts, price_idx=0, prev_idx=8, unit='美分/磅')
        if f:
            return f
    # LME 铜 3个月
    parts2 = get_sina_futures('rtq铜')
    if parts2 and len(parts2) > 3:
        try:
            price = safe_float(parts2[0])
            prev = safe_float(parts2[4]) if len(parts2) > 4 else None
            pct = calc_pct(price, prev)
            return {'name': 'LME铜3个月', 'price': price, 'pct': pct, 'unit': '美元/吨', 'unit_name': '伦敦金属交易所'}
        except:
            pass
    return None

# ─── WTI + 布伦特原油 ────────────────────────────────────────
def fetch_oil():
    """WTI 原油 + 布伦特原油"""
    results = []

    # WTI 原油（美国西德克萨斯中质原油）
    parts_wti = get_sina_futures('hf_CL')
    if parts_wti:
        f = format_futures('NYMEX WTI原油', parts_wti, price_idx=0, prev_idx=8, unit='美元/桶')
        if f:
            results.append(f)

    # 布伦特原油（ICE洲际交易所）
    parts_brent = get_sina_futures('hf_BZ')
    if parts_brent:
        f = format_futures('ICE布伦特原油', parts_brent, price_idx=0, prev_idx=8, unit='美元/桶')
        if f:
            results.append(f)
    else:
        # 备用：新浪布伦特
        parts_b = get_sina_futures('hf_OIL')
        if parts_b:
            f = format_futures('布伦特原油', parts_b, price_idx=0, prev_idx=8, unit='美元/桶')
            if f:
                results.append(f)

    return results if results else None

# ─── 铁矿石（澳大利亚 & 巴西） ──────────────────────────────
def fetch_iron_ore():
    """铁矿石价格：澳大利亚粉矿（62%Fe）、巴西淡水河谷"""
    results = []

    # 新华财经铁矿石指数 / 我的钢铁
    # 我的钢铁网有 API 但需要登录，尝试公共接口
    # 大连商品交易所铁矿石期货 DCE-I
    parts_dce = get_sina_futures('hf_I')
    if parts_dce:
        f = format_futures('大商所铁矿石期货', parts_dce, price_idx=0, prev_idx=8, unit='人民币/吨')
        if f:
            results.append(f)

    # 新浪提供的新华铁矿石指数
    parts_xh = get_sina_futures('CF_IOI')
    if parts_xh and len(parts_xh) > 2:
        price = safe_float(parts_xh[0])
        prev = safe_float(parts_xh[4]) if len(parts_xh) > 4 else price
        pct = calc_pct(price, prev)
        if price:
            results.append({'name': '新华铁矿石指数', 'price': price, 'pct': pct, 'unit': '美元/吨', 'unit_name': '澳大利亚62%Fe'})

    # 澳大利亚 DBCT 铁矿石（62% Fe）
    parts_au = get_sina_futures('rtq_TI62')
    if parts_au and len(parts_au) > 1:
        price = safe_float(parts_au[0])
        prev = safe_float(parts_au[4]) if len(parts_au) > 4 else price
        pct = calc_pct(price, prev)
        if price:
            results.append({'name': '澳大利亚62%Fe粉矿', 'price': price, 'pct': pct, 'unit': '美元/吨', 'unit_name': '青岛港CFR'})

    # 巴西铁矿石（淡水河谷 reference）
    parts_br = get_sina_futures('rtq_Fe62')
    if parts_br and len(parts_br) > 1:
        price = safe_float(parts_br[0])
        prev = safe_float(parts_br[4]) if len(parts_br) > 4 else price
        pct = calc_pct(price, prev)
        if price:
            results.append({'name': '巴西淡水河谷62%Fe', 'price': price, 'pct': pct, 'unit': '美元/吨', 'unit_name': 'CFR中国'})

    return results if results else None

# ═══════════════════════════════════════════════════════════════
# 第3部分：主程序
# ═══════════════════════════════════════════════════════════════
def fmt_pct(pct):
    if pct is None:
        return '—'
    return '{}{:.2f}%'.format('+' if pct >= 0 else '', pct)

def main():
    now = datetime.now()
    ts = now.strftime("%H:%M")
    ds = now.strftime("%Y年%m月%d日")
    wk = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
    fn = now.strftime("%Y-%m-%d-%H-00")
    ha = (now.hour - 8) % 24
    ts8 = '{:02d}:{:02d}'.format(ha, now.minute)

    print('=' * 50)
    print('开始生成报告 {} {}'.format(ds, ts))
    print('=' * 50)

    # ── 新闻 ──────────────────────────────────────────────────
    print('\n[1/4] 采集新闻...')
    all_news = fetch_chinese_news()
    print('  共获取 {} 条新闻'.format(len(all_news)))

    # ── 市场数据 ────────────────────────────────────────────────
    print('\n[2/4] 采集市场数据...')
    market = {}

    # A股
    r = get_em_stock('1.000001')
    if r: market['上证指数'] = r
    r = get_em_stock('1.000300')
    if r: market['沪深300'] = r
    r = get_em_stock('0.399001')
    if r: market['深证成指'] = r

    # 恒生
    p = get_sina_futures('rt_hkHSI')
    if p and len(p) > 9:
        try:
            market['恒生指数'] = {
                'price': safe_float(p[2]),
                'pct': safe_float(p[8]),
                'unit': '点'
            }
        except: pass

    # 黄金
    gold = fetch_gold()
    if gold: market['COMEX黄金'] = gold

    # 铜
    copper = fetch_copper()
    if copper: market['铜'] = copper

    # 原油
    oils = fetch_oil()
    if oils:
        for oil in oils:
            market[oil['name']] = oil

    # 铁矿石
    iron = fetch_iron_ore()
    if iron:
        for ore in iron:
            market[ore['name']] = ore

    print('  市场数据: {}'.format(list(market.keys())))

    # ── 生成报告 ───────────────────────────────────────────────
    print('\n[3/4] 生成中文报告...')
    lines = []

    lines.append('## 📰 财经新闻汇总\n\n')
    lines.append('**日期**: {}（{}）\n'.format(ds, wk))
    lines.append('**时段**: {} - {}（北京时间）\n'.format(ts8, ts))
    lines.append('**编制**: 羊咩咩 🐏\n')
    lines.append('\n---\n\n')

    # 一、重大事件（中文标题+摘要）
    lines.append('## 一、重大事件\n\n')
    if all_news:
        for i, n in enumerate(all_news[:12], 1):
            title = n['title']
            desc = n['desc']
            src = n['source']
            link = n['link']

            lines.append('**{}. {}**\n'.format(i, title))
            if desc:
                lines.append('{}\n'.format(desc))
            lines.append('信源: {} · '.format(src))
            if link:
                lines.append('[查看原文]({})\n'.format(link))
            else:
                lines.append('\n')
            lines.append('\n')
    else:
        lines.append('暂无新闻数据\n\n')

    lines.append('\n---\n\n')

    # 二、市场摘要
    lines.append('## 二、市场摘要\n\n')

    # 股指
    indices = [k for k in market if any(x in k for x in ['指数', '沪深', '深证', '上证'])]
    if indices:
        lines.append('### 📈 全球股指\n\n')
        for name in indices:
            d = market[name]
            p = safe_float(d.get('price'))
            pct = safe_float(d.get('pct'))
            if p:
                if 'unit' in d:
                    lines.append('{}：{:.2f}（{}）\n'.format(name, p, fmt_pct(pct)))
                else:
                    lines.append('{}：{:.2f}（{}）\n'.format(name, p, fmt_pct(pct)))
        lines.append('\n')

    # 黄金
    if 'COMEX黄金' in market:
        d = market['COMEX黄金']
        lines.append('### 🥇 黄金（COMEX纽约金）\n\n')
        p = safe_float(d.get('price'))
        pct = safe_float(d.get('pct'))
        lines.append('COMEX黄金期货：{}{}/盎司（{}）\n'.format(
            '' if p is None else '${:.2f}'.format(p),
            d.get('unit', ''),
            fmt_pct(pct)
        ))
        lines.append('数据来源：纽约商品交易所（COMEX）| 新浪财经\n\n')

    # 铜（LME）
    if '铜' in market or 'COMEX铜' in market:
        d = market.get('铜') or market.get('COMEX铜')
        if d:
            lines.append('### 🔩 铜（LME伦敦金属交易所）\n\n')
            p = safe_float(d.get('price'))
            pct = safe_float(d.get('pct'))
            lines.append('{}：{}{}（{}）\n'.format(
                d.get('name', 'LME铜'),
                '' if p is None else '${:.2f}'.format(p),
                d.get('unit', ''),
                fmt_pct(pct)
            ))
            lines.append('数据来源：伦敦金属交易所（LME）| 新浪财经\n\n')

    # 原油
    oil_keys = [k for k in market if '原油' in k or '布伦特' in k or 'WTI' in k]
    if oil_keys:
        lines.append('### 🛢️ 原油\n\n')
        for name in ['NYMEX WTI原油', 'ICE布伦特原油', '布伦特原油']:
            if name in market:
                d = market[name]
                p = safe_float(d.get('price'))
                pct = safe_float(d.get('pct'))
                lines.append('{}：{}{}（{}）\n'.format(
                    name,
                    '' if p is None else '${:.2f}'.format(p),
                    d.get('unit', ''),
                    fmt_pct(pct)
                ))
        lines.append('数据来源：NYMEX（WTI）/ ICE（布伦特）| 新浪财经\n\n')

    # 铁矿石
    iron_keys = [k for k in market if '铁矿' in k or 'Fe' in k or '铁矿石' in k]
    if iron_keys:
        lines.append('### ⚙️ 金属 — 铁矿石\n\n')
        for name in iron_keys:
            d = market[name]
            p = safe_float(d.get('price'))
            pct = safe_float(d.get('pct'))
            unit_name = d.get('unit_name', '')
            lines.append('{}（{}）：{}{}（{}）\n'.format(
                d.get('name', name),
                unit_name,
                '' if p is None else '${:.2f}'.format(p),
                d.get('unit', ''),
                fmt_pct(pct)
            ))
        lines.append('数据来源：澳大利亚/巴西现货指数 | 新浪财经\n\n')

    # 页脚
    lines.append('\n---\n')
    lines.append('*数据截至北京时间{} | 内容仅供参考，投资有风险，入市需谨慎*\n'.format(ts))
    lines.append('*由羊咩咩 🐏 自动生成*\n')

    desp = ''.join(lines)
    print('  报告生成完毕，{} 字符'.format(len(desp)))

    # ── 推送 ──────────────────────────────────────────────────
    print('\n[4/4] 推送微信...')
    title = '财经新闻汇总 {} {}'.format(ds, ts)
    url = 'https://sctapi.ftqq.com/{}.send'.format(SENDKEY)
    data = urllib.parse.urlencode({'title': title, 'desp': desp}, encoding='utf-8').encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print('  推送结果: code={} {}'.format(
                result.get('code'),
                result.get('message', '')
            ))
    except Exception as e:
        print('  推送失败: {}'.format(e))

    # 本地保存
    try:
        reports_dir = '/tmp/reports' if os.path.exists('/tmp') else r'C:\Users\84351\.qclaw\workspace\reports'
        os.makedirs(reports_dir, exist_ok=True)
        fp = os.path.join(reports_dir, fn + '.md')
        with open(fp, 'w', encoding='utf-8') as f:
            f.write('# 财经新闻汇总 - {} {}\n\n'.format(ds, ts))
            f.write(desp)
        print('  已保存本地: {}'.format(fp))
    except Exception as e:
        print('  保存失败: {}'.format(e))

if __name__ == '__main__':
    main()
