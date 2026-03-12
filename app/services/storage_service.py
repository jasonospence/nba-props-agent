import json
from pathlib import Path
from datetime import datetime
from app.config import settings

class StorageService:
    def __init__(self) -> None:
        self.base = Path(settings.report_output_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def save_json(self, name: str, payload: dict | list) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fp = self.base / f"{ts}_{name}.json"
        fp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(fp)

    def save_text(self, name: str, text: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fp = self.base / f"{ts}_{name}.md"
        fp.write_text(text, encoding="utf-8")
        return str(fp)

    def save_html(self, name: str, html: str) -> str:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        fp = self.base / f"{ts}_{name}.html"
        fp.write_text(html, encoding="utf-8")
        return str(fp)
