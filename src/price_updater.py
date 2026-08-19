"""
Обновление цен на Яндекс.Маркете
Поддерживает JSON и CSV файлы
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any

from .ftp_client import FTPClient
from .ym_client import YandexMarketClient

logger = logging.getLogger(__name__)


class PriceUpdater:
    """Класс для обновления цен"""

    def __init__(self):
        self.ftp_client = FTPClient(
            host=os.environ['FTP_HOST'],
            user=os.environ['FTP_USER'],
            password=os.environ['FTP_PASS']
        )
        self.ym_client = YandexMarketClient(
            api_key=os.environ['YM_API_KEY'],
            campaign_id=os.environ['YM_CAMPAIGN_ID'],
            warehouse_id=os.environ['YM_WAREHOUSE_ID'],
            business_id=os.environ['YM_BUSINESS_ID']
        )
        self.ftp_folder = os.environ.get('FTP_FOLDER', '/')
        self.ftp_price_folder = os.environ.get('FTP_PRICE_FOLDER', 'prices/')

    def run(self) -> bool:
        """Основной метод обновления цен"""
        try:
            logger.info("🔄 Начинаем обновление цен...")

            # Скачиваем файлы с ценами с FTP
            price_files = self._download_price_files()
            if not price_files:
                logger.warning("⚠️ Файлы с ценами не найдены")
                return False

            # Парсим файлы (поддерживает JSON и CSV)
            prices = self._parse_price_files(price_files)
            if not prices:
                logger.warning("⚠️ Нет данных о ценах для обновления")
                return False

            logger.info(f"📊 Найдено {len(prices)} товаров для обновления цен")

            # Отправляем цены в Яндекс.Маркет
            result = self._update_prices(prices)

            # Сохраняем результат
            self._save_result(prices, result)

            logger.info("✅ Обновление цен успешно завершено")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении цен: {e}")
            return False

    def _download_price_files(self) -> List[str]:
        """Скачивает файлы с ценами с FTP"""
        local_dir = "src/data/prices/"
        os.makedirs(local_dir, exist_ok=True)

        # Ищем файлы с "price" в названии (и .json, и .csv)
        remote_files = self.ftp_client.list_files(self.ftp_price_folder, pattern="price")
        downloaded = []

        for remote_file in remote_files:
            local_path = os.path.join(local_dir, os.path.basename(remote_file))
            if self.ftp_client.download_file(remote_file, local_path):
                downloaded.append(local_path)
                logger.info(f"📥 Скачан файл: {remote_file}")

        return downloaded

    def _parse_price_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Парсит файлы цен
        Поддерживает: .json и .csv
        """
        all_prices = []

        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    # ===== ЕСЛИ ФАЙЛ JSON =====
                    if file_path.endswith('.json'):
                        data = json.load(f)
                        if isinstance(data, list):
                            all_prices.extend(data)
                        elif isinstance(data, dict) and 'prices' in data:
                            all_prices.extend(data['prices'])
                        logger.info(f"📄 Прочитан JSON: {os.path.basename(file_path)}")

                    # ===== ЕСЛИ ФАЙЛ CSV =====
                    elif file_path.endswith('.csv'):
                        reader = csv.DictReader(f)
                        for row in reader:
                            # Пытаемся найти колонки (поддерживает разные названия)
                            offer_id = row.get('offer_id') or row.get('SKU') or row.get('id') or row.get('Артикул')
                            price = row.get('price') or row.get('цена') or row.get('Цена') or row.get('Price')
                            old_price = row.get('old_price') or row.get('старая_цена') or row.get('Старая цена') or row.get('OldPrice')
                            
                            if offer_id and price:
                                price_data = {
                                    'offer_id': str(offer_id).strip(),
                                    'price': float(str(price).strip().replace(',', '.'))
                                }
                                # Добавляем старую цену, если есть
                                if old_price and str(old_price).strip():
                                    price_data['old_price'] = float(str(old_price).strip().replace(',', '.'))
                                all_prices.append(price_data)
                            else:
                                logger.warning(f"⚠️ В CSV пропущена строка: {row}")
                        logger.info(f"📄 Прочитан CSV: {os.path.basename(file_path)}")

                    else:
                        logger.warning(f"⚠️ Неподдерживаемый формат: {file_path}")

            except Exception as e:
                logger.error(f"❌ Ошибка парсинга {file_path}: {e}")

        return all_prices

    def _update_prices(self, prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Отправляет цены в Яндекс.Маркет"""
        payload = {
            "prices": [
                {
                    "id": item['offer_id'],
                    "price": {
                        "value": str(item['price']),
                        "currencyId": "RUR"
                    }
                }
                for item in prices
            ]
        }

        # Добавляем старую цену, если есть
        for item, payload_item in zip(prices, payload['prices']):
            if 'old_price' in item and item['old_price']:
                payload_item['price']['discountBase'] = str(item['old_price'])

        response = self.ym_client.update_prices(payload)
        return response.json() if response else {}

    def _save_result(self, prices: List[Dict], result: Dict) -> None:
        """Сохраняет результат в JSON"""
        output_file = f"src/data/prices/prices_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_items": len(prices),
            "prices": prices,
            "api_response": result
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 Результат сохранен: {output_file}")
