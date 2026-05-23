# module_cookies_parser.py
import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from core.lib.module_logger_manager import LoggerManager

class CookiesParser:
    """Парсер куков из папки logs для различных почтовых сервисов"""
    
    def __init__(self, logs_dir: str = "logs", logger: LoggerManager = None):
        self.logs_dir = Path(logs_dir)
        self.logger = logger or LoggerManager("CookiesParser")
        
        # Домены для различных почтовых сервисов
        self.mail_domains = {
            'yandex': {
                'domains': [
                    'yandex.ru', '.yandex.ru', 'mail.yandex.ru', 'passport.yandex.ru',
                    'ya.ru', '.ya.ru', 'yandex.com', '.yandex.com',
                    'passport.yandex.com', 'mail.yandex.com'
                ],
                'cookie_names': ['yandex_login', 'yandexuid', 'Session_id', 'ys', 'yp']
            },
            'mailru': {
                'domains': [
                    'mail.ru', '.mail.ru', 'e.mail.ru', 'account.mail.ru',
                    'list.ru', '.list.ru', 'bk.ru', '.bk.ru', 'inbox.ru', '.inbox.ru',
                    'xmail.ru', '.xmail.ru', 'internet.ru', '.internet.ru'
                ],
                'cookie_names': ['mrcu', 'act', 'mbox', 'sdcs']
            },
            'rambler': {
                'domains': [
                    'rambler.ru', '.rambler.ru', 'mail.rambler.ru', 'id.rambler.ru',
                    'lenta.ru', '.lenta.ru', 'mail.lenta.ru'
                ],
                'cookie_names': ['rambler_id', 'rur', 'rlb_id', 'rlb_redirect']
            },
            'gmail': {
                'domains': [
                    'gmail.com', '.gmail.com', 'mail.google.com', 'accounts.google.com',
                    'google.com', '.google.com'
                ],
                'cookie_names': ['SID', 'HSID', 'SSID', 'APISID', 'SAPISID', 'NID']
            }
        }
    
    def find_cookies_files(self) -> List[Path]:
        """Рекурсивный поиск всех файлов с куками в папке logs"""
        cookies_files = []
        
        if not self.logs_dir.exists():
            self.logger.warning(f"Папка {self.logs_dir} не существует")
            return cookies_files
        
        try:
            # Рекурсивно ищем все .txt файлы
            for file_path in self.logs_dir.rglob("*.txt"):
                # Проверяем, что файл не слишком большой (больше 1MB пропускаем)
                if file_path.stat().st_size > 1024 * 1024:
                    continue
                
                # Проверяем, что файл содержит куки в формате Netscape
                if self._is_netscape_cookies_file(file_path):
                    cookies_files.append(file_path)
            
            self.logger.info(f"Найдено файлов с куками: {len(cookies_files)}")
            return cookies_files
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске файлов с куками: {e}")
            return []
    
    def _is_netscape_cookies_file(self, file_path: Path) -> bool:
        """Проверяет, является ли файл куками в формате Netscape"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = []
                for i, line in enumerate(f):
                    if i >= 10:  # Проверяем первые 10 строк
                        break
                    first_lines.append(line.strip())
                
                # Ищем признаки формата Netscape
                for line in first_lines:
                    if not line or line.startswith('#'):
                        continue
                    
                    # Формат Netscape: domain\tflag\tpath\tsecure\texpiration\tname\tvalue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        # Проверяем, что domain выглядит как домен
                        domain = parts[0]
                        if '.' in domain and any(char.isalpha() for char in domain):
                            return True
            
            return False
        except Exception:
            return False
    
    def parse_cookies_file(self, file_path: Path) -> List[Dict]:
        """Парсит файл с куками в формате Netscape"""
        cookies = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Пропускаем пустые строки и комментарии
                    if not line or line.startswith('#'):
                        continue
                    
                    # Парсим строку в формате Netscape
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
                    
                    # Конвертируем expiration
                    try:
                        expires = int(float(expiration)) if expiration != '0' else 0
                    except (ValueError, TypeError):
                        expires = 0
                    
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
    
    def _cookies_belong_to_service(self, cookies: List[Dict], service: str) -> bool:
        """Проверяет, принадлежат ли куки указанному почтовому сервису"""
        if service not in self.mail_domains:
            return False
        
        service_info = self.mail_domains[service]
        
        # Счетчики для определения принадлежности
        domain_matches = 0
        cookie_name_matches = 0
        
        for cookie in cookies:
            domain = cookie['domain']
            name = cookie['name']
            
            # Проверяем домен
            for service_domain in service_info['domains']:
                if service_domain.startswith('.'):
                    # Поддомен (например, .yandex.ru)
                    if domain.endswith(service_domain) or domain == service_domain[1:]:
                        domain_matches += 1
                        break
                else:
                    # Точное совпадение домена
                    if domain == service_domain:
                        domain_matches += 1
                        break
            
            # Проверяем имена куки
            if name in service_info['cookie_names']:
                cookie_name_matches += 1
        
        # Куки принадлежат сервису, если есть хотя бы 2 совпадения по доменам 
        # или 1 совпадение по домену + 1 по имени куки
        return domain_matches >= 2 or (domain_matches >= 1 and cookie_name_matches >= 1)
    
    def find_service_cookies(self, service: str = 'yandex') -> Dict[str, List[Dict]]:
        """
        Находит все файлы с куками для указанного почтового сервиса
        
        Returns:
            Dict[file_path, List[cookies]] - словарь с путями к файлам и списками куков
        """
        service_cookies = {}
        
        if service not in self.mail_domains:
            self.logger.error(f"Неизвестный почтовый сервис: {service}")
            return service_cookies
        
        self.logger.info(f"Поиск куков для сервиса: {service}")
        
        # Находим все файлы с куками
        cookies_files = self.find_cookies_files()
        
        if not cookies_files:
            self.logger.warning("Файлы с куками не найдены")
            return service_cookies
        
        # Анализируем каждый файл
        for file_path in cookies_files:
            try:
                cookies = self.parse_cookies_file(file_path)
                if not cookies:
                    continue
                
                # Проверяем, принадлежат ли куки целевому сервису
                if self._cookies_belong_to_service(cookies, service):
                    service_cookies[str(file_path)] = cookies
                    self.logger.info(f"Найдены куки {service} в файле: {file_path}")
            
            except Exception as e:
                self.logger.error(f"Ошибка анализа файла {file_path}: {e}")
                continue
        
        self.logger.info(f"Найдено файлов с куками {service}: {len(service_cookies)}")
        return service_cookies
    
    def get_all_yandex_cookies_files(self) -> List[str]:
        """
        Находит ВСЕ файлы с куками Яндекс (не только лучший)
        Возвращает список путей к файлам
        """
        yandex_cookies = self.find_service_cookies('yandex')
        
        if not yandex_cookies:
            self.logger.warning("Куки Яндекс не найдены")
            return []
        
        # Сортируем файлы по оценке качества (от лучшего к худшему)
        file_scores = {}
        
        for file_path, cookies in yandex_cookies.items():
            score = self._score_yandex_cookies(cookies)
            file_scores[file_path] = score
        
        # Сортируем по убыванию оценки
        sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)
        
        self.logger.info(f"Найдено файлов Яндекс: {len(sorted_files)}")
        for file_path, score in sorted_files[:5]:  # Показываем топ-5
            self.logger.info(f"  {Path(file_path).name}: оценка {score}")
        
        return [file_path for file_path, score in sorted_files]
    
    def _score_yandex_cookies(self, cookies: List[Dict]) -> int:
        """Оценивает качество куков Яндекс"""
        score = 0
        
        # Критические куки Яндекс
        critical_cookies = {
            'yandexuid',  # Основной идентификатор
            'Session_id',  # ID сессии
            'ys',          # Сессия
            'yandex_login' # Логин
        }
        
        # Важные домены
        important_domains = {
            '.yandex.ru',
            'yandex.ru', 
            'mail.yandex.ru',
            'passport.yandex.ru'
        }
        
        found_cookies = set()
        found_domains = set()
        
        for cookie in cookies:
            name = cookie['name']
            domain = cookie['domain']
            
            # Учитываем критические куки
            if name in critical_cookies:
                found_cookies.add(name)
                score += 10
            
            # Учитываем важные домены
            if domain in important_domains:
                found_domains.add(domain)
                score += 5
            
            # Дополнительные баллы за другие куки Яндекс
            if 'yandex' in name.lower():
                score += 2
        
        # Бонус за полноту набора критических куков
        completeness = len(found_cookies) / len(critical_cookies)
        score += int(completeness * 20)
        
        # Бонус за разнообразие доменов
        domain_variety = len(found_domains)
        score += domain_variety * 3
        
        return score
    
    def create_cookies_file(self, cookies: List[Dict], output_path: str) -> bool:
        """Создает файл с куками в формате Netscape"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# This file contains cookies for mail checking\n")
                f.write("# Generated by CookiesParser\n\n")
                
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
        """
        Объединяет куки Яндекс из разных файлов в один оптимальный набор
        """
        yandex_cookies = self.find_service_cookies('yandex')
        
        if not yandex_cookies:
            return None
        
        # Собираем все уникальные куки
        all_cookies = {}
        
        for file_cookies in yandex_cookies.values():
            for cookie in file_cookies:
                # Создаем уникальный ключ для куки (домен + имя)
                key = f"{cookie['domain']}|{cookie['name']}"
                
                # Если куки с таким ключом еще нет, или эта куки новее (по expiration)
                if key not in all_cookies or cookie['expiration'] > all_cookies[key]['expiration']:
                    all_cookies[key] = cookie
        
        # Создаем финальный список куков
        merged_cookies = list(all_cookies.values())
        
        if not merged_cookies:
            return None
        
        # Создаем файл с объединенными куками
        output_path = Path(self.logs_dir) / output_file
        if self.create_cookies_file(merged_cookies, str(output_path)):
            return str(output_path)
        
        return None


# Утилитарные функции для удобства
def get_yandex_cookies_file(logs_dir: str = "logs") -> Optional[str]:
    """Быстрая функция для получения файла с куками Яндекс"""
    parser = CookiesParser(logs_dir)
    files = parser.get_all_yandex_cookies_files()
    return files[0] if files else None

def get_all_yandex_cookies_files(logs_dir: str = "logs") -> List[str]:
    """Быстрая функция для получения ВСЕХ файлов с куками Яндекс"""
    parser = CookiesParser(logs_dir)
    return parser.get_all_yandex_cookies_files()

def merge_yandex_cookies(logs_dir: str = "logs") -> Optional[str]:
    """Быстрая функция для объединения куков Яндекс"""
    parser = CookiesParser(logs_dir)
    return parser.merge_yandex_cookies()