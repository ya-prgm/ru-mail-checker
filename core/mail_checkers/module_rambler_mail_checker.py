# module_rambler_mail_checker.py
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

class RamblerMailChecker:
	def __init__(self, proxy_url: str, cookies_file: str, timeout: int = 30, 
				 user_agent: str = None, logger: LoggerManager = None, 
				 result_saver: ResultSaver = None, download_html: bool = False):
		self.proxy_url = proxy_url
		self.cookies_file = cookies_file
		self.timeout = timeout
		self.user_agent = user_agent
		self.cookies_loaded = False
		self.cookiejar = None
		self.logger = logger or LoggerManager("RamblerMailChecker")
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
			return False
	
	async def check_mail(self, search_keywords: list) -> bool:
		"""Основной метод проверки почты для списка ключевых слов"""
		if not self.cookies_loaded:
			if not self.load_cookies():
				return False
		
		# Если передали один ключ вместо списка, преобразуем в список
		if isinstance(search_keywords, str):
			search_keywords = [search_keywords]
		
		# Объединяем все ключевые слова в один поисковый запрос через OR
		search_query = " OR ".join(search_keywords)
		self.logger.info(f"Проверка Rambler почты для {len(search_keywords)} ключевых слов через прокси: {self.proxy_url}")
		self.logger.info(f"Поисковый запрос: {search_query}")
		
		try:
			return await self._search_and_process(search_query, search_keywords)
		except Exception as e:
			self.logger.error(f"Ошибка при проверке почты для ключевых слов {search_keywords}: {e}")
			return False












	async def _search_and_process(self, search_query: str, original_keywords: list) -> bool:
		"""Выполнение поиска и обработка результатов"""
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
				"User-Agent": self.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
			})

			rambler_domains = [
				'.rambler.ru', '.rambler.ua', '.rambler.kz', '.rambler.com',
				'mail.rambler.ru', 'id.rambler.ru', 'pass.rambler.ru',
				'rambler.ru', 'www.rambler.ru'
			]

			for cookie in self.cookiejar:
			    if cookie.domain in rambler_domains:
			        # Устанавливаем ту же куку для mail.rambler.ru
			        self.session.cookies.set(
			            cookie.name, 
			            cookie.value, 
			            domain='mail.rambler.ru',
			            path=cookie.path or '/'
			        )
			        self.logger.debug(f"Установлена кука {cookie.name} для mail.rambler.ru")

			# Особенно важно для rsid
			rsid_cookie = next((c for c in self.cookiejar if c.name == 'rsid'), None)
			if rsid_cookie:
			    self.session.cookies.set(
			        'rsid', 
			        rsid_cookie.value, 
			        domain='mail.rambler.ru',
			        path='/'
			    )
			    self.logger.info("✅ rsid явно установлен для mail.rambler.ru")




			# === 2. ЗАПРОС ГЛАВНОЙ СТРАНИЦЫ ДЛЯ ПОЛУЧЕНИЯ КУК ===
			main_resp = await asyncio.get_event_loop().run_in_executor(
				None,
				lambda: self.session.get("https://mail.rambler.ru/folder/INBOX", timeout=30)
			)

			
			if main_resp.status_code != 200:
				self.logger.error(f"❌ Ошибка загрузки главной страницы: {main_resp.status_code}")
				return False



			ramail_resp = await asyncio.get_event_loop().run_in_executor(
				None,
				lambda: self.session.get("https://mail.rambler.su/latest/ramail-7/build/app.js", timeout=30)
			)


			
			if ramail_resp.status_code != 200:
				self.logger.error(f"❌ Ошибка загрузки главной страницы: {ramail_resp.status_code}")
				return False





			# === 3. ПОДГОТОВКА API ЗАПРОСА ДЛЯ ПОИСКА ===
			self.session.headers.update({
				"Accept": "application/json, text/plain, */*",
				"Content-Type": "application/json; charset=utf-8", 
				"Origin": "https://mail.rambler.ru",
				"Referer": f"https://mail.rambler.ru/folder/INBOX",
				"Sec-Fetch-Dest": "empty",
				"Sec-Fetch-Mode": "cors",
				"Sec-Fetch-Site": "same-origin",
				"User-Agent": self.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
				"X-Rambler-Mail-Client-Type": "b2c/mail/web",
				"X-Rambler-Mail-Client-Version": "2.9.182",
				"X-Rambler-Mail-Method": "Rambler::Mail::get_folder_messages"
			})

			# === 4. ФОРМИРОВАНИЕ PAYLOAD ДЛЯ ПОИСКА ===
			timestamp = str(int(time.time() * 1000))
			
			payload = {
				"method": "Rambler::Mail::get_folder_messages",
				"params": [{
					"folder.name": "INBOX",
					"folder.offset": 0,
					"folder.elements": 50,
					"folder.sortorder": "D",
					"filter": {
						"text": search_query
					}
				}],
				"id": timestamp,
				"rpc": "2.0"
			}

			# === 5. ВЫПОЛНЕНИЕ ПОИСКОВОГО ЗАПРОСА ===
			api_url = "https://mail.rambler.ru/api/v2"
			
			self.logger.info(f"🔍 Выполняем поиск в Rambler: '{search_query}'")
			
			resp = await asyncio.get_event_loop().run_in_executor(
				None,
				lambda: self.session.post(
					api_url,
					json=payload,
					timeout=30
				)
			)

			print(resp.text)

			# === 6. ОБРАБОТКА РЕЗУЛЬТАТОВ ===
			self.logger.info(f"📨 Статус ответа Rambler: {resp.status_code}")
			
			if resp.status_code != 200:
				self.logger.error(f"❌ Ошибка API Rambler: {resp.text[:500]}")
				return False

			try:
				data = resp.json()
				self.logger.info("✅ Ответ JSON от Rambler получен успешно")
			except json.JSONDecodeError:
				self.logger.error(f"❌ Невалидный JSON от Rambler: {resp.text[:500]}")
				return False

			# === 7. ПАРСИНГ РЕЗУЛЬТАТОВ ===
			messages = []
			
			# Правильная структура ответа: data['result'] - это словарь с полем 'folder'
			if 'result' in data and isinstance(data['result'], dict):
				print(data)
				result_data = data['result']
				folder_data = result_data.get('folder', {})
				messages = folder_data.get('messages', [])
				self.logger.info(f"📊 Найдено сообщений в Rambler: {len(messages)}")
				
				# Логируем структуру для отладки
				self.logger.debug(f"Структура ответа: folder.total_elements = {folder_data.get('total_elements', 0)}")
			else:
				self.logger.info("ℹ️ Нет результатов поиска в ответе Rambler")
				return False

			if messages:
				# Обрабатываем найденные сообщения
				emails_data = await self._extract_emails_from_search_async(messages)
				account_data = self._extract_account_data(messages)
				session_cookies = self._get_session_cookies()
				
				await self._save_final_results_async(
					account_data, 
					emails_data, 
					search_query, 
					session_cookies
				)
				
				self.logger.info("✅ Данные Rambler успешно сохранены")
				return True
			else:
				self.logger.info("ℹ️ Сообщения не найдены в Rambler")
				return False

		except requests.exceptions.Timeout:
			self.logger.error("❌ Таймаут запроса к Rambler")
			return False
		except requests.exceptions.ConnectionError:
			self.logger.error("❌ Ошибка соединения с Rambler")  
			return False
		except Exception as e:
			self.logger.error(f"❌ Неожиданная ошибка в Rambler: {str(e)}")
			import traceback
			self.logger.error(f"Трассировка: {traceback.format_exc()}")
			return False















	async def _extract_emails_from_search_async(self, messages: list) -> list:
		"""Извлечение данных писем из JSON ответа Rambler"""
		emails_data = []
		
		try:
			self.logger.info(f"Найдено сообщений в JSON Rambler: {len(messages)}")
			
			# Используем ThreadPoolExecutor для параллельного парсинга сообщений
			with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
				future_to_msg = {executor.submit(self._parse_rambler_email_message, msg, i): (msg, i) for i, msg in enumerate(messages)}
				
				for future in as_completed(future_to_msg):
					try:
						email_data = future.result()
						if email_data and email_data['from_email'] and email_data['subject']:
							emails_data.append(email_data)
							self.logger.info(f"Извлечено письмо Rambler {email_data['index'] + 1}: от {email_data['from_email']} - {email_data['subject'][:30]}...")
					except Exception as e:
						self.logger.debug(f"Ошибка парсинга сообщения Rambler: {e}")
			
		except Exception as e:
			self.logger.error(f"Ошибка извлечения писем из JSON Rambler: {e}")
		
		return emails_data

	def _parse_rambler_email_message(self, msg, index):
		"""Парсинг одного сообщения из JSON ответа Rambler"""
		email_data = {
			'from_email': '',
			'subject': '',
			'snippet': '',
			'date': '',
			'to_email': '',  # Добавляем поле получателя
			'index': index
		}
		
		try:
			# Извлекаем отправителя из массива from
			from_data = msg.get('from', [])
			if from_data and len(from_data) > 0:
				from_item = from_data[0]
				if len(from_item) >= 3:
					name_part = from_item[1] if from_item[1] else from_item[0]
					domain_part = from_item[2]
					if name_part and domain_part:
						email_data['from_email'] = f"{name_part}@{domain_part}"
			
			# Извлекаем получателя из массива to
			to_data = msg.get('to', [])
			if to_data and len(to_data) > 0:
				to_item = to_data[0]
				if len(to_item) >= 3:
					to_name_part = to_item[1] if to_item[1] else to_item[0]
					to_domain_part = to_item[2]
					if to_name_part and to_domain_part:
						email_data['to_email'] = f"{to_name_part}@{to_domain_part}"
			
			# Если не нашли отправителя, пропускаем
			if not email_data['from_email']:
				return None
			
			# Извлекаем тему
			email_data['subject'] = msg.get('subject', '')
			
			# Извлекаем дату (timestamp в секундах)
			date_timestamp = msg.get('rdate', 0)
			if date_timestamp:
				email_data['date'] = datetime.fromtimestamp(date_timestamp).strftime('%Y-%m-%d %H:%M:%S')
			
			# Извлекаем сниппет
			email_data['snippet'] = msg.get('snippet', '')
			
			return email_data
		
		except Exception as e:
			self.logger.debug(f"Ошибка парсинга сообщения Rambler {index}: {e}")
			return None

	def _extract_account_data(self, messages: list = None) -> dict:
		"""Извлечение данных аккаунта Rambler из писем или куков"""
		account_data = {
			'name': '',
			'email': '',
			'country': ''
		}
		
		try:
			# Сначала пытаемся найти email получателя из писем
			if messages:
				for msg in messages:
					to_data = msg.get('to', [])
					if to_data and len(to_data) > 0:
						to_item = to_data[0]
						if len(to_item) >= 3:
							to_name_part = to_item[1] if to_item[1] else to_item[0]
							to_domain_part = to_item[2]
							if to_name_part and to_domain_part:
								account_data['email'] = f"{to_name_part}@{to_domain_part}"
								account_data['name'] = to_name_part
								self.logger.info(f"Найден email получателя из письма: {account_data['email']}")
								return account_data
			
			# Если не нашли в письмах, ищем в куках
			rambler_login = ""
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
							if name == 'rlogin' and value:
								rambler_login = value
								break
			except Exception as e:
				self.logger.error(f"Ошибка чтения куков Rambler: {e}")
			
			if rambler_login:
				account_data['email'] = f"{rambler_login}@rambler.ru"
				account_data['name'] = rambler_login
				self.logger.info(f"Найден логин Rambler из куков: {rambler_login}")
			else:
				account_data['email'] = 'unknown@rambler.ru'
				account_data['name'] = 'unknown'
		
		except Exception as e:
			self.logger.error(f"Ошибка извлечения данных аккаунта Rambler: {e}")
			account_data['email'] = 'error@rambler.ru'
		
		self.logger.info(f"Извлечены данные аккаунта Rambler: {account_data}")
		return account_data

	def _get_session_cookies(self) -> list:
		"""Возвращает только Rambler-куки из исходного файла"""
		netscape_cookies = []

		try:
			rambler_domains = [
				'.rambler.ru', '.rambler.ua', '.rambler.kz', '.rambler.com',
				'mail.rambler.ru', 'id.rambler.ru', 'pass.rambler.ru',
				'rambler.ru', 'www.rambler.ru'
			]
			
			with open(self.cookies_file, 'r', encoding='utf-8') as f:
				for line in f:
					line = line.strip()
					if line and not line.startswith('#'):
						parts = line.split('\t')
						if len(parts) >= 7:
							domain = parts[0]
							if any(rambler_domain in domain for rambler_domain in rambler_domains):
								netscape_cookies.append(line)
			
			self.logger.info(f"Отфильтровано {len(netscape_cookies)} Rambler-кук из исходного файла")
			
		except Exception as e:
			self.logger.error(f"Ошибка при фильтрации кук Rambler: {e}")
		
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
				self.logger.info(f"✅ Результаты Rambler успешно сохранены: {file_path}")
			else:
				self.logger.error("❌ Ошибка сохранения результатов Rambler")
				
		except Exception as e:
			self.logger.error(f"Ошибка при сохранении финальных результатов Rambler: {e}")