# -*- coding: utf-8 -*-
"""
财经新闻汇总 - GitHub Actions 版本
在 GitHub Actions 上运行，可访问外网获取真实数据
"""
import urllib.request
import urllib.parse
import json
import sys
import os
import re
from datetime import datetime

def http_get(url, headers=None, timeout=15):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  [网络错误] {url}: {e}")
        return None

H_SINA = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://finance.sina.com.cn'
}
H_EM = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://finance.eastmoney.com'
}
H_REUTERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/xml'
}

SENDKEY = os.environ.get('SERVERCHAN_SENDKEY', 'SCT328691TqGJDJfpEgA5noR3meGMVrKJ7')

# ===== 第1部分：获取真实国际新闻 =====
def fetch_reuters_news():
    """从 Reuters RSS 获取最新国际财经新闻（备用：FT/CNBC）"""
    news = []
    # Reuters 在 GitHub Actions 上可能被墙，用多个备用源
    sources = [
        ('https://feeds.reuters.com/reuters/businessNews', 'Reuters'),
        ('https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines', 'MarketWatch'),
        ('https://cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
    ]
    for feed_url, src_name in sources:
        feed = http_get(feed_url, H_REUTERS)
        if not feed:
            continue
        items = re.findall(r'<item>(.*?)</item>', feed, re.DOTALL)
        for item in items[:10]:
            title_m = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item, re.DOTALL)
            link_m = re.search(r'<link>(.*?)</link>', item)
            if title_m:
                title = title_m.group(1).strip()
                link = link_m.group(1).strip() if link_m else ''
                if title and len(title) > 10 and not any(k in title.lower() for k in ['video', 'press release', 'podcast']):
                    news.append({'title': title, 'source': src_name, 'link': link})
        if news:
            print("  {} ({} 条)".format(src_name, len(news)))
            break
    return news

def fetch_bbc_news():
    """从 BBC Business RSS 获取最新新闻"""
    news = []
    feed = http_get('https://feeds.bbci.co.uk/news/business/rss.xml', H_REUTERS)
    if feed:
        items = re.findall(r'<item>(.*?)</item>', feed, re.DOTALL)
        for item in items[:10]:
            title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            link_m = re.search(r'<link>(.*?)</link>', item)
            if title_m:
                title = title_m.group(1).strip()
                link = link_m.group(1).strip() if link_m else ''
                if title and len(title) > 10:
                    news.append({'title': title, 'source': 'BBC', 'link': link})
    return news

def fetch_bloomberg_news():
    """从 Bloomberg RSS 获取最新新闻"""
    news = []
    feed = http_get('https://feeds.bloomberg.com/markets/news.rss', H_REUTERS)
    if feed:
        items = re.findall(r'<item>(.*?)</item>', feed, re.DOTALL)
        for item in items[:10]:
            title_m = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            if title_m:
                title = title_m.group(1).strip().replace('<![CDATA[','').replace(']]>','')
                if title and len(title) > 10:
                    news.append({'title': title, 'source': 'Bloomberg', 'link': ''})
    return news

# ===== 第2部分：获取真实市场数据 =====
def get_em_stock(secid):
    """东方财富股票数据"""
    txt = http_get(f'https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f170,f171,f47,f48')
    if not txt: return None
    try:
        d = json.loads(txt)
        if not d.get('data') or not d['data'].get('f43'): return None
        price = d['data']['f43'] / 100
        pct = (d['data'].get('f170') or 0) / 100
        chg = (d['data'].get('f171') or 0) / 100
        return {'price': price, 'pct': pct, 'chg': chg}
    except: return None

def get_sina_quote(sym):
    """新浪财经报价"""
    txt = http_get(f'https://hq.sinajs.cn/list={sym}', H_SINA)
    if not txt: return None
    m = re.search(r'hq_str_' + re.escape(sym) + r'="([^"]+)"', txt)
    if not m: return None
    p = m.group(1).split(',')
    return p

