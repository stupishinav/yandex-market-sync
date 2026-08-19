import os
import json
import csv
import logging
from datetime import datetime
from typing import List, Dict, Any  ← ЭТО ГЛАВНОЕ!
def _download_price_files(self) -> List[str]:
    """Скачивает файлы с ценами с FTP - упрощенная версия"""
    local_dir = "src/data/prices/"
    os.makedirs(local_dir, exist_ok=True)

    # Пробуем найти файлы в разных местах
    possible_paths = [
        self.ftp_price_folder,
        "/from_etm",
        "/from_etm/",
        "from_etm",
        "/",
        ""
    ]
    
    downloaded = []
    for path in possible_paths:
        try:
            logger.info(f"🔍 Ищем в папке: {path}")
            remote_files = self.ftp_client.list_files(path, pattern="price")
            if not remote_files:
                remote_files = self.ftp_client.list_files(path, pattern="")
                remote_files = [f for f in remote_files if f.endswith(('.json', '.csv', '.txt'))]
            
            for remote_file in remote_files:
                local_path = os.path.join(local_dir, os.path.basename(remote_file))
                if self.ftp_client.download_file(remote_file, local_path):
                    downloaded.append(local_path)
                    logger.info(f"📥 НАЙДЕН И СКАЧАН: {remote_file}")
            
            if downloaded:
                logger.info(f"✅ Найдено файлов в папке {path}: {len(downloaded)}")
                return downloaded
        except Exception as e:
            logger.warning(f"⚠️ Не удалось проверить папку {path}: {e}")
    
    logger.warning(f"⚠️ Файлы не найдены ни в одной папке. Скачано: {len(downloaded)}")
    return downloaded
