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
        "<style>body{font-family:Arial,sans-serif;padding:20px;}h1{color:#222;border-bottom:2px solid #eee;}details{margin-bottom:15px;border:1px solid #ddd;border-radius:5px;padding:10px;background:#f7f7f7;}summary{font-weight:bold;cursor:pointer;} .tradeline{padding:10px 15px;border:1px solid #ccc;margin-top:10px;border-radius:6px;background:#fff;box-shadow:0 2px 5px rgba(0,0,0,0.05);} .tradeline p{margin:6px 0;line-height:1.5;}</style>",
        "</head><body>"
    ]

    for category, tradelines in buckets.items():
        html_parts.append(f"<h1>💳 Credit Limit: {category.replace('-', ' – ')}</h1>")
        banks = sorted(set(t['bank'] for t in tradelines))
        for bank in banks:
            html_parts.append(f"<details><summary>🏦 {bank}</summary>")
            for t in [x for x in tradelines if x['bank'] == bank]:
                html_parts.append("<div class='tradeline'>")
                html_parts.append("<p>" + t['text'].replace("\n", "<br>") + "</p>")
                html_parts.append("</div>")
            html_parts.append("</details>")

    html_parts.append("</body></html>")
    return "\n".join(html_parts)
