# core/cookies_parsers/mailru_cookies_parser.py
import re
from pathlib import Path
from typing import List, Dict, Optional
from core.lib.module_logger_manager import LoggerManager

class MailRuCookiesParser:
    """Парсер куков Mail.ru группы (mail.ru, list.ru, bk.ru, inbox.ru, xmail.ru, internet.ru)"""

    def __init__(self, logs_dir: str = "logs", logger: Optional[LoggerManager] = None):
        self.logs_dir = Path(logs_dir)
        self.logger = logger or LoggerManager("MailRuCookiesParser")

        self.domains = [
            '.mail.ru', 'mail.ru', 'e.mail.ru', 'account.mail.ru',
            '.list.ru', 'list.ru',
            '.bk.ru', 'bk.ru',
            '.inbox.ru', 'inbox.ru',
            '.xmail.ru', 'xmail.ru',
            '.internet.ru', 'internet.ru'
        ]
        self.cookie_names = ['mrcu', 'act', 'mbox', 'sdcs', 'Mpop']

    # ------------------- Базовые методы (аналог Yandex) -------------------
    def find_cookies_files(self) -> List[Path]:
        files = []
        if not self.logs_dir.exists():
            self.logger.warning(f"Папка {self.logs_dir} не существует")
            return files
        try:
            for p in self.logs_dir.rglob("*.txt"):
                if p.stat().st_size > 1024*1024:          # >1MB — пропускаем
                    continue
                if self._is_netscape_file(p):
                    files.append(p)
            self.logger.info(f"Найдено кандидатов на куки Mail.ru: {len(files)}")
            return files
        except Exception as e:
            self.logger.error(f"Ошибка поиска файлов: {e}")
            return []

    def _is_netscape_file(self, path: Path) -> bool:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if i >= 10: break
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    parts = line.split("\t")
                    if len(parts) >= 7 and "." in parts[0]:
                        return True
        except: pass
        return False

    def parse_file(self, path: Path) -> List[Dict]:
        cookies = []
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    parts = line.split("\t")
                    if len(parts) < 7: continue
                    cookies.append({
                        "domain": parts[0].strip(),
                        "name":   parts[5].strip(),
                        "value":  parts[6].strip(),
                        "path":   parts[2].strip(),
                        "secure": parts[3].upper() == "TRUE",
                        "expires": int(float(parts[4])) if parts[4] != "0" else 0,
                    })
            return cookies
        except Exception as e:
            self.logger.error(f"Ошибка парсинга {path}: {e}")
            return []

    def _belongs_to_mailru(self, cookies: List[Dict]) -> bool:
        domain_hits = 0
        name_hits   = 0
        for c in cookies:
            dom = c["domain"].lower()
            name = c["name"]
            if any(d in dom for d in ["mail.ru","list.ru","bk.ru","inbox.ru","xmail.ru","internet.ru"]):
                domain_hits += 1
            if name in self.cookie_names:
                name_hits += 1
        return domain_hits >= 2 or (domain_hits >= 1 and name_hits >= 1)

    # ------------------- Публичные методы -------------------
    def get_all_mailru_cookies_files(self) -> List[str]:
        """Возвращает отсортированный список файлов с куками Mail.ru (лучшие сверху)"""
        candidates = self.find_cookies_files()
        scored = []
        for p in candidates:
            cookies = self.parse_file(p)
            if self._belongs_to_mailru(cookies):
                score = self._score(cookies)
                scored.append((str(p), score))

        scored.sort(key=lambda x: x[1], reverse=True)
        files = [p for p, _ in scored]
        self.logger.info(f"Найдено валидных файлов Mail.ru: {len(files)}")
        return files

    def _score(self, cookies: List[Dict]) -> int:
        score = 0
        important = {"mrcu", "Mpop", "act"}
        for c in cookies:
            if c["name"] in important:
                score += 15
            if c["name"] in self.cookie_names:
                score += 5
            if any(d in c["domain"] for d in [".mail.ru","e.mail.ru"]):
                score += 3
        return score

def get_all_mailru_cookies_files(logs_dir: str = "logs") -> List[str]:
    return MailRuCookiesParser(logs_dir).get_all_mailru_cookies_files()