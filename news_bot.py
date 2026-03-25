python
#!/usr/bin/env python3
"""
财经新闻汇总 - GitHub Actions 版
"""

import os
import requests
from datetime import datetime

SERVERCHAN_SENDKEY = os.getenv("SERVERCHAN_SENDKEY", "")

def fetch_rss_news(url, source_name, max_items=5):
    try:
        import xml.etree.ElementTree as ET
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0"
        })
        resp.encoding = 'utf-8'
        root = ET.fromstring(resp.content)
        items = []
        channel = root.find('channel')
        if channel is not None:
            for item in channel.findall('item')[:max_items]:
                title = item.find('title')
                desc = item.find('description')
                items.append({
                    "title": title.text if title is not None else "",
                    "description": desc.text if desc is not None else "",
                    "source": source_name
                })
        return items
    except Exception as e:
        print(f"获取 {source_name} 失败: {e}")
        return []
def fetch_all_news():
    sources = {
        "Reuters": "https://www.reutersagency.com/feed/?best-regions=world&post_type=best",
        "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    }
    all_news = []
    for source, url in sources.items():
        news = fetch_rss_news(url, source)
        all_news.extend(news)
    seen = set()
    unique = []
    for item in all_news:
        if item["title"] and item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    return un
  ique[:12]

def fetch_yahoo_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        result = data.get("chart", {}).get("result", [{}])[0]
        prices = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        if len(prices) >= 2:
            today = prices[-1]
            yesterday = prices[-2]
            change = today - yesterday
            change_pct = (change / yesterday) * 100
            return {"price": today, "change": change, "change_pct": change_pct}
    except:
        pass
    return {}

def fetch_market_data():
    indices = {"道琼斯": "^DJI", "标普500": "^GSPC", "纳斯达克": "^IXIC", "恒生指数": "^HSI"}
    commodities = {"黄金": "GC=F", "布伦特原油": "BZ=F"}
    data = {"indices": {}, "commodities": {}}
    for name, symbol in indices.items():
        result = fetch_yahoo_data(symbol)
        if result:
            data["indices"][name] = result
    for name, symbol in commodities.items():
        result = fetch_yahoo_data(symbol)
        if result:
            data["commodities"][name] = result
    return data
def generate_report(news, market):
    now = datetime.now()
    report = f"📰 财经新闻汇总 {now.strftime('%m-%d %H:%M')}\n\n【重大事件】\n"
    for i, item in enumerate(news[:10], 1):
        title = item.get("title", "")[:50]
        source = item.get("source", "")
        report += f"{i}. {title}... ({source})\n"
    report += "\n【股指情况】\n"
    for name, data in market.get("indices", {}).items():
        sign = "+" if data["change"] >= 0 else ""
        report += f"{name}: {data['price']:.2f} ({sign}{data['change_pct']:.2f}%)\n"
    report += "\n【大宗商品】\n"
    for name, data in market.get("commodities", {}).items():
        sign = "+" if data["change"] >= 0 else ""
        unit = "美元/盎司" if "黄金" in name else "美元/桶"
        report += f"{name}: {data['price']:.2f}{unit} ({sign}{data['change']:.2f})\n"
    report += "\n数据来源: Reuters/BBC/Yahoo Finance"
    return report

def send_wechat(title, content):
    if not SERVERCHAN_SENDKEY:
        print("未配置 SendKey")
        return False
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_SENDKEY}.send"
    data = {"title": title, "desp": content.replace("\n", "\n\n")}
    try:
        resp = requests.post(url, data=data, timeout=10)
        return resp.json().get("code") == 0
    except Exception as e:
        print(f"推送失败: {e}")
        return False

def main():
    print("开始抓取...")
    news = fetch_all_news()
    print(f"获取 {len(news)} 条新闻")
    market = fetch_market_data()
    print("市场数据获取完成")
    report = generate_report(news, market)
    with open("report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    title = f"📰 财经新闻 {datetime.now().strftime('%m-%d %H:%M')}"
    send_wechat(title, report)
    print("完成！")
    print(report)

if __name__ == "__main__":
    main()
