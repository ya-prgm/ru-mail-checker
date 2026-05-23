# 📧 Чекер Почты на Запросах

Многофункциональный инструмент для автоматической проверки и поиска писем в почтовых ящиках популярных российских сервисов. Позволяет находить письма по заданным ключевым словам, автоматически сохранять результаты и работать через прокси.

Telegram: @ya_prgm

Telegram: @ya_prgm

Telegram: @ya_prgm


## 📋 Содержание

- [Возможности](#возможности)
- [Поддерживаемые почтовые сервисы](#поддерживаемые-почтовые-сервисы)
- [Структура проекта](#структура-проекта)
- [Требования и установка](#требования-и-установка)
- [Быстрый старт](#быстрый-старт)
- [Подробная документация](#подробная-документация)
  - [Формат файлов cookies](#формат-файлов-cookies)
  - [Работа с прокси](#работа-с-прокси)
  - [Модули проверки почты](#модули-проверки-почты)
  - [Парсеры cookies](#парсеры-cookies)
  - [Сохранение результатов](#сохранение-результатов)
- [Примеры использования](#примеры-использования)
- [Конфигурация и настройки](#конфигурация-и-настройки)
- [Логирование](#логирование)
- [FAQ и устранение проблем](#faq-и-устранение-проблем)
- [Лицензия](#лицензия)

---

## ✨ Возможности

- **Мультиплатформенность**: Поддержка Яндекс.Почты, Mail.ru и Рамбler
- **Поиск по ключевым словам**: Находит письма по заданным запросам
- **Автоматическое сохранение**: Результаты сохраняются в структурированном виде
- **Ротация прокси**: Встроенный менеджер прокси с автоматической проверкой работоспособности
- **Гибкая работа с cookies**: Поддержка различных форматов файлов cookies
- **Параллельная обработка**: Многопоточная обработка писем для повышения скорости
- **Детальное логирование**: Полная информация о выполнении операций
- **Интерактивный браузер**: Возможность запуска браузера с загруженными cookies
- **Экспорт результатов**: Сохранение в удобном формате для дальнейшего анализа

---

## 🏢 Поддерживаемые почтовые сервисы

| Сервис | Домены | Особенности |
|--------|--------|-------------|
| **Яндекс.Почта** | yandex.ru, ya.ru, yandex.com | Поиск через API mail.360.yandex.ru |
| **Mail.ru** | mail.ru, list.ru, bk.ru, inbox.ru | Работа с light.mail.ru |
| **Рамблер** | rambler.ru, lenta.ru | API Rambler Mail |

---

## 📁 Структура проекта

```
📦 checker-emails/
├── 📄 README.md                    # Документация проекта
├── 📄 browser.py                   # Запуск браузера с cookies
│
└── 📂 core/
    ├── 📂 cookies_parsers/         # Парсеры cookies для сервисов
    │   ├── yandex_cookies_parser.py
    │   ├── mailru_cookies_parser.py
    │   └── rambler_cookies_parser.py
    │
    ├── 📂 mail_checkers/           # Модули проверки почты
    │   ├── module_yandex_mail_checker.py
    │   ├── module_mailru_mail_checker.py
    │   └── module_rambler_mail_checker.py
    │
    └── 📂 lib/                     # Библиотечные модули
        ├── module_cookies_parser.py    # Универсальный парсер cookies
        ├── module_logger_manager.py    # Менеджер логирования
        ├── module_proxy_manager.py     # Менеджер прокси
        └── module_saving_results.py    # Сохранение результатов
```

---

## 🔧 Требования и установка

### Системные требования

- **Python**: версия 3.8 или выше
- **ОС**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 20.04+)
- **Интернет-соединение**: стабильное подключение для работы с API почтовых сервисов

### Установка зависимостей

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/mail-checker.git
cd mail-checker

# Установка зависимостей
pip install -r requirements.txt
```

### Необходимые Python-пакеты

```
curl_cffi>=0.5.0          # HTTP-клиент с эмуляцией браузера
playwright>=1.40.0        # Управление браузером
aiohttp>=3.9.0            # Асинхронный HTTP-клиент
aiohttp-socks>=0.8.0      # SOCKS5 прокси для aiohttp
beautifulsoup4>=4.12.0    # Парсинг HTML
lxml>=4.9.0               # Парсер для BS4
requests>=2.31.0          # Синхронный HTTP-клиент
```

### Установка Playwright (для browser.py)

```bash
# Установка браузеров для Playwright
python -m playwright install chromium
python -m playwright install firefox
```

---

## 🚀 Быстрый старт

### 1. Подготовка cookies

Создайте файл `cookies.txt` в формате Netscape:

```
# Netscape HTTP Cookie File
.yandex.ru    TRUE    /    TRUE    1735689600    yandex_login    mylogin
.yandex.ru    TRUE    /    TRUE    1735689600    yandexuid    123456789
.mail.rambler.ru    TRUE    /    FALSE    1735689600    rlogin    myemail
```

### 2. Запуск проверки почты

```python
from core.mail_checkers import YandexMailChecker
from core.lib import LoggerManager, ResultSaver

# Инициализация компонентов
logger = LoggerManager("MyApp")
saver = ResultSaver(base_output_dir="results")

# Создание чекера
checker = YandexMailChecker(
    proxy_url="http://proxy.example.com:8080",
    cookies_file="cookies.txt",
    logger=logger,
    result_saver=saver
)

# Загрузка cookies
checker.load_cookies()

# Проверка почты с поиском
result = await checker.check_mail(search_domains=["testmail", "example"])
```

### 3. Запуск браузера с cookies

```bash
python browser.py
```

---

## 📖 Подробная документация

### Формат файлов cookies

Проект использует формат **Netscape HTTP Cookie File** — стандартный формат, экспортируемый большинством браузерных расширений для работы с cookies.

#### Структура файла

Каждая строка файла содержит 7 полей, разделённых табуляцией:

```
DOMAIN    FLAG    PATH    SECURE    EXPIRATION    NAME    VALUE
```

| Поле | Описание | Пример |
|------|----------|--------|
| `DOMAIN` | Домен cookie (с точкой для поддоменов) | `.yandex.ru` |
| `FLAG` | Флаг tailmatch (TRUE/FALSE) | `TRUE` |
| `PATH` | Путь на сайте | `/` |
| `SECURE` | Требуется ли HTTPS (TRUE/FALSE) | `TRUE` |
| `EXPIRATION` | Время истечения (Unix timestamp) | `1735689600` |
| `NAME` | Имя cookie | `yandex_login` |
| `VALUE` | Значение cookie | `mylogin123` |

#### Пример файла cookies.txt

```txt
# Netscape HTTP Cookie File
# Этот файл содержит cookies для проверки почты

.yandex.ru    TRUE    /    TRUE    2147483647    yandex_login    john_doe
.yandex.ru    TRUE    /    TRUE    2147483647    yandexuid    9876543210
.mail.yandex.ru    TRUE    /    TRUE    2147483647    Session_id    abc123def
.ya.ru    TRUE    /    TRUE    2147483647    ys    sess_xyz
mail.rambler.ru    FALSE    /    FALSE    0    rlogin    myemail
```

#### Важные замечания

1. **Точка в начале домена**: Сохраняйте её для корректной работы с Яндексом
2. **Большие значения expiration**: Автоматически конвертируются из миллисекунд в секунды
3. **Комментарии**: Строки, начинающиеся с `#`, игнорируются
4. **Пустые строки**: Пропускаются при обработке

---

### Работа с прокси

#### Форматы прокси

Менеджер прокси поддерживает различные форматы:

```bash
# Простой формат: IP:Port
185.199.108.153:8080

# С авторизацией: IP:Port:Login:Password
185.199.108.153:8080:myuser:mypassword

# HTTP с авторизацией
http://myuser:mypassword@185.199.108.153:8080

# SOCKS5
socks5://myuser:mypassword@185.199.108.153:8080
```

#### Класс Proxy

```python
from core.lib.module_proxy_manager import Proxy, ProxyManager

# Создание прокси из строки
proxy = Proxy.from_string("185.199.108.153:8080:user:pass")

# Или программно
proxy = Proxy(
    host="185.199.108.153",
    port=8080,
    login="user",
    password="pass",
    proxy_type="http"  # или "socks5"
)

print(proxy.url)  # http://user:pass@185.199.108.153:8080
```

#### Менеджер прокси

```python
from core.lib.module_proxy_manager import ProxyManager
import asyncio

# Инициализация
manager = ProxyManager(logger=my_logger)

# Загрузка из файла
count = manager.load_from_file("proxies.txt")
print(f"Загружено прокси: {count}")

# Асинхронная проверка всех прокси
asyncio.run(manager.check_all_proxies(timeout=5, max_concurrent=50))

# Получение статистики
stats = manager.get_statistics()
print(f"Рабочих: {stats['working']}, Не рабочих: {stats['not_working']}")

# Получение следующего прокси (ротация)
proxy = manager.get_next_proxy()

# Получение самого быстрого прокси
fast = manager.get_fastest_proxy()
```

#### Файл proxies.txt

```txt
# Пример файла с прокси (по одному на строку)

# Простые прокси
185.199.108.153:8080
192.168.1.1:3128

# С авторизацией
185.199.108.154:8080:admin:secret123

# SOCKS5
socks5://185.199.108.155:1080:user:pass

# HTTP с протоколом
http://185.199.108.156:8080:login:password
```

---

### Модули проверки почты

#### Яндекс.Почта (YandexMailChecker)

```python
from core.mail_checkers.module_yandex_mail_checker import YandexMailChecker
import asyncio

# Инициализация чекера
checker = YandexMailChecker(
    proxy_url="http://proxy:8080",        # URL прокси (опционально)
    cookies_file="yandex_cookies.txt",    # Путь к файлу cookies
    timeout=30,                            # Таймаут запросов (сек)
    user_agent="Mozilla/5.0...",          # User-Agent (опционально)
    logger=my_logger,                     # Логгер (опционально)
    result_saver=my_saver,                # Сохранялка результатов
    download_html=False                   # Сохранять ли HTML (опционально)
)

# Загрузка cookies
if checker.load_cookies():
    print("Cookies успешно загружены")

# Асинхронная проверка
async def check():
    result = await checker.check_mail(
        search_domains=["keyword1", "keyword2"]  # Ключевые слова для поиска
    )
    return result

# Запуск
result = asyncio.run(check())
```

#### Mail.ru (MailRuMailChecker)

```python
from core.mail_checkers.module_mailru_mail_checker import MailRuMailChecker

checker = MailRuMailChecker(
    proxy_url="http://proxy:8080",
    cookies_file="mailru_cookies.txt",
    timeout=30,
    logger=my_logger,
    result_saver=my_saver,
    download_html=False
)

checker.load_cookies()

# Проверка с одним ключевым словом
result = await checker.check_mail(search_keyword="важное письмо")
```

#### Рамблер (RamblerMailChecker)

```python
from core.mail_checkers.module_rambler_mail_checker import RamblerMailChecker

checker = RamblerMailChecker(
    proxy_url="http://proxy:8080",
    cookies_file="rambler_cookies.txt",
    timeout=30,
    logger=my_logger,
    result_saver=my_saver
)

checker.load_cookies()

# Проверка (принимает строку или список)
result = await checker.check_mail(
    search_keywords=["письмо", "уведомление"]  # Или просто "письмо"
)
```

#### Обратные вызовы (Callbacks)

Все чекеры поддерживают механизм обратных вызовов для отслеживания статуса:

```python
def status_callback(email, status_account, search_status, count_hits):
    print(f"Email: {email}")
    print(f"Аккаунт валиден: {status_account}")
    print(f"Поиск успешен: {search_status}")
    print(f"Найдено писем: {count_hits}")

checker = YandexMailChecker(
    proxy_url="...",
    cookies_file="...",
    on_status_update=status_callback  # Передаём функцию
)
```

---

### Парсеры cookies

Проект включает специализированные парсеры для каждого почтового сервиса.

#### Универсальный парсер (CookiesParser)

```python
from core.lib.module_cookies_parser import CookiesParser

# Инициализация
parser = CookiesParser(logs_dir="logs", logger=my_logger)

# Поиск всех файлов с cookies
all_files = parser.find_cookies_files()
print(f"Найдено файлов: {len(all_files)}")

# Поиск cookies конкретного сервиса
yandex_cookies = parser.find_service_cookies('yandex')
mailru_cookies = parser.find_service_cookies('mailru')
rambler_cookies = parser.find_service_cookies('rambler')

# Получение всех файлов Яндекс, отсортированных по качеству
yandex_files = parser.get_all_yandex_cookies_files()

# Объединение cookies из нескольких файлов
merged_path = parser.merge_yandex_cookies("combined_cookies.txt")
```

#### Специализированные парсеры

```python
# Яндекс
from core.cookies_parsers.yandex_cookies_parser import YandexCookiesParser

yandex_parser = YandexCookiesParser(logs_dir="logs")
files = yandex_parser.get_all_yandex_cookies_files()
merged = yandex_parser.merge_yandex_cookies()

# Mail.ru
from core.cookies_parsers.mailru_cookies_parser import MailRuCookiesParser

mailru_parser = MailRuCookiesParser(logs_dir="logs")
files = mailru_parser.get_all_mailru_cookies_files()

# Рамблер
from core.cookies_parsers.rambler_cookies_parser import RamblerCookiesParser

rambler_parser = RamblerCookiesParser(logs_dir="logs")
files = rambler_parser.get_all_rambler_cookies_files()
```

#### Оценка качества cookies

Каждый парсер оценивает качество cookies по следующим критериям:

| Критерий | Баллы | Описание |
|----------|-------|----------|
| Критические cookies | +10 | Присутствие ключевых cookies сервиса |
| Важные домены | +5 | Наличие cookies с важных доменов |
| Полнота набора | +20 | Процент найденных критических cookies |
| Разнообразие доменов | +3×N | За каждый уникальный важный домен |

---

### Сохранение результатов

#### Класс ResultSaver

```python
from core.lib.module_saving_results import ResultSaver

# Инициализация
saver = ResultSaver(
    base_output_dir="results",  # Базовая директория для сохранения
    logger=my_logger
)

# Ручное сохранение результатов
file_path = saver.save_email_results(
    account_data={
        "email": "user@yandex.ru",
        "name": "Иван Петров",
        "country": "Russia"
    },
    emails_data=[
        {
            "from_email": "sender@example.com",
            "subject": "Важное письмо",
            "snippet": "Краткое содержание...",
            "date": "2024-01-15 10:30:00"
        }
    ],
    search_query="ключевое слово",
    cookies_path="cookies.txt",
    proxy_url="http://proxy:8080",
    session_cookies=[...]  # Список cookies в формате Netscape
)

print(f"Сохранено в: {file_path}")
```

#### Структура сохранённых файлов

```
📦 results/
├── 📂 yandex/
│   ├── 📂 sender1@example.com/
│   │   ├── (3) [sender1@example.com] [user@yandex.ru].txt
│   │   └── (1) [sender2@example.com] [user@yandex.ru].txt
│   └── 📂 sender2@example.com/
│       └── (5) [sender3@example.com] [user@yandex.ru].txt
│
├── 📂 mailru/
│   └── 📂 sender@mail.ru/
│       └── (2) [sender@mail.ru] [mylogin@mail.ru].txt
│
└── 📂 rambler/
    └── 📂 user@rambler.ru/
        └── (1) [news@rambler.ru] [user@rambler.ru].txt
```

#### Формат сохранённого файла

```txt
– Name: Иван Петров
– Email: user@yandex.ru
– Country: Russia
– Search Query: важное письмо
– Cookies: cookies.txt

From: sender@example.com
Subject: Важное письмо о проекте
Snippet: Уважаемый Иван, сообщаем о начале нового проекта...
Date: 2024-01-15 10:30:00

From: sender@example.com
Subject: Обновление по проекту
Snippet: Проект продвигается согласно плану...
Date: 2024-01-16 14:20:00

# Session Cookies (Netscape format):
.yandex.ru    TRUE    /    TRUE    1735689600    yandex_login    user
.yandex.ru    TRUE    /    TRUE    1735689600    yandexuid    123456
```

---

## 💻 Примеры использования

### Пример 1: Полная проверка Яндекс почты

```python
import asyncio
from core.mail_checkers.module_yandex_mail_checker import YandexMailChecker
from core.lib.module_logger_manager import LoggerManager
from core.lib.module_saving_results import ResultSaver

async def main():
    # Инициализация
    logger = LoggerManager("YandexChecker", level="INFO")
    saver = ResultSaver(base_output_dir="results", logger=logger)
    
    # Создание чекера
    checker = YandexMailChecker(
        proxy_url="http://proxy.example.com:8080",
        cookies_file="yandex_cookies.txt",
        logger=logger,
        result_saver=saver
    )
    
    # Загрузка cookies
    if not checker.load_cookies():
        logger.error("Не удалось загрузить cookies")
        return
    
    # Поиск писем
    result = await checker.check_mail(
        search_domains=["проект", "договор", "счёт"]
    )
    
    if result:
        logger.info("✅ Проверка завершена успешно")
    else:
        logger.warning("⚠️ Письма не найдены")

# Запуск
asyncio.run(main())
```

### Пример 2: Проверка всех сервисов с ротацией прокси

```python
import asyncio
from core.mail_checkers import (
    YandexMailChecker,
    MailRuMailChecker,
    RamblerMailChecker
)
from core.lib.module_proxy_manager import ProxyManager
from core.lib.module_logger_manager import LoggerManager

async def check_all_services():
    logger = LoggerManager("MultiServiceChecker", level="DEBUG")
    manager = ProxyManager(logger=logger)
    
    # Загрузка прокси
    count = manager.load_from_file("proxies.txt")
    logger.info(f"Загружено {count} прокси")
    
    # Проверка прокси
    await manager.check_all_proxies(timeout=5)
    
    results = {}
    
    # Яндекс
    proxy = manager.get_next_proxy()
    yandex = YandexMailChecker(
        proxy_url=proxy.url if proxy else None,
        cookies_file="cookies/yandex.txt",
        logger=logger
    )
    results['yandex'] = await yandex.check_mail(["keyword"])
    
    # Mail.ru
    proxy = manager.get_next_proxy()
    mailru = MailRuMailChecker(
        proxy_url=proxy.url if proxy else None,
        cookies_file="cookies/mailru.txt",
        logger=logger
    )
    results['mailru'] = await mailru.check_mail("keyword")
    
    # Рамблер
    proxy = manager.get_next_proxy()
    rambler = RamblerMailChecker(
        proxy_url=proxy.url if proxy else None,
        cookies_file="cookies/rambler.txt",
        logger=logger
    )
    results['rambler'] = await rambler.check_mail(["keyword"])
    
    # Итоги
    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"{status_icon} {service}: {'Успешно' if status else 'Неудачно'}")
    
    return results

asyncio.run(check_all_services())
```

### Пример 3: Интерактивный браузер

```bash
# Простой запуск с файлом cookies.txt
python browser.py

# Или указать путь к файлу в коде browser.py
```

Программа запустит браузер Chromium с загруженными cookies и откроет страницу Яндекс.Почты. Вы сможете свободно работать в браузере, а после закрытия программа завершится.

---

## ⚙️ Конфигурация и настройки

### Настройки логирования

```python
from core.lib.module_logger_manager import LoggerManager

# Разные уровни логирования
logger = LoggerManager(
    name="MyApp",
    log_file="logs/app.log",      # Путь к файлу логов
    level="DEBUG",                # DEBUG, INFO, WARNING, ERROR
    console_output=True,          # Вывод в консоль
    file_output=True              # Запись в файл
)

logger.info("Информационное сообщение")
logger.warning("Предупреждение")
logger.error("Ошибка")
logger.debug("Отладочная информация")
```

### Уровни логирования

| Уровень | Описание | Использование |
|---------|----------|---------------|
| `DEBUG` | Подробная отладочная информация | Разработка и тестирование |
| `INFO` | Общая информация о ходе работы | Стандартный режим |
| `WARNING` | Предупреждения о потенциальных проблемах | Мониторинг |
| `ERROR` | Сообщения об ошибках | Отладка проблем |

### Настройки ResultSaver

```python
from core.lib.module_saving_results import ResultSaver

saver = ResultSaver(
    base_output_dir="my_results",  # Директория для результатов
    logger=my_logger
)

# Получение статистики
domains = saver.get_saved_domains()
print(f"Домены с результатами: {domains}")

# Количество файлов по домену
yandex_count = saver.get_results_count_by_domain("yandex")
print(f"Файлов Яндекс: {yandex_count}")
```

---

## 📊 Логирование

### Формат логов

```
2024-01-15 10:30:00 | INFO     | [YandexMailChecker.check_mail] Загружено 45 cookies
2024-01-15 10:30:05 | DEBUG    | [YandexMailChecker._search_and_process] Отправлен запрос на API
2024-01-15 10:30:07 | INFO     | [YandexMailChecker._search_and_process] Найдено сообщений: 12
2024-01-15 10:30:10 | WARNING  | [ProxyManager.get_next_proxy] Рабочих прокси нет, используем первый
```

### Структура логов

```
ГГГГ-ММ-ДД ЧЧ:ММ:СС | УРОВЕНЬ   | [Модуль.Метод] Сообщение
```

### Получение логгера

```python
from core.lib.module_logger_manager import get_logger

# Быстрое получение логгера
logger = get_logger("MyComponent")

# Или создание своего
from core.lib.module_logger_manager import LoggerManager
logger = LoggerManager(
    name="CustomLogger",
    log_file="logs/custom.log",
    level="INFO"
)
```

---

## ❓ FAQ и устранение проблем

### Ошибка "Cookies не найдены"

**Проблема**: Файл cookies не найден или имеет неверный формат

**Решение**:
1. Проверьте существование файла
2. Убедитесь, что формат соответствует Netscape
3. Проверьте наличие точки в начале домена для Яндекса

```python
# Проверка формата
with open("cookies.txt", "r") as f:
    first_line = f.readline()
    if not first_line.startswith("#"):
        print("⚠️ Первой строкой должен быть комментарий")
```

### Ошибка "Timeout запроса"

**Проблема**: Превышен таймаут при обращении к API

**Решение**:
1. Увеличьте значение timeout
2. Проверьте работоспособность прокси
3. Попробуйте другой прокси

```python
checker = YandexMailChecker(
    cookies_file="...",
    timeout=60  # Увеличено с 30 до 60 секунд
)
```

### Cookies не работают (аккаунт не валиден)

**Проблема**: Cookies устарели или неполные

**Решение**:
1. Получите свежие cookies из браузера
2. Проверьте наличие критических cookies
3. Используйте расширение "EditThisCookie" для экспорта

### Ошибка парсинга JSON

**Проблема**: API почтового сервиса вернул неожиданный ответ

**Решение**:
1. Проверьте логи на предмет ошибок
2. Обновите версию библиотек
3. Проверьте структуру cookies

### Прокси не подключается

**Проблема**: Прокси недоступен или неверные данные

**Решение**:
1. Проверьте формат прокси в файле
2. Используйте `check_all_proxies()` для проверки
3. Получите новые рабочие прокси

---

## ⚠️ Disclaimer / Отказ от ответственности

### English
This repository and the information contained herein are strictly for educational, research, and informational purposes only. 
* **No Commercial Use:** This project is not intended for commercial use and is completely non-profit.
* **No Harm Intended:** The author does not encourage, support, or facilitate any illegal activities, service disruption, or unauthorized access to computer systems.
* **Intellectual Property:** All product names, logos, and brands are property of their respective owners. 
* **Terms of Service:** The user of this materials assumes all responsibility for compliance with the terms of service of the respective platforms. The author bears no responsibility for any misuse or damage caused by this repository.
* **Take-Down Notice:** If you are the copyright owner or a representative of the company and wish to have this content removed, please contact me directly, and I will delete this repository immediately.

### Русский
Данный репозиторий и содержащаяся в нем информация предоставлены исключительно в ознакомительных, учебных и научно-исследовательских целях.
* **Некоммерческое использование:** Проект не преследует коммерческих целей, является полностью некоммерческим и не используется для получения выгоды.
* **Отсутствие злого умысла:** Автор не призывает к совершению противоправных действий, не поощряет взлом, обход систем безопасности или нарушение работоспособности сторонних сервисов.
* **Интелектуальная собственность:** Все права на товарные знаки, названия сервисов и их логотипы принадлежат их законным владельцам.
* **Пользовательское соглашение:** Любое использование материалов данного репозитория производится пользователями на свой страх и риск. Автор не несет ответственности за возможные блокировки аккаунтов или иные последствия.
* **Правообладателям:** Если вы являетесь представителем компании или правообладателем и считаете, что данный репозиторий нарушает ваши права, пожалуйста, свяжитесь со мной. Материалы будут удалены незамедлительно по первому требованию.

Telegram: @ya_prgm

---

*Дата последнего обновления: 2026*
