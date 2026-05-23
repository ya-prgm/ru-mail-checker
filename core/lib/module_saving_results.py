# module_saving_results.py
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from core.lib.module_logger_manager import LoggerManager

class ResultSaver:
    def __init__(self, base_output_dir: str = "results", logger: LoggerManager = None):
        self.base_output_dir = base_output_dir
        self.logger = logger or LoggerManager("ResultSaver")
        
        # Создаем базовую директорию если не существует
        Path(self.base_output_dir).mkdir(parents=True, exist_ok=True)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Очистка имени файла от недопустимых символов"""
        return re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    def _extract_email_from_sender(self, sender_data: str) -> str:
        """Извлечение чистого email адреса из данных отправителя"""
        if not sender_data:
            return "unknown"
        
        # Пробуем найти email в формате "Name <email@domain.com>"
        email_match = re.search(r'<([^>]+)>', sender_data)
        if email_match:
            return email_match.group(1)
        
        # Пробуем найти email в формате "email@domain.com"
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender_data)
        if email_match:
            return email_match.group(0)
        
        # Если email не найден, возвращаем оригинальную строку
        return sender_data
    
    def _get_email_domain(self, email: str) -> str:
        """Определение домена почтового сервиса из email"""
        if not email or '@' not in email:
            return "other"
        
        domain = email.lower().split('@')[1]
        
        # Определяем почтовый сервис по домену
        if 'yandex' in domain:
            return 'yandex'
        elif 'rambler' in domain:
            return 'rambler'
        elif 'mail.ru' in domain or 'bk.ru' in domain or 'inbox.ru' in domain or 'list.ru' in domain:
            return 'mailru'
        elif 'gmail.com' in domain:
            return 'gmail'
        elif 'outlook.com' in domain or 'hotmail.com' in domain:
            return 'outlook'
        elif 'yahoo.com' in domain:
            return 'yahoo'
        elif 'protonmail.com' in domain or 'proton.me' in domain:
            return 'protonmail'
        else:
            return 'other'
    
    def _group_emails_by_sender_email(self, emails_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Группировка писем по email отправителя"""
        grouped_emails = {}
        
        for email in emails_data:
            from_data = email.get('from_email', '')
            sender_email = self._extract_email_from_sender(from_data)
            
            if not sender_email:
                continue
                
            if sender_email not in grouped_emails:
                grouped_emails[sender_email] = []
            grouped_emails[sender_email].append(email)
        
        return grouped_emails
    
    def _generate_filename(self, account_email: str, sender_email: str, message_count: int) -> str:
        """Генерация имени файла в формате: (кол-во_писем) [отправитель] [почта_аккаунта].txt"""
        sanitized_sender = self._sanitize_filename(sender_email)
        sanitized_account = self._sanitize_filename(account_email)
        
        return f"({message_count}) [{sanitized_sender}] [{sanitized_account}].txt"
    
    def save_email_results(self, 
                         account_data: Dict,
                         emails_data: List[Dict],
                         search_query: str,
                         cookies_path: str,
                         proxy_url: str,
                         session_cookies: List) -> str:
        """
        Сохранение результатов найденных писем
        
        Args:
            account_data: Данные аккаунта {name, email, country}
            emails_data: Список писем [{from_email, subject, snippet, date}]
            search_query: Поисковый запрос (ключевое слово)
            cookies_path: Путь к файлу с куками
            proxy_url: URL прокси
            session_cookies: Куки в формате Netscape
            
        Returns:
            Путь к первому сохраненному файлу
        """
        saved_paths = []
        
        try:
            # Группируем письма по email отправителя
            grouped_emails = self._group_emails_by_sender_email(emails_data)
            
            if not grouped_emails:
                self.logger.warning("Нет писем для сохранения")
                return ""
            
            # Определяем email аккаунта и его домен
            account_email = account_data.get('email', 'unknown')
            account_domain = self._get_email_domain(account_email)
            
            # Создаем основную папку для домена (yandex, rambler, mailru и т.д.)
            domain_dir = Path(self.base_output_dir) / account_domain
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.info(f"Сохранение результатов в папку: {account_domain}")
            
            # Сохраняем письма для каждого отправителя отдельно
            for sender_email, sender_emails in grouped_emails.items():
                try:
                    # Создаем папку для отправителя (используем только email)
                    folder_name = self._sanitize_filename(sender_email)
                    sender_dir = domain_dir / folder_name
                    sender_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Кол-во писем от этого отправителя
                    message_count = len(sender_emails)
                    
                    # Генерируем имя файла
                    filename = self._generate_filename(account_email, sender_email, message_count)
                    file_path = sender_dir / filename
                    
                    # Форматируем содержимое
                    content = self._format_content(
                        account_data, 
                        sender_emails, 
                        search_query, 
                        cookies_path, 
                        session_cookies
                    )
                    
                    # Проверяем, что content не None и является строкой
                    if content is None:
                        self.logger.error(f"Содержимое для сохранения равно None для отправителя {sender_email}")
                        content = f"Ошибка: содержимое писем недоступно для отправителя {sender_email}"
                    
                    # Сохраняем файл
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    saved_paths.append(str(file_path))
                    self.logger.info(f"Сохранены письма от {sender_email} в {account_domain}: {file_path}")
                    
                except Exception as e:
                    self.logger.error(f"Ошибка сохранения писем от {sender_email}: {e}")
            
            if saved_paths:
                self.logger.info(f"Всего сохранено файлов в папке {account_domain}: {len(saved_paths)}")
                return saved_paths[0]  # Возвращаем путь к первому файлу
            else:
                return ""
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения результатов: {e}")
            return ""

    def _format_content(self, 
                       account_data: Dict, 
                       emails_data: List[Dict],
                       search_query: str,
                       cookies_path: str,
                       session_cookies: List) -> str:
        """Форматирование содержимого файла"""
        lines = []
        
        # Заголовок с данными аккаунта
        lines.append(f"– Name: {account_data.get('name', '')}")
        lines.append(f"– Email: {account_data.get('email', '')}")
        lines.append(f"– Country: {account_data.get('country', '')}")
        lines.append(f"– Search Query: {search_query}")
        lines.append(f"– Cookies: {cookies_path}")
        lines.append("")
        
        # Функция для парсинга даты с разными форматами
        def parse_date(date_str: str) -> datetime:
            # Словарь для русских месяцев
            russian_months = {
                'янв': '01',
                'фев': '02',
                'мар': '03',
                'апр': '04',
                'май': '05',
                'июн': '06',
                'июл': '07',
                'авг': '08',
                'сен': '09',
                'окт': '10',
                'ноя': '11',
                'дек': '12'
            }
            
            # Преобразование русских месяцев
            parts = date_str.lower().split()
            if len(parts) >= 2 and parts[1] in russian_months:
                day = parts[0]
                month = russian_months[parts[1]]
                year = datetime.now().year if len(parts) < 3 else parts[2]
                time_part = '' if len(parts) < 4 else f' {parts[3]}'
                date_str = f"{day}.{month}.{year}{time_part}"
            
            formats = [
                '%Y-%m-%dT%H:%M:%S',  # 2023-01-06T11:08:42 (ДОБАВЛЕН)
                '%Y-%m-%d %H:%M:%S',  # 2024-11-20 23:35:19
                '%d.%m.%Y %H:%M:%S',  # 20.11.2024 23:35:19
                '%d.%m.%y %H:%M:%S',  # 20.11.24 23:35:19
                '%d.%m.%Y %H:%M',     # 20.11.2024 23:35
                '%d.%m.%y %H:%M',     # 20.11.24 23:35
                '%d.%m.%Y',           # 20.11.2024
                '%d.%m.%y',           # 20.11.24
                '%Y-%m-%d',           # 2024-11-20
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    pass
            self.logger.warning(f"Не удалось спарсить дату: {date_str}")
            return datetime.min
        
        # Сортируем письма по дате (новые сверху)
        sorted_emails = sorted(
            emails_data,
            key=lambda x: parse_date(x.get('date', '0000-00-00 00:00:00')),
            reverse=True
        )
        
        # Данные писем
        for i, email in enumerate(sorted_emails, 1):
            # Извлекаем чистый email из данных отправителя
            from_data = email.get('from_email', '')
            clean_email = self._extract_email_from_sender(from_data)
            
            # Обеспечиваем, что все значения являются строками и не None
            subject = email.get('subject', '')
            snippet = email.get('snippet', '')
            date = email.get('date', '')
            
            # Преобразуем None в пустые строки
            subject = subject if subject is not None else ''
            snippet = snippet if snippet is not None else ''
            date = date if date is not None else ''
            clean_email = clean_email if clean_email is not None else ''
            
            lines.append(f"From: {clean_email}")
            lines.append(f"Subject: {subject}")
            lines.append(f"Snippet: {snippet}")
            lines.append(f"Date: {date}")
            
            if i < len(sorted_emails):
                lines.append("")  # Разделитель между письмами
        
        # Куки в формате Netscape (ТОЛЬКО если они есть)
        if session_cookies:
            lines.append("")
            lines.append("# Session Cookies (Netscape format):")
            # Очищаем каждую строку куков от лишних пробелов в начале и конце
            # и убеждаемся, что каждая строка не None
            cleaned_cookies = []
            for cookie_line in session_cookies:
                if cookie_line is not None:
                    cleaned_cookies.append(cookie_line.strip())
            lines.extend(cleaned_cookies)
        
        # Объединяем все строки и убеждаемся, что результат не None
        result = '\n'.join(lines)
        return result if result is not None else ""

    def save_search_html(self, html_content: str, search_query: str, proxy_url: str, ip: str, account_email: str = None):
        """Сохранение HTML результатов поиска для отладки"""
        try:
            # Определяем домен для сохранения отладочной информации
            account_domain = "unknown"
            if account_email:
                account_domain = self._get_email_domain(account_email)
            
            debug_dir = Path(self.base_output_dir) / account_domain / "debug" / "search_results"
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = int(datetime.now().timestamp())
            sanitized_query = self._sanitize_filename(search_query)
            filename = f"SEARCH_{sanitized_query}_{ip}_{timestamp}.html"
            file_path = debug_dir / filename
            
            # Убеждаемся, что html_content не None
            if html_content is None:
                html_content = "<!-- HTML content is None -->"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"<!-- ПРОКСИ: {proxy_url} | IP: {ip} | Запрос: {search_query} | Время: {datetime.now()} -->\n")
                f.write(html_content)
            
            self.logger.debug(f"Сохранен HTML поиска в {account_domain}: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения HTML поиска: {e}")

    def get_saved_domains(self) -> List[str]:
        """Получение списка доменов, для которых есть сохраненные результаты"""
        domains = []
        base_path = Path(self.base_output_dir)
        
        if base_path.exists():
            for item in base_path.iterdir():
                if item.is_dir() and item.name not in ['debug', 'other']:
                    domains.append(item.name)
        
        return sorted(domains)

    def get_results_count_by_domain(self, domain: str) -> int:
        """Получение количества сохраненных результатов для конкретного домена"""
        domain_path = Path(self.base_output_dir) / domain
        if not domain_path.exists():
            return 0
        
        count = 0
        for item in domain_path.iterdir():
            if item.is_dir():  # Папка отправителя
                count += len(list(item.glob("*.txt")))
        
        return count