import requests
from bs4 import BeautifulSoup
import re

URL = 'https://tradelinesupply.com/pricing/'

def scrape_and_group_tradelines():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all('tr')

    buckets = {
        '0-2500': [],
        '2501-5000': [],
        '5001-10000': [],
        '10001+': []
    }

    for row in rows:
        try:
            product_td = row.find('td', class_='product_data')
            price_td = row.find('td', class_='product_price')

            if not product_td or not price_td:
                continue

            bank_name = product_td.get('data-bankname', '').strip()
            credit_limit_raw = product_td.get('data-creditlimit', '').strip().replace('$', '').replace(',', '')
            credit_limit = int(credit_limit_raw) if credit_limit_raw.isdigit() else 0
            date_opened = product_td.get('data-dateopened', '').strip()
            purchase_by = product_td.get('data-purchasebydate', '').strip()
            reporting_period = product_td.get('data-reportingperiod', '').strip()
            availability = product_td.get('data-availability', '').strip()

            price_text = price_td.get_text(strip=True)
            price_match = re.search(r"\$\s?(\d+(?:,\d{3})*(?:\.\d{2})?)", price_text)
            if not price_match:
                continue
            base_price = float(price_match.group(1).replace(",", ""))
            final_price = base_price + 100

            formatted = (
                f"🏦 Bank: {bank_name}\n"
                f"💳 Credit Limit: ${credit_limit:,}\n"
                f"📅 Date Opened: {date_opened}\n"
                f"🛒 Purchase Deadline: {purchase_by}\n"
                f"📈 Reporting Period: {reporting_period}\n"
                f"📦 Availability: {availability}\n"
                f"💰 Price: ${final_price:,.2f}"
            )

            item = {
                'bank': bank_name,
                'text': formatted,
                'price': final_price,
                'limit': credit_limit
            }

            if credit_limit <= 2500:
                buckets['0-2500'].append(item)
            elif credit_limit <= 5000:
                buckets['2501-5000'].append(item)
            elif credit_limit <= 10000:
                buckets['5001-10000'].append(item)
            else:
                buckets['10001+'].append(item)

        except Exception:
            continue

    for key in buckets:
        buckets[key] = sorted(buckets[key], key=lambda x: x['price'])

    return buckets

def export_tradelines_to_html(return_string=False):
    buckets = scrape_and_group_tradelines()

    html_parts = [
        "<html><head><meta charset='UTF-8'>",
        "<title>Tradelines Catalog</title>",
        "<style>",
        "body { font-family: 'Segoe UI', sans-serif; background: #f4f6f8; padding: 30px; margin: 0; color: #333; }",
        "h1 { font-size: 24px; border-left: 5px solid #4a90e2; padding-left: 10px; margin-top: 40px; margin-bottom: 20px; }",
        ".grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }",
        ".card { background: #fff; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); padding: 20px; transition: transform 0.2s ease; display: flex; flex-direction: column; }",
        ".card:hover { transform: translateY(-4px); }",
        ".bank-name { font-size: 18px; font-weight: 600; margin-bottom: 8px; color: #2c3e50; }",
        ".detail { font-size: 14px; margin: 4px 0; color: #555; }",
        ".price { font-size: 16px; font-weight: bold; color: #27ae60; margin-top: 10px; }",
        "</style></head><body>"
    ]

    for category, tradelines in buckets.items():
        html_parts.append(f"<h1>Credit Limit Range: {category.replace('-', ' – ')}</h1>")
        html_parts.append("<div class='grid'>")
        for item in tradelines:
            html_parts.append("<div class='card'>")
            html_parts.append(f"<div class='bank-name'>{item['bank']}</div>")
            for line in item['text'].split('\n'):
                if 'Price' in line:
                    html_parts.append(f"<div class='price'>{line.split(': ')[1]}</div>")
                else:
                    html_parts.append(f"<div class='detail'>{line}</div>")
            html_parts.append("</div>")
        html_parts.append("</div>")  # close grid

    html_parts.append("</body></html>")
    return "\n".join(html_parts)
