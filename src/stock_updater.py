"""
Обновление остатков на Яндекс.Маркете
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
            logger.info("Начинаем обновление остатков...")

            if not os.environ.get('FTP_HOST'):
                logger.error("Нет секрета FTP_HOST!")
                return False

            stock_files = self._download_stock_files()
            if not stock_files:
                logger.warning("Файлы с остатками не найдены")
                return False

            stocks = self._parse_stock_files(stock_files)
            
            # ОТЛАДКА: показываем, сколько товаров прочитано
            logger.info(f"🔍 Прочитано товаров из файла: {len(stocks)}")
            
            if not stocks:
                logger.warning("Нет данных об остатках")
                return False

            logger.info(f"Найдено {len(stocks)} товаров для обновления остатков")
            result = self._update_stocks(stocks)
            self._save_result(stocks, result)
            logger.info("Остатки обновлены!")
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
                remote_files = self.ftp_client.list_files(path, pattern="price")
                if remote_files:
                    downloaded = []
                    for f in remote_files:
                        local = os.path.join(local_dir, os.path.basename(f))
                        if self.ftp_client.download_file(f, local):
                            downloaded.append(local)
                            logger.info(f"Найден файл: {f}")
                    if downloaded:
                        return downloaded
            except:
                continue

        return []

    def _parse_stock_files(self, file_paths: List[str]) -> List[Dict]:
        all_stocks = []
        encodings = ['cp1251', 'windows-1251', 'utf-8-sig', 'utf-8', 'latin-1']

        for file_path in file_paths:
            try:
                logger.info(f"📄 Открываем файл: {file_path}")
                
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
                                
                                # ОТЛАДКА: показываем названия колонок
                                logger.info(f"📋 Названия колонок в CSV: {reader.fieldnames}")
                                
                                row_count = 0
                                for row in reader:
                                    row_count += 1
                                    # ОТЛАДКА: показываем первые 3 строки
                                    if row_count <= 3:
                                        logger.info(f"📊 Строка {row_count}: {row}")
                                    
                                    offer_id = row.get('Код ЭТМ') or row.get('offer_id') or row.get('SKU')
                                    stock = row.get('Количество') or row.get('stock') or row.get('quantity')
                                    
                                    if offer_id and stock:
                                        try:
                                            stock_val = str(stock).strip().replace(',', '.')
                                            all_stocks.append({
                                                'offer_id': str(offer_id).strip(),
                                                'stock': float(stock_val)
                                            })
                                        except Exception as e:
                                            logger.warning(f"⚠️ Ошибка в строке {row_count}: {e}")
                                    else:
                                        if row_count <= 3:
                                            logger.warning(f"⚠️ В строке {row_count} нет 'Код ЭТМ' или 'Количество'")
                                
                                logger.info(f"📊 Всего строк в CSV: {row_count}")
                                logger.info(f"📊 Прочитано товаров: {len(all_stocks)}")
                                logger.info(f"Прочитан CSV (кодировка: {encoding})")
                                break
                    except UnicodeDecodeError:
                        logger.warning(f"⚠️ Не подошла кодировка {encoding}")
                        continue
                    except Exception as e:
                        logger.error(f"Ошибка при чтении с кодировкой {encoding}: {e}")
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
