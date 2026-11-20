import logging


def setup_logger():
    # 1. Создаем логгер
    logger = logging.getLogger("market_bot")
    logger.setLevel(logging.DEBUG)  # Пропускаем всё для начала

    # 2. Формат: Дата [Уровень] Имя: Сообщение
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. Обработчик для консоли (чтобы видеть в PyCharm)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # 4. Обработчик для всех событий (INFO+)


    # Добавляем все обработчики к логгеру
    logger.addHandler(console_handler)


    return logger
