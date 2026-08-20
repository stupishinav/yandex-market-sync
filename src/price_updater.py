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
            
            logger.info(f"🔍 Прочитано товаров из файлов: {len(prices)}")
            
            if not prices:
                logger.warning("Нет данных о ценах")
                return False

            logger.info(f"Найдено {len(prices)} товаров для обновления цен")
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
            "/from_etm/19",
            "/from_etm/14",
            "/from_etm",
            "from_etm",
            "/",
            ""
        ]

        all_downloaded = []
        
        for path in paths_to_try:
            try:
                logger.info(f"🔍 Ищем в: {path}")
                remote_files = self.ftp_client.list_files(path, pattern="price")
                if remote_files:
                    for remote_file in remote_files:
                        folder_name = path.replace('/', '_').replace('\\', '_')
                        if folder_name.startswith('_'):
                            folder_name = folder_name[1:]
                        if not folder_name:
                            folder_name = 'root'
                        
                        base_name = os.path.basename(remote_file)
                        name, ext = os.path.splitext(base_name)
                        unique_name = f"{folder_name}_{name}{ext}"
                        local_path = os.path.join(local_dir, unique_name)
                        
                        if os.path.exists(local_path):
                            logger.info(f"⏭️ Файл уже скачан: {unique_name}")
                            continue
                        
                        if self.ftp_client.download_file(remote_file, local_path):
                            all_downloaded.append(local_path)
                            logger.info(f"📥 Найден и скачан: {remote_file} -> {unique_name}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при поиске в {path}: {e}")
                continue

        logger.info(f"📊 Всего скачано файлов: {len(all_downloaded)}")
        return all_downloaded

    def _parse_price_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        all_prices = []
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
                                    all_prices.extend(data)
                                    logger.info(f"Прочитан JSON (кодировка: {encoding})")
                                    break
                            elif file_path.endswith('.csv'):
                                reader = csv.DictReader(f, delimiter=';')
                                
                                logger.info(f"📋 Названия колонок в CSV: {reader.fieldnames}")
                                
                                row_count = 0
                                for row in reader:
                                    row_count += 1
                                    if row_count <= 3:
                                        logger.info(f"📊 Строка {row_count}: {row}")
                                    
                                    offer_id = None
                                    for key in row.keys():
                                        if key and key.strip():
                                            if 'Код ЭТМ' in key or 'offer_id' in key or 'SKU' in key:
                                                offer_id = row.get(key)
                                                break
                                    
                                    if not offer_id:
                                        values = list(row.values())
                                        if values:
                                            offer_id = values[0]
                                    
                                    price = None
                                    for key in row.keys():
                                        if key and key.strip():
                                            if 'Розничная Цена' in key or 'price' in key or 'цена' in key:
                                                price = row.get(key)
                                                break
                                    
                                    if not price:
                                        values = list(row.values())
                                        if len(values) > 9:
                                            price = values[9]
                                    
                                    if offer_id and price:
                                        try:
                                            price_str = str(price).strip().replace(',', '.')
                                            if price_str and price_str.replace('.', '', 1).isdigit():
                                                all_prices.append({
                                                    'offer_id': str(offer_id).strip(),
                                                    'price': round(float(price_str), 2)
                                                })
                                        except Exception as e:
                                            logger.warning(f"⚠️ Ошибка в строке {row_count}: {e}")
                                    else:
                                        if row_count <= 3:
                                            logger.warning(f"⚠️ В строке {row_count} нет 'Код ЭТМ' или 'Розничная Цена'")
                                
                                logger.info(f"📊 Всего строк в CSV: {row_count}")
                                logger.info(f"📊 Прочитано товаров: {len(all_prices)}")
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

        unique_prices = {}
        for item in all_prices:
            offer_id = item.get('offer_id')
            if offer_id:
                unique_prices[offer_id] = item
        
        result = list(unique_prices.values())
        logger.info(f"🔍 ИТОГО прочитано уникальных товаров: {len(result)}")
        return result

    def _update_prices(self, prices: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not prices:
            logger.error("❌ Нет данных для отправки!")
            return {}
        
        logger.info(f"📤 Отправка {len(prices)} товаров в Яндекс.Маркет")
        response = self.ym_client.update_prices(prices)
        return response.json() if response else {}

    def _save_result(self, prices: List[Dict], result: Dict) -> None:
        os.makedirs("src/data/prices/", exist_ok=True)
        output_file = f"src/data/prices/update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({"prices": prices, "api_response": result}, f, indent=2)
        logger.info(f"Сохранен: {output_file}")
