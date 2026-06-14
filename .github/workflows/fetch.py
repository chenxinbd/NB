import requests, json, re, os, time
from bs4 import BeautifulSoup

BASE_URL = os.environ.get("UPSTREAM_URL", "http://localhost")
SEARCHMORE_URL = BASE_URL + "/site/price/searchmore"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.38",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

session = requests.Session()
session.headers.update(HEADERS)

def fetch_all_products():
    all_products = []
    page = 1
    total = 9999
    while (page - 1) * 20 < total:
        payload = {"key": "", "cate": "", "instock": "0", "price": "0"}
        resp = session.post(f"{SEARCHMORE_URL}/{page}", data=payload, timeout=30)
        raw = resp.json()
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        html = data["html"]
        if page == 1:
            match = re.search(r'total\s*=\s*(\d+)', html)
            if match:
                total = int(match.group(1))
        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("li", class_="list-chanpin")
        if not items:
            break
        for item in items:
            try:
                name_tag = item.find("h4")
                if not name_tag:
                    continue
                name = name_tag.get_text(strip=True)
                stock_tag = item.find("p", class_="kucun")
                stock_text = stock_tag.get_text(strip=True) if stock_tag else "库存：暂缺"
                stock = stock_text.replace("库存：", "").strip()
                price_tag = item.find("span", class_="xianjia")
                price_text = price_tag.get_text(strip=True) if price_tag else "0"
                fan_price = float(re.search(r'[\d.]+', price_text).group())
                img_tag = item.find("img", class_="img-rounded")
                img_url = ""
                if img_tag:
                    img_url = img_tag.get("data") or img_tag.get("src", "")
                    if img_url.startswith("/"):
                        img_url = BASE_URL + img_url
                all_products.append({
                    "name": name,
                    "stock": stock,
                    "fan_price": fan_price,
                    "image": img_url
                })
            except:
                continue
        page += 1
        time.sleep(0.5)
    return all_products

def calc_sell_price(fan_price):
    if fan_price >= 1500:
        return None
    rules_str = os.environ.get("PRICE_RULES", "")
    rules = []
    for r in rules_str.split(";"):
        if r:
            limit, add = r.split(",")
            rules.append((float(limit), float(add)))
    for limit, add in rules:
        if fan_price < limit:
            return fan_price + add
    last_limit, last_add = rules[-1]
    return fan_price + last_add + ((fan_price - (last_limit - 10)) // 100) * 10

if __name__ == "__main__":
    print("正在抓取商品...")
    products = fetch_all_products()
    print(f"共抓取 {len(products)} 个商品")
    output = []
    for p in products:
        sell_price = calc_sell_price(p["fan_price"])
        if sell_price is None:
            continue
        if p["fan_price"] < 7:
            continue
        output.append({
            "name": p["name"],
            "stock": p["stock"],
            "price": round(sell_price, 2),
            "image": p["image"] if p["image"] else ""
        })
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"完成，共 {len(output)} 个商品可供展示")
