# core/cookies_parsers/yandex_cookies_parser.py
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from core.lib.module_logger_manager import LoggerManager

class YandexCookiesParser:
    def __init__(self, logs_dir: str = "logs", logger: LoggerManager = None):
        self.logs_dir = Path(logs_dir)
        self.logger = logger or LoggerManager("YandexCookiesParser")
        self.domains = [
            'yandex.ru', '.yandex.ru', 'mail.yandex.ru', 'passport.yandex.ru',
            'ya.ru', '.ya.ru', 'yandex.com', '.yandex.com',
            'passport.yandex.com', 'mail.yandex.com'
        ]
        self.cookie_names = ['yandex_login', 'yandexuid', 'Session_id', 'ys', 'yp']

    def find_cookies_files(self) -> List[Path]:
        cookies_files = []
        if not self.logs_dir.exists():
            self.logger.warning(f"Папка {self.logs_dir} не существует")
            return cookies_files
        try:
            for file_path in self.logs_dir.rglob("*.txt"):
                if file_path.stat().st_size > 1024 * 1024:
                    continue
                if self._is_netscape_cookies_file(file_path):
                    cookies_files.append(file_path)
            self.logger.info(f"Найдено файлов с куками: {len(cookies_files)}")
            return cookies_files
        except Exception as e:
            self.logger.error(f"Ошибка при поиске файлов с куками: {e}")
            return []

    def _is_netscape_cookies_file(self, file_path: Path) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [line.strip() for i, line in enumerate(f) if i < 10]
            for line in first_lines:
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) >= 7:
                    domain = parts[0]
                    if '.' in domain and any(char.isalpha() for char in domain):
                        return True
            return False
        except Exception:
            return False

    def parse_cookies_file(self, file_path: Path) -> List[Dict]:
        cookies = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) < 7:
                        continue
                    domain = parts[0].strip()
                    flag = parts[1].strip().upper() == 'TRUE'
                    path = parts[2].strip()
                    secure = parts[3].strip().upper() == 'TRUE'
                    expiration = parts[4].strip()
                    name = parts[5].strip()
                    value = parts[6].strip()
                    expires = int(float(expiration)) if expiration != '0' else 0
                    cookie_data = {
                        'domain': domain,
                        'flag': flag,
                        'path': path,
                        'secure': secure,
                        'expiration': expires,
                        'name': name,
                        'value': value,
                        'source_file': str(file_path),
                        'line_number': line_num
                    }
                    cookies.append(cookie_data)
            self.logger.debug(f"Парсинг {file_path}: найдено {len(cookies)} кук")
            return cookies
        except Exception as e:
            self.logger.error(f"Ошибка парсинга файла {file_path}: {e}")
            return []

    def _cookies_belong_to_yandex(self, cookies: List[Dict]) -> bool:
        domain_matches = 0
        cookie_name_matches = 0
        for cookie in cookies:
            domain = cookie['domain']
            name = cookie['name']
            for service_domain in self.domains:
                if service_domain.startswith('.'):
                    if domain.endswith(service_domain) or domain == service_domain[1:]:
                        domain_matches += 1
                        break
                else:
                    if domain == service_domain:
                        domain_matches += 1
                        break
            if name in self.cookie_names:
                cookie_name_matches += 1
        return domain_matches >= 2 or (domain_matches >= 1 and cookie_name_matches >= 1)

    def find_yandex_cookies(self) -> Dict[str, List[Dict]]:
        yandex_cookies = {}
        self.logger.info("Поиск куков для Yandex")
        cookies_files = self.find_cookies_files()
        if not cookies_files:
            self.logger.warning("Файлы с куками не найдены")
            return yandex_cookies
        for file_path in cookies_files:
            try:
                cookies = self.parse_cookies_file(file_path)
                if not cookies:
                    continue
                if self._cookies_belong_to_yandex(cookies):
                    yandex_cookies[str(file_path)] = cookies
                    self.logger.info(f"Найдены куки Yandex в файле: {file_path}")
            except Exception as e:
                self.logger.error(f"Ошибка анализа файла {file_path}: {e}")
                continue
        self.logger.info(f"Найдено файлов с куками Yandex: {len(yandex_cookies)}")
        return yandex_cookies

    def get_all_yandex_cookies_files(self) -> List[str]:
        yandex_cookies = self.find_yandex_cookies()
        if not yandex_cookies:
            self.logger.warning("Куки Yandex не найдены")
            return []
        file_scores = {}
        for file_path, cookies in yandex_cookies.items():
            score = self._score_yandex_cookies(cookies)
            file_scores[file_path] = score
        sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        self.logger.info(f"Найдено файлов Yandex: {len(sorted_files)}")
        for file_path, score in sorted_files[:5]:
            self.logger.info(f"  {Path(file_path).name}: оценка {score}")
        return [file_path for file_path, score in sorted_files]

    def _score_yandex_cookies(self, cookies: List[Dict]) -> int:
        score = 0
        critical_cookies = {'yandexuid', 'Session_id', 'ys', 'yandex_login'}
        important_domains = {'.yandex.ru', 'yandex.ru', 'mail.yandex.ru', 'passport.yandex.ru'}
        found_cookies = set()
        found_domains = set()
        for cookie in cookies:
            name = cookie['name']
            domain = cookie['domain']
            if name in critical_cookies:
                found_cookies.add(name)
                score += 10
            if domain in important_domains:
                found_domains.add(domain)
                score += 5
            if 'yandex' in name.lower():
                score += 2
        completeness = len(found_cookies) / len(critical_cookies)
        score += int(completeness * 20)
        domain_variety = len(found_domains)
        score += domain_variety * 3
        return score

    def create_cookies_file(self, cookies: List[Dict], output_path: str) -> bool:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file contains cookies for mail checking\n")
                f.write("# Generated by YandexCookiesParser\n\n")
                for cookie in cookies:
                    domain = cookie['domain']
                    flag = 'TRUE' if cookie['flag'] else 'FALSE'
                    path = cookie['path']
                    secure = 'TRUE' if cookie['secure'] else 'FALSE'
                    expiration = str(cookie['expiration'])
                    name = cookie['name']
                    value = cookie['value']
                    line = f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n"
                    f.write(line)
            self.logger.info(f"Создан файл куков: {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания файла куков: {e}")
            return False

    def merge_yandex_cookies(self, output_file: str = "cookies_yandex_merged.txt") -> Optional[str]:
        yandex_cookies = self.find_yandex_cookies()
        if not yandex_cookies:
            return None
        all_cookies = {}
        for file_cookies in yandex_cookies.values():
            for cookie in file_cookies:
                key = f"{cookie['domain']}|{cookie['name']}"
                if key not in all_cookies or cookie['expiration'] > all_cookies[key]['expiration']:
                    all_cookies[key] = cookie
        merged_cookies = list(all_cookies.values())
        if not merged_cookies:
            return None
        output_path = Path(self.logs_dir) / output_file
        if self.create_cookies_file(merged_cookies, str(output_path)):
            return str(output_path)
        return None

def get_yandex_cookies_file(logs_dir: str = "logs") -> Optional[str]:
    parser = YandexCookiesParser(logs_dir)
    files = parser.get_all_yandex_cookies_files()
    return files[0] if files else None

def get_all_yandex_cookies_files(logs_dir: str = "logs") -> List[str]:
    parser = YandexCookiesParser(logs_dir)
    return parser.get_all_yandex_cookies_files()

def merge_yandex_cookies(logs_dir: str = "logs") -> Optional[str]:
    parser = YandexCookiesParser(logs_dir)
    return parser.merge_yandex_cookies()