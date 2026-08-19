"""
Обновление цен на Яндекс.Маркете
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
    def __init__(self):
        self.ftp_client = FTPClient(
            host=os.environ.get('FTP_HOST'),
            user=os.environ.get('FTP_USER'),
            password=os.environ.get('FTP_PASS')
        )
        self.ym_client = YandexMarketClient(
            api_key=os.environ.get('YM_API_KEY'),
            campaign_id=os.environ.get('YM_CAMPAIGN_ID'),
            warehouse_id=os.environ.get('YM_WAREHOUSE_ID'),
            business_id=os.environ.get('YM_BUSINESS_ID')
        )
        self.ftp_folder = os.environ.get('FTP_FOLDER', '/')
        self.ftp_price_folder = os.environ.get('FTP_PRICE_FOLDER', 'prices/')

    def run(self) -> bool:
        try:
            logger.info("Начинаем обновление цен...")

            if not os.environ.get('FTP_HOST'):
                logger.error("Нет секрета FTP_HOST!")
                return False

            price_files = self._download_price_files()
            if not price_files:
                logger.warning("Файлы с ценами не найдены")
                return False

            prices = self._parse_price_files(price_files)
            if not prices:
                logger.warning("Нет данных о ценах")
                return False

            logger.info(f"Найдено {len(prices)} товаров")
            result = self._update_prices(prices)
            self._save_result(prices, result)
            logger.info("Готово!")
            return True

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return False

    def _download_price_files(self) -> List[str]:
        local_dir = "src/data/prices/"
        os.makedirs(local_dir, exist_ok=True)

        paths_to_try = [
            self.ftp_price_folder,
            "/from_etm",
            "from_etm",
            "/",
            ""
        ]

        for path in paths_to_try:
            try:
                logger.info(f"Ищем в: {path}")
                remote_files = self.ftp_client.list_files(path, pattern="price")
                if remote_files:
                    downloaded = []
                    for f in remote_files:
                        local = os.path.join(local_dir, os.path.basename(f))
                        if self.ftp_client.download_file(f, local):
                            downloaded.append(local)
                            logger.info(f"Найден: {f}")
                    if downloaded:
                        return downloaded
            except:
                continue

        return []

    def _parse_price_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        all_prices = []
        encodings = ['utf-8-sig', 'cp1251', 'windows-1251', 'latin-1', 'utf-8']

        for file_path in file_paths:
            try:
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            if file_path.endswith('.json'):
                                data = json.load(f)
                                if isinstance(data, list):
                                    all_prices.extend(data)
                                    logger.info(f"Прочитан JSON (кодировка: {encoding})")
                                    break
                            elif file_path.endswith('.csv'):
                                # ВАЖНО: разделитель ; (точка с запятой)
                                reader = csv.DictReader(f, delimiter=';')
                                for row in reader:
                                    offer_id = row.get('Код ЭТМ') or row.get('offer_id') or row.get('SKU')
                                    price = row.get('Розничная Цена') or row.get('price') or row.get('цена')
                                    if offer_id and price:
                                        # Заменяем запятую на точку в числе, если есть
                                        price_str = str(price).strip().replace(',', '.')
                                        all_prices.append({
                                            'offer_id': str(offer_id).strip(),
                                            'price': float(price_str)
                                        })
                                logger.info(f"Прочитан CSV (кодировка: {encoding})")
                                break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        continue
            except Exception as e:
                logger.error(f"Ошибка парсинга {file_path}: {e}")

        return all_prices

    def _update_prices(self, prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {
            "prices": [
                {
                    "id": p['offer_id'],
                    "price": {"value": str(p['price']), "currencyId": "RUR"}
                }
                for p in prices
            ]
        }
        response = self.ym_client.update_prices(payload)
        return response.json() if response else {}

    def _save_result(self, prices: List[Dict], result: Dict) -> None:
        os.makedirs("src/data/prices/", exist_ok=True)
        output_file = f"src/data/prices/update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"prices": prices, "api_response": result}, f, indent=2)
        logger.info(f"Сохранен: {output_file}")
