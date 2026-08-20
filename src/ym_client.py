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
        
        skus = []
        for item in stocks:
            try:
                sku = {
                    "sku": str(item['offer_id']).strip(),
                    "warehouseId": str(self.warehouse_id),
                    "items": [
                        {
                            "count": int(float(str(item['stock']).replace(',', '.'))),
                            "type": "FIT"
                        }
                    ]
                }
                skus.append(sku)
            except Exception as e:
                logger.error(f"Ошибка в данных товара {item.get('offer_id')}: {e}")
                continue
        
        payload = {"skus": skus}
        
        headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
        logger.info(f"📤 Отправка остатков (товаров: {len(skus)})")
        
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

    def update_prices(self, prices):
        """
        Обновление цен
        Принимает список товаров с ценами
        """
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-prices/updates"
        
        # Проверяем, что пришли данные
        if not prices:
            logger.error("❌ Нет данных для обновления цен!")
            return None
        
        # ФОРМИРУЕМ ПРАВИЛЬНЫЙ PAYLOAD ДЛЯ ЦЕН
        # Документация Яндекса: https://yandex.ru/dev/market/partner-api/doc/
        price_entries = []
        for item in prices:
            try:
                price_entry = {
                    "id": str(item['offer_id']).strip(),
                    "price": {
                        "value": str(item['price']).replace(',', '.'),
                        "currencyId": "RUR"
                    }
                }
                # Если есть старая цена (для скидки)
                if 'old_price' in item and item['old_price']:
                    price_entry['price']['discountBase'] = str(item['old_price']).replace(',', '.')
                price_entries.append(price_entry)
            except Exception as e:
                logger.error(f"Ошибка в данных товара {item.get('offer_id')}: {e}")
                continue
        
        # Формируем финальный payload
        payload = {"prices": price_entries}
        
        logger.info(f"📤 Отправка цен (товаров: {len(price_entries)})")
        
        # ОТЛАДКА: показываем первые 2 товара в запросе
        if len(price_entries) > 0:
            logger.info(f"🔍 Пример товара в запросе: {price_entries[0]}")
        if len(price_entries) > 1:
            logger.info(f"🔍 Пример товара в запросе: {price_entries[1]}")
        
        headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
        
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