# ===== 主程序 =====
def main():
    now = datetime.now()
    ts = now.strftime("%H:%M")
    ds = now.strftime("%Y年%m月%d日")
    wk = ["周一","周二","周三","周四","周五","周六","周日"][now.weekday()]
    fn = now.strftime("%Y-%m-%d-%H-00")
    ha = (now.hour - 8) % 24
    ts8 = f"{ha:02d}:{now.minute:02d}"

    print("=" * 40)
    print(f"开始生成报告 {ds} {ts}")
    print("=" * 40)

    # 获取新闻
    print("\n[1/4] 获取国际新闻...")
    reuters_news = fetch_reuters_news()
    bbc_news = fetch_bbc_news()
    bloomberg_news = fetch_bloomberg_news()
    print(f"  Reuters: {len(reuters_news)} 条")
    print(f"  BBC: {len(bbc_news)} 条")
    print(f"  Bloomberg: {len(bloomberg_news)} 条")

    # 获取市场数据
    print("\n[2/4] 获取市场数据...")
    market = {}

    # A股
    r = get_em_stock('1.000001')
    if r: market['上证指数'] = r
    r = get_em_stock('1.000300')
    if r: market['沪深300'] = r

    # 恒生
    p = get_sina_quote('rt_hkHSI')
    if p and len(p) > 8:
        try:
            market['恒生指数'] = {'price': float(p[2]), 'pct': float(p[8]), 'chg': float(p[8])}
        except: pass

    # 美股（新浪 gb_ 接口：p[1]=现价, p[2]=涨跌额, p[3]=涨跌幅%, p[4]=昨收）
    for sym, name in [('gb_aapl','苹果'),('gb_ndx','纳斯达克100'),('gb_dji','道琼斯工业')]:
        p = get_sina_quote(sym)
        if p and len(p) > 4:
            try:
                price = float(p[1])
                # p[3] 是涨跌幅（如 "-1.23"），但有时字段错位，用昨收价计算兜底
                try:
                    pct = float(p[3])
                    # 如果 pct 绝对值 > 50，说明字段错位了，用昨收价计算
                    if abs(pct) > 50:
                        raise ValueError("field mismatch")
                except (ValueError, IndexError):
                    prev = float(p[4]) if p[4] else price
                    pct = round((price - prev) / prev * 100, 2) if prev else 0.0
                market[name] = {'price': price, 'pct': pct}
            except Exception as ex:
                print("  [美股解析失败] {}: {}".format(name, ex))

    # 黄金
    p = get_sina_quote('hf_GC')
    if p and len(p) > 10 and p[1]:
        try:
            price = float(p[1])
            prev = float(p[8]) if p[8] else price
            pct = round((price - prev) / prev * 100, 2)
            market['黄金期货'] = {'price': price, 'pct': pct}
        except: pass

    # WTI原油
    p = get_sina_quote('hf_CL')
    if p and len(p) > 10 and p[1]:
        try:
            price = float(p[1])
            prev = float(p[8]) if p[8] else price
            pct = round((price - prev) / prev * 100, 2)
            market['WTI原油'] = {'price': price, 'pct': pct}
        except: pass

    print(f"  获取到 {len(market)} 项市场数据")

    # 合并新闻
    all_news = []
    seen = set()
    for n in reuters_news + bbc_news + bloomberg_news:
        key = n['title'][:30]
        if key not in seen:
            seen.add(key)
            all_news.append(n)

    print(f"\n[3/4] 共 {len(all_news)} 条新闻")

    # ===== 生成报告 =====
    title = f"财经新闻汇总 {ts}"

    lines = []
    lines.append(f"## 📰 财经新闻汇总\n")
    lines.append(f"**日期**: {ds}（{wk}）\n")
    lines.append(f"**时段**: {ts8}-{ts}（过去8小时）\n")
    lines.append(f"**编制**: 羊咩咩 🐏\n")
    lines.append(f"**说明**: 市场数据来源东方财富/新浪财经；新闻来源 Reuters/BBC/Bloomberg\n")
    lines.append("\n---\n")
    lines.append("\n## 一、重大事件\n")

    for i, n in enumerate(all_news[:12], 1):
        src_link = f" — 信源: {n['source']}"
        if n['link']:
            src_link += f" [原文链接]({n['link']})"
        lines.append(f"**{i}. {n['title']}**{src_link}\n\n")

    lines.append("---\n")
    lines.append("\n## 二、市场摘要\n")
    lines.append("\n### 📈 股指情况\n\n")

    # 按顺序输出
    for name in ['道琼斯工业','纳斯达克100','苹果','上证指数','沪深300','恒生指数']:
        if name in market:
            d = market[name]
            try:
                price = float(d['price'])
                pct = float(d['pct'])
                pct_str = "{}{:.2f}%".format('+' if pct >= 0 else '', pct)
                lines.append("{}：{:.2f} ({})\n".format(name, price, pct_str))
            except Exception as ex:
                lines.append("{}：数据解析异常\n".format(name))

    lines.append("\n### 🥇 黄金市场\n\n")
    if '黄金期货' in market:
        d = market['黄金期货']
        pct_str = f"{'+' if d['pct']>=0 else ''}{d['pct']:.2f}%"
        lines.append(f"COMEX黄金期货：${d['price']:.2f}/盎司 ({pct_str}) — 新浪财经\n")
    else:
        lines.append("COMEX黄金期货：暂无法获取\n")

    lines.append("\n### 💱 外汇市场\n\n")
    lines.append("（外汇数据暂不可用）\n")

    lines.append("\n### 📊 债券市场\n\n")
    lines.append("（债券数据暂不可用）\n")

    lines.append("\n### 🛢️ 原油市场\n\n")
    if 'WTI原油' in market:
        d = market['WTI原油']
        pct_str = f"{'+' if d['pct']>=0 else ''}{d['pct']:.2f}%"
        lines.append(f"WTI原油：${d['price']:.2f}/桶 ({pct_str}) — 新浪财经\n")
    else:
        lines.append("WTI原油：暂无法获取\n")
    lines.append("布伦特原油：暂无法获取\n")

    lines.append("\n### ⚙️ 金属市场\n\n")
    lines.append("（金属数据暂不可用）\n")

    lines.append("\n---\n")
    lines.append(f"*数据截至北京时间{ts} | 投资有风险，入市需谨慎*\n")

    desp = ''.join(lines)
    print(f"\n[4/4] 生成报告，共 {len(desp)} 字符")

    # ===== 保存本地 =====
    reports_dir = '/tmp/reports' if os.path.exists('/tmp') else r'C:\Users\84351\.qclaw\workspace\reports'
    os.makedirs(reports_dir, exist_ok=True)
    fp = os.path.join(reports_dir, f"{fn}.md")
    try:
        with open(fp, "w", encoding="utf-8") as f:
            f.write(f"# 财经新闻汇总 - {ds} {ts}\n\n")
            f.write(desp)
        print(f"已保存: {fp}")
    except Exception as e:
        print(f"保存失败: {e}")

    # ===== 推送 =====
    url = f"https://sctapi.ftqq.com/{SENDKEY}.send"
    data = urllib.parse.urlencode({"title": title, "desp": desp}, encoding='utf-8').encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            print(f"推送结果: {result}")
    except Exception as e:
        print(f"推送失败: {e}")

if __name__ == '__main__':
    main()
