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

    # Разбиваем на пачки по 2000
    chunk_size = 2000
    total_items = len(stocks)
    chunks = [stocks[i:i + chunk_size] for i in range(0, total_items, chunk_size)]
    
    logger.info(f"📦 Разбивка {total_items} товаров на {len(chunks)} пачек по {chunk_size} шт.")
    
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
            # ГЛАВНОЕ ИЗМЕНЕНИЕ: PUT вместо POST!
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
            import time
            time.sleep(0.5)
    
    for resp in reversed(all_responses):
        if resp and resp.status_code == 200:
            return resp
    return all_responses[0] if all_responses else None
