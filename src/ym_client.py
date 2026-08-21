"""
Клиент для работы с API Яндекс.Маркета
Использует API-Key токен (формат ACMA:...)
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
        """
        Обновление остатков - ИСПОЛЬЗУЕТ PUT
        """
        if not stocks:
            logger.error("❌ Нет данных для обновления остатков!")
            return None

        url = f"{self.base_url}/campaigns/{self.campaign_id}/offers/stocks"
        
        headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }

        chunk_size = 500
        total_items = len(stocks)
        chunks = [stocks[i:i + chunk_size] for i in range(0, total_items, chunk_size)]
        
        logger.info(f"📦 Разбивка {total_items} остатков на {len(chunks)} пачек по {chunk_size} шт.")
        
        all_responses = []
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"📤 Отправка пачки {idx + 1}/{len(chunks)} (товаров: {len(chunk)})")
            
            skus = []
            for item in chunk:
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
            
            try:
                response = requests.put(url, json=payload, headers=headers)
                if response.status_code == 200:
                    logger.info(f"✅ Пачка {idx + 1}/{len(chunks)} успешно отправлена")
                else:
                    logger.error(f"❌ Ошибка в пачке {idx + 1}/{len(chunks)}: {response.status_code}")
                    logger.error(f"Ответ: {response.text}")
                all_responses.append(response)
            except Exception as e:
                logger.error(f"❌ Ошибка запроса для пачки {idx + 1}: {e}")
                all_responses.append(None)
            
            if idx < len(chunks) - 1:
                time.sleep(0.3)
        
        for resp in reversed(all_responses):
            if resp and resp.status_code == 200:
                return resp
        return None

    def update_prices(self, prices):
        """
        Обновление цен - ИСПОЛЬЗУЕТ Api-Key
        """
        if not prices:
            logger.error("❌ Нет данных для обновления цен!")
            return None

        url = f"{self.base_url}/businesses/{self.business_id}/offer-prices/updates"
        
        # ✅ ПРАВИЛЬНО: Api-Key для обоих методов
        headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }

        chunk_size = 500
        total_items = len(prices)
        chunks = [prices[i:i + chunk_size] for i in range(0, total_items, chunk_size)]
        
        logger.info(f"📦 Разбивка {total_items} цен на {len(chunks)} пачек по {chunk_size} шт.")
        
        all_responses = []
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"📤 Отправка пачки {idx + 1}/{len(chunks)} (товаров: {len(chunk)})")
            
            offers = []
            for item in chunk:
                try:
                    price_value = round(float(item['price']), 2)
                    
                    offer = {
                        "offerId": str(item['offer_id']).strip(),
                        "price": {
                            "value": price_value,
                            "currencyId": "RUR"
                        }
                    }
                    offers.append(offer)
                except Exception as e:
                    logger.error(f"Ошибка в данных товара {item.get('offer_id')}: {e}")
                    continue
            
            payload = {"offers": offers}
            
            if offers:
                logger.info(f"🔍 Пример товара в пачке: {offers[0]}")
            
            try:
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    logger.info(f"✅ Пачка {idx + 1}/{len(chunks)} успешно отправлена")
                else:
                    logger.error(f"❌ Ошибка в пачке {idx + 1}/{len(chunks)}: {response.status_code}")
                    logger.error(f"Ответ: {response.text}")
                all_responses.append(response)
            except Exception as e:
                logger.error(f"❌ Ошибка запроса для пачки {idx + 1}: {e}")
                all_responses.append(None)
            
            if idx < len(chunks) - 1:
                time.sleep(0.3)
        
        for resp in reversed(all_responses):
            if resp and resp.status_code == 200:
                return resp
        return None
