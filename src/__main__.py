"""
Главный модуль для синхронизации данных с Яндекс.Маркетом
"""

import sys
import logging
import argparse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Точка входа в программу"""
    parser = argparse.ArgumentParser(description='Синхронизация данных с Яндекс.Маркетом')
    parser.add_argument(
        '--mode',
        choices=['stock', 'prices', 'both'],
        default='both',
        help='Режим работы: stock - только остатки, prices - только цены, both - и то, и другое'
    )
    args = parser.parse_args()

    logger.info(f"🚀 Запуск синхронизации в режиме: {args.mode}")

    results = []

    # Обновление остатков
    if args.mode in ['stock', 'both']:
        try:
            from .stock_updater import StockUpdater
            stock_updater = StockUpdater()
            success = stock_updater.run()
            results.append(('Остатки', success))
            logger.info(f"{'✅' if success else '❌'} Обновление остатков: {'успешно' if success else 'ошибка'}")
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении остатков: {e}")
            results.append(('Остатки', False))

    # Обновление цен
    if args.mode in ['prices', 'both']:
        try:
            from .price_updater import PriceUpdater
            price_updater = PriceUpdater()
            success = price_updater.run()
            results.append(('Цены', success))
            logger.info(f"{'✅' if success else '❌'} Обновление цен: {'успешно' if success else 'ошибка'}")
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении цен: {e}")
            results.append(('Цены', False))

    # Итоговый статус
    all_success = all(success for _, success in results)
    if all_success:
        logger.info("🎉 Все операции успешно завершены!")
        sys.exit(0)
    else:
        logger.warning("⚠️ Некоторые операции завершились с ошибкой")
        sys.exit(1)


if __name__ == "__main__":
    main()
