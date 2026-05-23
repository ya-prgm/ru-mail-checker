# module_yandex_mail_checker.py
import re
import time
import asyncio
import json
from datetime import datetime
from curl_cffi import requests
from requests.cookies import RequestsCookieJar
from core.lib.module_logger_manager import LoggerManager
from core.lib.module_saving_results import ResultSaver
import os
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

class YandexMailChecker:
    def __init__(self, proxy_url: str, cookies_file: str, timeout: int = 30, 
                 user_agent: str = None, logger: LoggerManager = None, 
                 result_saver: ResultSaver = None, download_html: bool = False, on_status_update=None):

        self.on_status_update = on_status_update
        self.proxy_url = proxy_url
        self.cookies_file = cookies_file
        self.timeout = timeout
        self.user_agent = user_agent
        self.cookies_loaded = False
        self.cookiejar = None
        self.logger = logger or LoggerManager("YandexMailChecker")
        self.result_saver = result_saver
        self.download_html = download_html
        
        self.session = None
        self.max_workers = 10
    
    def load_cookies(self) -> bool:
        """Загрузка куков из файла"""
        cookiejar = RequestsCookieJar()
        try:
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) == 7:
                        domain = parts[0]
                        tailmatch = parts[1] == 'TRUE'
                        path = parts[2]
                        secure = parts[3] == 'TRUE'
                        expiry_str = parts[4]
                        name = parts[5]
                        value = parts[6]
                        
                        expiry = int(expiry_str) if expiry_str != '0' else None
                        
                        if tailmatch and not domain.startswith('.'):
                            domain = '.' + domain
                        
                        cookiejar.set(
                            name=name,
                            value=value,
                            domain=domain,
                            path=path,
                            secure=secure,
                            expires=expiry,
                            rest={'HttpOnly': False}
                        )
            self.cookiejar = cookiejar
            self.cookies_loaded = True
            self.logger.info(f"Загружено {len(cookiejar)} кук")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кук: {e}")
            self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
            return False
    
    async def check_mail(self, search_domains: list) -> bool:
        """Основной метод проверки почты для списка доменов"""
        if not self.cookies_loaded:
            if not self.load_cookies():
                return False
        
        search_query = " OR ".join(search_domains)
        self.logger.info(f"Проверка почты для доменов: {search_domains} через прокси: {self.proxy_url}")
        
        try:
            return await self._search_and_process(search_query)
        except Exception as e:
            self.logger.error(f"Ошибка при проверке почты для доменов {search_domains}: {e}")
            return False
















    async def _search_and_process(self, keyword: str) -> bool:
        import re
        import json
        import time
        import random
        from bs4 import BeautifulSoup

        try:
            # === 1. ИНИЦИАЛИЗАЦИЯ СЕССИИ ===
            self.session = requests.Session(impersonate="chrome", timeout=30)
            self.session.verify = False
            if self.proxy_url:
                self.session.proxies = {"http": self.proxy_url, "https": self.proxy_url}

            self.session.cookies = self.cookiejar

            self.session.headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate", 
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
            })

            # === 2. ЗАПРОС ГЛАВНОЙ СТРАНИЦЫ И ПАРСИНГ КОНФИГОВ ===
            main_resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.session.get("https://mail.360.yandex.ru/", timeout=30)
            )
            
            if main_resp.status_code != 200:
                self.logger.error(f"❌ Ошибка загрузки главной страницы: {main_resp.status_code}")
                self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
                return False


            # === 3. ИЗВЛЕЧЕНИЕ ДАННЫХ ИЗ HTML КОНФИГОВ ===
            
            # 3.1. insert-js - UID и CKEY (ОСНОВНОЙ ИСТОЧНИК!)
            insert_js_match = re.search(r'<script id="insert-js"[^>]*>(.*?)</script>', main_resp.text, re.DOTALL)
            if not insert_js_match:
                self.logger.error("❌ Не найден insert-js в HTML")
                self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
                return False
                
            try:
                insert_data = json.loads(insert_js_match.group(1).strip())
                uid = insert_data.get("uid")
                
                # Получаем ckey из prefetched -> account-information -> data -> ckey
                prefetched = insert_data.get("prefetched", {})
                models = prefetched.get("models", {})
                account_info = models.get("account-information", {})
                account_data = account_info.get("data", {})
                ckey = account_data.get("ckey")
                
                self.logger.info(f"✅ UID из insert-js: {uid}")
                self.logger.info(f"✅ Ckey из insert-js: {ckey[:30]}..." if ckey else "❌ Ckey не найден в insert-js")
                
            except json.JSONDecodeError as e:
                self.logger.error(f"❌ Ошибка парсинга insert-js: {e}")
                self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
                return False

            if not uid or not ckey:
                self.logger.error("❌ UID или Ckey не найдены в insert-js")
                self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
                return False

            session_config_match = re.search(r'<script id="config-session"[^>]*>(.*?)</script>', main_resp.text, re.DOTALL)
            connection_id = None
            exp_boxes = []
            experiments = []
            
            if session_config_match:
                try:
                    session_config = json.loads(session_config_match.group(1).strip())
                    connection_id = session_config.get("connectionId")
                    exp_boxes = session_config.get("expBoxes", [])
                    experiments = session_config.get("experiments", [])
                    self.logger.info(f"✅ Connection ID: {connection_id}")
                except json.JSONDecodeError:
                    self.logger.warning("⚠️ Не удалось распарсить config-session")


            env_config_match = re.search(r'<script id="config-environment"[^>]*>(.*?)</script>', main_resp.text, re.DOTALL)
            version = "235.1.0"
            product = "RUS"
            
            if env_config_match:
                try:
                    env_config = json.loads(env_config_match.group(1).strip())
                    version = env_config.get("version", version)
                    product = env_config.get("product", product)
                except json.JSONDecodeError:
                    self.logger.warning("⚠️ Не удалось распарсить config-environment")


            self.session.headers.update({
                "Accept": "application/json, text/plain, */*",
                "Content-Type": "application/json; charset=utf-8", 
                "Origin": "https://mail.360.yandex.ru",
                "Referer": "https://mail.360.yandex.ru/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest"
            })

            # === 5. ФОРМИРОВАНИЕ PAYLOAD ===
            timestamp = str(int(time.time() * 1000))
            

            if not connection_id:
                connection_id = f"LIZA-{random.randint(10000000, 99999999)}-{timestamp}"
            
            payload = {
                "_ckey": ckey,
                "_uid": uid,
                "_locale": "ru",
                "_timestamp": timestamp,
                "_product": product,
                "_connection_id": connection_id,
                "_exp": ";".join(exp_boxes) if exp_boxes else "",
                "_eexp": ";".join(experiments) if experiments else "", 
                "_service": "LIZA",
                "_version": version,
                "_messages_per_page": "50",
                "_mailboxUid": "",
                "models": [{
                    "name": "messages",
                    "params": {
                        "current_folder": True,
                        "with_pins": "yes",
                        "sort_type": "date",
                        "mailboxUid": None,
                        "threaded": "yes", 
                        "tabId": "relevant",
                        # Параметры поиска
                        "request": keyword,
                        "search": "search",
                        "count": 50,
                        "first": 0,
                        "reqid": timestamp + str(uid)
                    },
                    "meta": {
                        "requestAttempt": 1
                    }
                }]
            }


            search_url = "https://mail.360.yandex.ru/web-api/models/liza1?_m=messages"
            
            self.logger.info(f"🔍 Выполняем поиск: '{keyword}'")
            
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.session.post(
                    search_url,
                    json=payload,
                    timeout=30
                )
            )

            # === 7. ОБРАБОТКА РЕЗУЛЬТАТОВ (ИСПРАВЛЕННАЯ ЧАСТЬ) ===
            self.logger.info(f"📨 Статус ответа: {resp.status_code}")
            
            if resp.status_code != 200:
                self.logger.error(f"❌ Ошибка API: {resp.text[:500]}")
                self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
                return False

            try:
                data = resp.json()
                self.logger.info("✅ Ответ JSON получен успешно")
            except json.JSONDecodeError:
                self.logger.error(f"❌ Невалидный JSON: {resp.text[:500]}")
                self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
                return False


            messages = []
            for model in data.get("models", []):
                if model.get("name") == "messages":
                    result = model.get("data", {})
                    
                    if "message" in result:
                        messages = result.get("message", [])
                        break
                    
                    elif "messages" in result:
                        messages = result.get("messages", [])
                        break
                    
                    result_data = model.get("result", {})
                    if "messages" in result_data:
                        messages = result_data.get("messages", [])
                        break

            if messages:
                first_model = next((m for m in data.get("models", []) if m.get("name") == "messages"), None)
                if first_model:
                    details = first_model.get("data", {}).get("details", {})
                    total_found = details.get("total-found", 0)

            if messages:
                # Обрабатываем найденные сообщения
                emails_data = await self._extract_emails_from_search_async(resp.text)
                account_data = self._extract_account_data(resp.text)
                session_cookies = self._get_session_cookies()
                
                await self._save_final_results_async(
                    account_data, 
                    emails_data, 
                    keyword, 
                    session_cookies
                )

                self.on_status_update(email=account_data['email'], status_account=True, search_status=True, count_hits=len(messages))



                
                self.logger.info("✅ Данные успешно сохранены")
                return True
                
            else:
                self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
                self.logger.info("ℹ️ Сообщения не найдены в ответе")
                # Логируем структуру ответа для отладки
                self.logger.debug(f"Структура ответа: {json.dumps(data, indent=2)[:1000]}...")
                return False

        except requests.exceptions.Timeout:
            self.logger.error("❌ Таймаут запроса")
            self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
            return False
        except requests.exceptions.ConnectionError:
            self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
            self.logger.error("❌ Ошибка соединения")  
            return False
        except Exception as e:
            self.on_status_update(email=None, status_account=False, search_status=False, count_hits=0)
            self.logger.error(f"❌ Неожиданная ошибка: {str(e)}")
            import traceback
            self.logger.error(f"Трассировка: {traceback.format_exc()}")
            return False












    async def _extract_emails_from_search_async(self, json_content: str) -> list:
        """Извлечение данных писем из JSON ответа"""
        emails_data = []
        
        try:
            data = json.loads(json_content)
            messages = data.get('models', [{}])[0].get('data', {}).get('message', [])
            
            self.logger.info(f"Найдено сообщений в JSON: {len(messages)}")
            
            # Используем ThreadPoolExecutor для параллельного парсинга сообщений
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_msg = {executor.submit(self._parse_email_message_json, msg, i): (msg, i) for i, msg in enumerate(messages)}
                
                for future in as_completed(future_to_msg):
                    try:
                        email_data = future.result()
                        if email_data and email_data['from_email'] and email_data['subject']:
                            emails_data.append(email_data)
                            self.logger.info(f"Извлечено письмо {email_data['index'] + 1}: от {email_data['from_email']} - {email_data['subject'][:30]}...")
                    except Exception as e:
                        self.logger.debug(f"Ошибка парсинга сообщения: {e}")
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения писем из JSON: {e}")
        
        return emails_data

    def _parse_email_message_json(self, msg, index):
        """Парсинг одного сообщения из JSON с извлечением EMAIL адреса"""
        email_data = {
            'from_email': '',
            'subject': '',
            'snippet': '',
            'date': '',
            'index': index
        }
        
        try:
            # Извлекаем from_email из fields
            fields = msg.get('field', [])
            for field in fields:
                if field.get('type') == 'from':
                    # Используем только email, без имени
                    email_data['from_email'] = field.get('email', '')
                    break
            
            # Если не нашли, пропускаем
            if not email_data['from_email']:
                return None
            
            # Извлекаем тему
            email_data['subject'] = msg.get('subject', '')
            
            # Извлекаем дату
            date_info = msg.get('date', {})
            email_data['date'] = date_info.get('iso', '') or f"{date_info.get('chunks', {}).get('year', '')}-{date_info.get('chunks', {}).get('month', ''):02d}-{date_info.get('chunks', {}).get('date', ''):02d} {date_info.get('chunks', {}).get('hours', ''):02d}:{date_info.get('chunks', {}).get('minutes', ''):02d}"
            
            # Извлекаем сниппет
            email_data['snippet'] = msg.get('firstline', '')
            
            return email_data
        
        except Exception as e:
            self.logger.debug(f"Ошибка парсинга сообщения {index}: {e}")
            return None

    def _extract_account_data(self, json_content: str) -> dict:
        """Извлечение данных аккаунта из JSON или куков"""
        account_data = {
            'name': '',
            'email': '',
            'country': ''
        }
        
        try:
            # Сначала пытаемся из куков (как в исходном)
            yandex_login = ""
            try:
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            name = parts[5].strip()
                            value = parts[6].strip()
                            if name == 'yandex_login' and value:
                                yandex_login = value
                                break
            except Exception as e:
                self.logger.error(f"Ошибка чтения куков: {e}")
            
            if yandex_login:
                account_data['email'] = f"{yandex_login}@yandex.com"
                account_data['name'] = yandex_login
                self.logger.info(f"Найден логин из куков: {yandex_login}, email: {account_data['email']}")
            else:
                # Если не из куков, пытаемся из JSON (uid)
                try:
                    data = json.loads(json_content)
                    uid = data.get('uid', '')
                    if uid:
                        account_data['email'] = f"uid_{uid}@yandex.com"  # Placeholder, если нужно
                except:
                    pass
                if not account_data['email']:
                    account_data['email'] = 'unknown@yandex.com'
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения данных аккаунта: {e}")
            account_data['email'] = 'error@yandex.com'
        
        self.logger.info(f"Извлечены данные аккаунта: {account_data}")
        return account_data

    def _get_session_cookies(self) -> list:
        """Возвращает только Яндекс-куки из исходного файла"""
        netscape_cookies = []

        try:
            yandex_domains = [
                '.yandex.ru', '.ya.ru', '.yandex.com', '.yandex.ua', '.yandex.kz', '.yandex.by',
                '.yandex.net', '.yandex.org', '.yandex.com.tr', '.yandex.az', '.yandex.fr',
                'passport.yandex.ru', 'passport.ya.ru', 'passport.yandex.com', 
                'mail.yandex.ru', 'mail.ya.ru', 'mail.yandex.com',
                'yandex.ru', 'ya.ru', 'www.yandex.ru', 'www.ya.ru',
            ]
            
            with open(self.cookies_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('\t')
                        if len(parts) >= 7:
                            domain = parts[0]
                            if any(yandex_domain in domain for yandex_domain in yandex_domains):
                                netscape_cookies.append(line)
            
            self.logger.info(f"Отфильтровано {len(netscape_cookies)} Яндекс-кук из исходного файла")
            
        except Exception as e:
            self.logger.error(f"Ошибка при фильтрации кук: {e}")
        
        return netscape_cookies

    async def _save_final_results_async(self, account_data: dict, emails_data: list, search_query: str, session_cookies: list):
        """Асинхронное сохранение финальных результатов через ResultSaver"""
        if not self.result_saver:
            self.logger.warning("ResultSaver не инициализирован, сохранение невозможно")
            return
        
        try:
            loop = asyncio.get_running_loop()
            file_path = await loop.run_in_executor(
                None,
                lambda: self.result_saver.save_email_results(
                    account_data=account_data,
                    emails_data=emails_data,
                    search_query=search_query,
                    cookies_path=self.cookies_file,
                    proxy_url=self.proxy_url,
                    session_cookies=session_cookies
                )
            )
            
            if file_path:
                self.logger.info(f"✅ Результаты успешно сохранены: {file_path}")
            else:
                self.logger.error("❌ Ошибка сохранения результатов")
                
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении финальных результатов: {e}")