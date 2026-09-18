"""Configuration management for Apex Agent."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "memory").mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "apex_index.db"
MEMORY_MD_PATH = DATA_DIR / "MEMORY.md"
ICP_MD_PATH = DATA_DIR / "ICP.md"

# 1. Primary: Hermes Live Gateway API Server (127.0.0.1:8642)
HERMES_API_BASE_URL = os.getenv("HERMES_API_BASE_URL", "http://127.0.0.1:8642/v1")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "29207fb3d15c403ace544110c40a2af8ef4ab4871a4c6cc7202b6208346873d9")

# 2. Secondary: OpenRouter / 9router (127.0.0.1:20128)
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "http://127.0.0.1:20128/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "sk-xIcYYd6ymiCEe0L0XLC9TplykOetTVWiV43xaQW70STeO6JbgghdvTfHU0FdbuqP")

# 3. Local offline fallback
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8080/v1")
LOCAL_LLM_API_KEY = os.getenv("LOCAL_LLM_API_KEY", "local")

# Telegram Notifications
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8725855304:AAGp1RTU-62RfVwvcUX82EzpYtCSJlqeBjE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "5590614649")
