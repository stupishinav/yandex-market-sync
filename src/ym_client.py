import requests
import logging

logger = logging.getLogger(__name__)

class YandexMarketClient:
    def __init__(self, api_key, campaign_id, warehouse_id, business_id):
        self.api_key = api_key
        self.campaign_id = campaign_id
        self.warehouse_id = warehouse_id

    def update_stock(self, stocks):
        url = f"https://api.partner.market.yandex.ru/v2/campaigns/{self.campaign_id}/offers/stocks"
        payload = {
            "skus": [
                {"sku": item['offer_id'], "warehouseId": self.warehouse_id, "items": [{"count": item['stock'], "type": "FIT"}]}
                for item in stocks
            ]
        }
        headers = {'Authorization': f'OAuth {self.api_key}', 'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Отправлено {len(stocks)} товаров")
        return response

    def update_prices(self, payload):
        url = f"https://api.partner.market.yandex.ru/v2/campaigns/{self.campaign_id}/offer-prices/updates"
        headers = {'Authorization': f'OAuth {self.api_key}', 'Content-Type': 'application/json'}
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Отправлено цен: {len(payload.get('prices', []))}")
        return response
