"""
Клиент для работы с API Яндекс.Маркета
Использует API-Key токен (формат ACMA:...)
"""

import requests
import logging

logger = logging.getLogger(__name__)


class YandexMarketClient:
    def __init__(self, api_key: str, campaign_id: str, warehouse_id: str, business_id: str):
        self.api_key = api_key
        self.campaign_id = campaign_id
        self.warehouse_id = warehouse_id
        self.business_id = business_id
        self.base_url = "https://api.partner.market.yandex.ru/v2"

    def update_stock(self, stocks):
        """Обновление остатков"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offers/stocks"
        
        payload = {
            "skus": [
                {
                    "sku": item['offer_id'],
                    "warehouseId": self.warehouse_id,
                    "items": [{"count": int(item['stock']), "type": "FIT"}]
                }
                for item in stocks
            ]
        }
        
        # ВАЖНО! Для API-Key используется заголовок Api-Key
        headers = {
            'Api-Key': self.api_key,  # ← ЭТО КЛЮЧЕВОЕ ИЗМЕНЕНИЕ!
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📤 Отправка остатков (товаров: {len(stocks)})")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                logger.info("✅ Остатки успешно отправлены")
            else:
                logger.error(f"❌ Ошибка: {response.status_code}")
                logger.error(f"Ответ: {response.text}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return None

    def update_prices(self, payload):
        """Обновление цен"""
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-prices/updates"
        
        # ВАЖНО! Для API-Key используется заголовок Api-Key
        headers = {
            'Api-Key': self.api_key,  # ← ЭТО КЛЮЧЕВОЕ ИЗМЕНЕНИЕ!
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📤 Отправка цен (товаров: {len(payload.get('prices', []))})")
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                logger.info("✅ Цены успешно отправлены")
            else:
                logger.error(f"❌ Ошибка: {response.status_code}")
                logger.error(f"Ответ: {response.text}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка запроса: {e}")
            return None
