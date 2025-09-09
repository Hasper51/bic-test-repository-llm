from dotenv import load_dotenv
import os
import logging

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_openrouter_api_key() -> str:
    """Return the configured API key or raise ValueError if missing."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY должен быть установлен в .env файле")
    return OPENROUTER_API_KEY


AVAILABLE_MODELS = [
    "deepseek/deepseek-chat-v3.1:free",
    "z-ai/glm-4.5-air:free",
    "moonshotai/kimi-k2:free",
]


def setup_logging(logfile: str = "server_logs.txt") -> logging.Logger:
    root = logging.getLogger()

    if not getattr(root, "_configured_by_setup_logging", False):
        for h in list(root.handlers):
            root.removeHandler(h)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Файловый хендлер (все WARNING+ и выше будут писаться в файл)
        fh = logging.FileHandler(logfile, encoding="utf-8")
        fh.setLevel(logging.WARNING)
        fh.setFormatter(formatter)
        root.addHandler(fh)

        # Консольный хендлер — по умолчанию показываем WARNING и ERROR
        sh = logging.StreamHandler()
        sh.setLevel(logging.WARNING)
        sh.setFormatter(formatter)
        root.addHandler(sh)

        root.setLevel(logging.WARNING)
        root._configured_by_setup_logging = True

    return logging.getLogger(__name__)
