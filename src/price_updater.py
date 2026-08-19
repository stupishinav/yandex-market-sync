"""
Обновление остатков на Яндекс.Маркете
Читает данные из того же файла, что и цены (price.csv)
"""

import os
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict

from .ftp_client import FTPClient
from .ym_client import YandexMarketClient

logger = logging.getLogger(__name__)


class StockUpdater:
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
            logger.info("🔄 Начинаем обновление остатков...")

            if not os.environ.get('FTP_HOST'):
                logger.error("Нет секрета FTP_HOST!")
                return False

            # Ищем файл price.csv (тот же, что и для цен)
            stock_files = self._download_stock_files()
            if not stock_files:
                logger.warning("Файл price.csv не найден")
                return False

            stocks = self._parse_stock_files(stock_files)
            if not stocks:
                logger.warning("Нет данных об остатках")
                return False

            logger.info(f"Найдено {len(stocks)} товаров для обновления остатков")
            result = self._update_stocks(stocks)
            self._save_result(stocks, result)
            logger.info("✅ Остатки обновлены!")
            return True

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return False

    def _download_stock_files(self) -> List[str]:
        local_dir = "src/data/stock/"
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
                logger.info(f"Ищем файл с остатками в: {path}")
                # Ищем price.csv (тот же файл, что и для цен)
                remote_files = self.ftp_client.list_files(path, pattern="price")
                if remote_files:
                    downloaded = []
                    for f in remote_files:
                        local = os.path.join(local_dir, os.path.basename(f))
                        if self.ftp_client.download_file(f, local):
                            downloaded.append(local)
                            logger.info(f"Найден файл для остатков: {f}")
                    if downloaded:
                        return downloaded
            except:
                continue

        return []

    def _parse_stock_files(self, file_paths: List[str]) -> List[Dict]:
        all_stocks = []
        encodings = ['utf-8-sig', 'cp1251', 'windows-1251', 'latin-1', 'utf-8']

        for file_path in file_paths:
            try:
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            if file_path.endswith('.json'):
                                data = json.load(f)
                                if isinstance(data, list):
                                    all_stocks.extend(data)
                                    logger.info(f"Прочитан JSON (кодировка: {encoding})")
                                    break
                            elif file_path.endswith('.csv'):
                                reader = csv.DictReader(f, delimiter=';')
                                for row in reader:
                                    offer_id = row.get('Код ЭТМ') or row.get('offer_id') or row.get('SKU')
                                    # Ищем колонку с количеством
                                    stock = row.get('Количество') or row.get('stock') or row.get('quantity') or row.get('Остаток')
                                    if offer_id and stock:
                                        # Пропускаем товары с нулевым остатком (опционально)
                                        stock_val = str(stock).strip().replace(',', '.')
                                        if float(stock_val) > 0:  # только положительные остатки
                                            all_stocks.append({
                                                'offer_id': str(offer_id).strip(),
                                                'stock': float(stock_val)
                                            })
                                logger.info(f"Прочитан CSV (кодировка: {encoding}), найдено {len(all_stocks)} товаров с остатками")
                                break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        continue
            except Exception as e:
                logger.error(f"Ошибка парсинга {file_path}: {e}")

        return all_stocks

    def _update_stocks(self, stocks: List[Dict]) -> Dict:
        response = self.ym_client.update_stock(stocks)
        return response.json() if response else {}

    def _save_result(self, stocks: List[Dict], result: Dict) -> None:
        os.makedirs("src/data/stock/", exist_ok=True)
        output_file = f"src/data/stock/update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"stocks": stocks, "api_response": result}, f, indent=2)
        logger.info(f"Сохранен: {output_file}")
