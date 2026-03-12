import requests
from pathlib import Path
from app.config import settings


TELEGRAM_MAX_TEXT = 3900


class TelegramService:
    def __init__(self) -> None:
        self.enabled = settings.telegram_enabled
        self.bot_token = settings.telegram_bot_token.strip()
        self.chat_id = settings.telegram_chat_id.strip()
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def should_send(self) -> bool:
        return self.enabled and self.is_configured()

    def _split_message(self, text: str, max_len: int = TELEGRAM_MAX_TEXT) -> list[str]:
        if len(text) <= max_len:
            return [text]

        chunks: list[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= max_len:
                chunks.append(remaining)
                break

            split_at = remaining.rfind("\n", 0, max_len)
            if split_at <= 0:
                split_at = max_len
            chunks.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()

        return [c for c in chunks if c]

    def send_text(self, text: str) -> None:
        if not self.should_send():
            return

        chunks = self._split_message(text)
        for idx, chunk in enumerate(chunks):
            prefix = f"[{idx + 1}/{len(chunks)}]\n" if len(chunks) > 1 else ""
            payload = {
                "chat_id": self.chat_id,
                "text": f"{prefix}{chunk}",
                "disable_web_page_preview": True,
            }
            resp = requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=30)
            resp.raise_for_status()

    def send_document(self, file_path: str, caption: str = "") -> None:
        if not self.should_send():
            return

        fp = Path(file_path)
        if not fp.exists():
            raise FileNotFoundError(f"Telegram document path not found: {file_path}")

        with fp.open("rb") as handle:
            payload = {"chat_id": self.chat_id}
            if caption:
                payload["caption"] = caption[:1024]
            resp = requests.post(
                f"{self.base_url}/sendDocument",
                data=payload,
                files={"document": handle},
                timeout=60,
            )
            resp.raise_for_status()

    def send_report(self, report_html_path: str, preview_text: str = "") -> None:
        header = "NBA Props Agent report is ready."
        self.send_document(report_html_path, caption=f"{header} (HTML)")

        if preview_text:
            self.send_text(f"{header}\n\nShort preview:\n{preview_text}")
        else:
            self.send_text(f"{header}\n\nOpen the attached HTML report for full formatted details.")
