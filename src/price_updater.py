def update_prices(self, prices):
    """
    Обновление цен - ПРАВИЛЬНЫЙ ФОРМАТ
    """
    if not prices:
        logger.error("❌ Нет данных для обновления цен!")
        return None

    # Используем правильный эндпоинт для бизнеса
    url = f"{self.base_url}/businesses/{self.business_id}/offer-prices/updates"
    
    headers = {
        'Api-Key': self.api_key,
        'Content-Type': 'application/json'
    }

    chunk_size = 2000
    total_items = len(prices)
    chunks = [prices[i:i + chunk_size] for i in range(0, total_items, chunk_size)]
    
    logger.info(f"📦 Разбивка {total_items} товаров на {len(chunks)} пачек по {chunk_size} шт.")
    
    all_responses = []
    
    for idx, chunk in enumerate(chunks):
        logger.info(f"📤 Отправка пачки {idx + 1}/{len(chunks)} (товаров: {len(chunk)})")
        
        offers = []
        for item in chunk:
            try:
                # Форматируем цену как число с 2 знаками
                price_value = round(float(item['price']), 2)
                
                # ПРАВИЛЬНАЯ СТРУКТУРА: price - это ОБЪЕКТ!
                offer = {
                    "offerId": str(item['offer_id']).strip(),
                    "price": {
                        "value": price_value,        # ← ЧИСЛО!
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
        
        if idx < len(chunks) - 1:
            import time
            time.sleep(0.5)
    
    for resp in reversed(all_responses):
        if resp and resp.status_code == 200:
            return resp
    return all_responses[0] if all_responses else None
