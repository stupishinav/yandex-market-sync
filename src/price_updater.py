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
                            logger.info(f"Найден и скачан: {f}")
                    if downloaded:
                        return downloaded
            except Exception as e:
                logger.warning(f"Ошибка при поиске в {path}: {e}")
                continue

        return []

    def _parse_price_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        all_prices = []
        encodings = ['cp1251', 'windows-1251', 'utf-8-sig', 'utf-8', 'latin-1']

        for file_path in file_paths:
            logger.info(f"Обработка файла: {file_path}")
            
            # Сначала прочитаем файл как текст и посмотрим, что внутри
            try:
                with open(file_path, 'r', encoding='cp1251') as f:
                    content = f.read()
                    logger.info(f"Содержимое файла (первые 500 символов):\n{content[:500]}")
            except Exception as e:
                logger.warning(f"Не удалось прочитать как cp1251: {e}")

            # Теперь пробуем парсить
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
                            reader = csv.DictReader(f)
                            # Проверяем названия колонок
                            logger.info(f"Названия колонок в CSV: {reader.fieldnames}")
                            
                            for row in reader:
                                logger.info(f"Строка данных: {row}")
                                
                                # Ищем колонки
                                offer_id = row.get('Код ЭТМ') or row.get('offer_id') or row.get('SKU') or row.get('id')
                                price = row.get('Розничная Цена') or row.get('price') or row.get('цена') or row.get('Price')
                                
                                if offer_id and price:
                                    all_prices.append({
                                        'offer_id': str(offer_id).strip(),
                                        'price': float(str(price).strip().replace(',', '.'))
                                    })
                                    logger.info(f"Добавлен товар: {offer_id} -> {price}")
                                else:
                                    logger.warning(f"Пропущена строка (нет offer_id или price): {row}")
                            
                            if all_prices:
                                logger.info(f"Прочитан CSV (кодировка: {encoding}), найдено {len(all_prices)} товаров")
                                break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"Ошибка при чтении {file_path} с кодировкой {encoding}: {e}")
                    continue

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
