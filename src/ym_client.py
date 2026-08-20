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
        Обновление цен - ПРАВИЛЬНАЯ СТРУКТУРА ДЛЯ API-KEY
        """
        if not prices:
            logger.error("❌ Нет данных для обновления цен!")
            return None

        url = f"{self.base_url}/campaigns/{self.campaign_id}/offer-prices/updates"
        
        headers = {
            'Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }

        # Разбиваем товары на пачки по 2000
        chunk_size = 2000
        total_items = len(prices)
        chunks = [prices[i:i + chunk_size] for i in range(0, total_items, chunk_size)]
        
        logger.info(f"📦 Разбивка {total_items} товаров на {len(chunks)} пачек по {chunk_size} шт.")
        
        all_responses = []
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"📤 Отправка пачки {idx + 1}/{len(chunks)} (товаров: {len(chunk)})")
            
            # ФОРМИРУЕМ ПРАВИЛЬНЫЙ PAYLOAD
            offers = []
            for item in chunk:
                try:
                    # ГЛАВНОЕ: ПРЕОБРАЗУЕМ ЦЕНУ В СТРОКУ С 2 ЗНАКАМИ
                    price_value = str(round(float(item['price']), 2))
                    # Убираем .0 если цена целая
                    if price_value.endswith('.0'):
                        price_value = price_value[:-2]
                    
                    offer = {
                        "offerId": str(item['offer_id']).strip(),
                        "price": price_value,
                        "currency": "RUR"
                    }
                    offers.append(offer)
                except Exception as e:
                    logger.error(f"Ошибка в данных товара {item.get('offer_id')}: {e}")
                    continue
            
            payload = {"offers": offers}
            
            # ОТЛАДКА: показываем первый товар в пачке
            if offers:
                logger.info(f"🔍 Пример товара в пачке: {offers[0]}")
                logger.info(f"🔍 Payload (первые 200 символов): {str(payload)[:200]}")
            
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
            
            # Пауза между пачками
            if idx < len(chunks) - 1:
                time.sleep(0.5)
        
        # Возвращаем последний успешный ответ
        for resp in reversed(all_responses):
            if resp and resp.status_code == 200:
                return resp
        return all_responses[0] if all_responses else None
