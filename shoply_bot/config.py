# SPDX-License-Identifier: CC0-1.0

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)


@dataclass
class Settings:
    openai_api_key: str
    openai_model: str
    brand_name: str

    @classmethod
    def load(cls) -> "Settings":
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY не найден в окружении или .env")

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        brand = os.getenv("BRAND_NAME", "Shoply")
        return cls(openai_api_key=api_key, openai_model=model, brand_name=brand)
