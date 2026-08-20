"""
Клиент для работы с API Яндекс.Маркета
"""
import requests
import logging
import time

logger = logging.getLogger(__name__)

class YandexMarketClient:
    def __init__(self, api_key: str, campaign_id: str, warehouse_id: str, business_id: str):
        self.api_key = api_key
        self.campaign_id = campaign_id
        self.warehouse_id = warehouse_id
        self.business_id = business_id
        self.base_url = "https://api.partner.market.yandex.ru/v2"

    def update_stock(self, stocks):
        """Обновление остатков методом PUT"""
        if not stocks:
            logger.error("Нет данных для обновления остатков!")
            return None

        # 1. Правильный эндпоинт для ОСТАТКОВ
        url = f"{self.base_url}/campaigns/{self.campaign_id}/offers/stocks"
        
        # 2. Правильный заголовок для ОСТАТКОВ (Api-Key)
        headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }

        # Отправляем пачками по 500
        chunk_size = 500
        chunks = [stocks[i:i + chunk_size] for i in range(0, len(stocks), chunk_size)]
        logger.info(f"Разбивка {len(stocks)} остатков на {len(chunks)} пачек")

        for idx, chunk in enumerate(chunks):
            skus = []
            for item in chunk:
                try:
                    skus.append({
                        "sku": str(item['offer_id']).strip(),
                        "warehouseId": str(self.warehouse_id),
                        "items": [{"count": int(float(str(item['stock']).replace(',', '.'))), "type": "FIT"}]
                    })
                except Exception as e:
                    logger.error(f"Ошибка в данных товара {item.get('offer_id')}: {e}")
                    continue
            payload = {"skus": skus}
            try:
                # 3. Правильный метод для ОСТАТКОВ - PUT
                response = requests.put(url, json=payload, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Пачка остатков {idx+1}/{len(chunks)} отправлена")
                else:
                    logger.error(f"Ошибка в пачке {idx+1}: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Ошибка запроса: {e}")
            time.sleep(0.5)
        return True

    def update_prices(self, prices):
        """Обновление цен на уровне бизнеса"""
        if not prices:
            logger.error("Нет данных для обновления цен!")
            return None

        # 1. Правильный эндпоинт для ЦЕН (бизнес-уровень)
        url = f"{self.base_url}/businesses/{self.business_id}/offer-prices/updates"
        
        # 2. Правильный заголовок для ЦЕН (Authorization)
        headers = {
            'Authorization': f'OAuth {self.api_key}',
            'Content-Type': 'application/json'
        }

        # Отправляем пачками по 500
        chunk_size = 500
        chunks = [prices[i:i + chunk_size] for i in range(0, len(prices), chunk_size)]
        logger.info(f"Разбивка {len(prices)} цен на {len(chunks)} пачек")

        for idx, chunk in enumerate(chunks):
            offers = []
            for item in chunk:
                try:
                    price_value = round(float(item['price']), 2)
                    offers.append({
                        "offerId": str(item['offer_id']).strip(),
                        "price": {"value": price_value, "currencyId": "RUR"}
                    })
                except Exception as e:
                    logger.error(f"Ошибка в данных товара {item.get('offer_id')}: {e}")
                    continue
            payload = {"offers": offers}
            try:
                # 3. Правильный метод для ЦЕН - POST
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    logger.info(f"Пачка цен {idx+1}/{len(chunks)} отправлена")
                else:
                    logger.error(f"Ошибка в пачке {idx+1}: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Ошибка запроса: {e}")
            time.sleep(0.5)
        return True
