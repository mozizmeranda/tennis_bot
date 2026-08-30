from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from environs import Env

# 1. Инициализация environs
env = Env()
env.read_env()  # Загружает переменные из файла .env

# 2. Настройка путей (pathlib вместо os.path)
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# 3. Базовая настройка логирования
LOG_LEVEL = env.str("LOG_LEVEL", default="INFO").upper()

logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            LOGS_DIR / "app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
    ]
)

# 4. Telegram & Admin
ADMIN_ID: int = env.int("ADMIN_ID", default=0)
TELEGRAM_TOKEN: str = env.str("TELEGRAM_TOKEN", default="")
WEBHOOK_URL: str = env.str("WEBHOOK_URL")
WEBHOOK_SECRET: str = env.str("WEBHOOK_SECRET")

# 5. Словари
CALENDAR_ID: dict[str, str] = {
    "A": env.str("CALENDAR_A", default=""),
    "B": env.str("CALENDAR_B", default="")
}

courts: dict[str, int] = {
    "A": env.int("COURTS_A", default=3),
    "B": env.int("COURTS_B", default=2)
}

# 6. Payme
PAYME_KEY: str = env.str("PAYME_KEY", default="")
PAYME_MERCHANT_ID: str = env.str("PAYME_MERCHANT_ID", default="")

# 7. Click
CLICK_MERCHANT_ID: int = env.int("CLICK_MERCHANT_ID", default=0)
CLICK_SERVICE_ID: int = env.int("CLICK_SERVICE_ID", default=0)
CLICK_MERCHANT_USER_ID: int = env.int("CLICK_MERCHANT_USER_ID", default=0)
CLICK_SECRET_KEY: str = env.str("CLICK_SECRET_KEY", default="")
CLICK_RETURN_URL: str = env.str("CLICK_RETURN_URL", default="")

# 8. Timeout
TIMEOUT_MS: int = env.int("TIMEOUT_MS", default=0)

PAYMENT_CACHE: dict[str, str] = {}

locs = {
    "A": "МГУ",
    "B": "Аджо"
}

location_ids = {
    1: "A",
    2: "B"
}


