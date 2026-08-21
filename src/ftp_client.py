"""
Клиент для работы с FTP
"""

import logging
from ftplib import FTP

logger = logging.getLogger(__name__)


class FTPClient:
    def __init__(self, host, user, password, port=21):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self._ftp = None

    def connect(self):
        try:
            self._ftp = FTP()
            self._ftp.connect(self.host, self.port)
            self._ftp.login(self.user, self.password)
            logger.info(f"✅ Подключено к FTP: {self.host}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к FTP: {e}")
            return False

    def download_file(self, remote_path, local_path):
        if not self._ftp:
            self.connect()
        try:
            with open(local_path, 'wb') as f:
                self._ftp.retrbinary(f'RETR {remote_path}', f.write)
            logger.info(f"📥 Скачан файл: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания: {e}")
            return False

    def list_files(self, path, pattern=''):
        if not self._ftp:
            self.connect()
        try:
            self._ftp.cwd(path)
            files = [f for f in self._ftp.nlst() if pattern in f]
            return files
        except Exception as e:
            logger.warning(f"Ошибка получения списка в {path}: {e}")
            return []
