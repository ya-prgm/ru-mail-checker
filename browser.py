
from playwright.sync_api import sync_playwright
import os
import json
from datetime import datetime

def launch_browser_with_cookies(cookies_path: str):
    """
    Запускает браузер с загруженными куками из указанного файла
    """
    if not os.path.exists(cookies_path):
        print(f"❌ Файл с куками не найден: {cookies_path}")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        try:
            cookies_list = parse_cookies_file(cookies_path)
            context.add_cookies(cookies_list)
            print(f"✅ Загружено кук из: {cookies_path}")
        except Exception as e:
            print(f"❌ Ошибка загрузки кук: {e}")
            browser.close()
            return
        page = context.new_page()
        page.goto("https://mail.rambler.ru/", timeout=300000)
        
        print("✅ Браузер запущен с куками!")
        print("🔧 Вы можете свободно работать в браузере...")
        print("❌ Закройте браузер чтобы завершить программу")
        input("Нажмите Enter после закрытия браузера...")
        
        browser.close()

def parse_cookies_file(cookies_path: str):
    """
    Парсит файл куков в формате Netscape и преобразует в формат Playwright
    Использует алгоритм из old_mail_checker.py
    """
    if not os.path.exists(cookies_path):
        return []
    
    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            content = f.read()
        content_stripped = content.strip()
        if content_stripped.startswith('[') or content_stripped.startswith('{'):
            cookies = json.loads(content)
            if isinstance(cookies, list):
                return cookies
            elif isinstance(cookies, dict):
                return [cookies]
            return []
        else:
            return parse_netscape_cookies(content)
    
    except json.JSONDecodeError:
        try:
            with open(cookies_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return parse_netscape_cookies(content)
        except Exception as e:
            print(f"Ошибка загрузки куки: {e}")
            return []
    except Exception as e:
        print(f"Ошибка загрузки куки: {e}")
        return []

def parse_netscape_cookies(content: str):
    """
    Парсит куки в формате Netscape cookie file (исправленная версия)
    """
    cookies = []
    valid_count = 0
    converted_count = 0
    
    lines = content.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('HttpOnly'):
            continue
        parts = line.split('\t')
        if len(parts) < 7:
            continue
        
        domain = parts[0]
        path = parts[2]
        secure = parts[3].upper() == 'TRUE'
        expires_str = parts[4]
        name = parts[5]
        value = parts[6]
        expires = None
        if expires_str != '0':
            try:
                expires_val = float(expires_str)
                if expires_val > 1e12:
                    expires_val = expires_val / 1000
                    converted_count += 1
                max_valid_expires = 2147483647
                if 0 < expires_val <= max_valid_expires:
                    expires = expires_val
                else:
                    expires = max_valid_expires
                    print(f"⚠️  Ограничиваем expires для {name}: {expires_val} -> {max_valid_expires}")
                    
            except (ValueError, OverflowError):
                print(f"⚠️  Некорректный expires для {name}: {expires_str}")
        
        cookie = {
            'name': name,
            'value': value,
            'domain': domain,
            'path': path,
            'secure': secure,
        }
        
        if expires is not None:
            cookie['expires'] = expires
        
        cookies.append(cookie)
        valid_count += 1
    
    print(f"📊 Прочитано кук: {len(cookies)}")
    print(f"✅ Валидных: {valid_count}")
    print(f"🔄 Конвертировано из мс в сек: {converted_count}")
    print("\n🔍 Первые 10 кук:")
    for i, cookie in enumerate(cookies[:10]):
        expires_info = cookie.get('expires', 'session')
        if expires_info != 'session':
            dt = datetime.fromtimestamp(expires_info)
            expires_info = f"{expires_info} ({dt.strftime('%Y-%m-%d %H:%M:%S')})"
        print(f"  {i+1}. {cookie['name']}: {cookie['domain']} (expires: {expires_info})")
    
    return cookies

if __name__ == "__main__":
    cookies_file = 'cookies.txt'
    
    if not os.path.exists(cookies_file):
        print(f"❌ Файл {cookies_file} не найден!")
        possible_files = ['cookies.txt']
        for file in possible_files:
            if os.path.exists(file):
                cookies_file = file
                print(f"✅ Найден файл: {file}")
                break
        else:
            print("❌ Не найден ни один файл с куками!")
            exit(1)
    
    launch_browser_with_cookies(cookies_file)