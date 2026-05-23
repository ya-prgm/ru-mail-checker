# module_proxy_manager.py
"""
Менеджер прокси для ротации и проверки
"""
import asyncio
import aiohttp
import time
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import random

class Proxy:
    """Класс для представления прокси"""
    
    def __init__(self, host: str, port: int, login: Optional[str] = None, password: Optional[str] = None, proxy_type: str = 'http'):
        self.host = host
        self.port = port
        self.login = login
        self.password = password
        self.proxy_type = proxy_type.lower()  # 'http' или 'socks5'
        self.status: Optional[str] = None  # 'working', 'not_working', None
        self.last_check: Optional[datetime] = None
        self.speed: Optional[float] = None  # в секундах
        self.response_time: Optional[float] = None  # время отклика
        
    @property
    def url(self) -> str:
        """Возвращает URL прокси (HTTP)"""
        if self.login and self.password:
            return f"http://{self.login}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"
    
    @property
    def socks5_url(self) -> str:
        """Возвращает SOCKS5 URL прокси"""
        if self.login and self.password:
            return f"socks5://{self.login}:{self.password}@{self.host}:{self.port}"
        return f"socks5://{self.host}:{self.port}"
    
    @property
    def proxy_url(self) -> str:
        """Возвращает URL прокси в зависимости от типа"""
        if self.proxy_type == 'socks5':
            return self.socks5_url
        return self.url
    
    def to_dict(self) -> Dict:
        """Преобразует прокси в словарь"""
        return {
            'host': self.host,
            'port': self.port,
            'login': self.login,
            'password': self.password,
            'proxy_type': self.proxy_type,
            'status': self.status,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'speed': self.speed,
            'response_time': self.response_time
        }
    
    @classmethod
    def from_string(cls, proxy_string: str) -> 'Proxy':
        """
        Создает прокси из строки
        Поддерживаемые форматы:
        - ip:port
        - ip:port:login:password
        - socks5://login:password@host:port
        - socks5://host:port
        - http://login:password@host:port
        - http://host:port
        """
        proxy_string = proxy_string.strip()
        
        # Проверяем формат с протоколом (socks5:// или http://)
        if '://' in proxy_string:
            # Парсим URL формат: protocol://[login:password@]host:port
            protocol_part, rest = proxy_string.split('://', 1)
            protocol = protocol_part.lower()
            
            if protocol not in ['socks5', 'http', 'https']:
                raise ValueError(f"Неподдерживаемый протокол: {protocol}")
            
            # Определяем тип прокси
            proxy_type = 'socks5' if protocol == 'socks5' else 'http'
            
            # Проверяем наличие авторизации
            if '@' in rest:
                auth_part, host_port = rest.split('@', 1)
                login, password = auth_part.split(':', 1)
                host, port = host_port.rsplit(':', 1)
                return cls(
                    host=host,
                    port=int(port),
                    login=login,
                    password=password,
                    proxy_type=proxy_type
                )
            else:
                # Нет авторизации
                host, port = rest.rsplit(':', 1)
                return cls(
                    host=host,
                    port=int(port),
                    proxy_type=proxy_type
                )
        else:
            # Старый формат: ip:port или ip:port:login:password
            parts = proxy_string.split(':')
            if len(parts) == 2:
                return cls(host=parts[0], port=int(parts[1]), proxy_type='http')
            elif len(parts) == 4:
                return cls(host=parts[0], port=int(parts[1]), login=parts[2], password=parts[3], proxy_type='http')
            else:
                raise ValueError(f"Неверный формат прокси: {proxy_string}")


class ProxyManager:
    """Менеджер для работы с прокси"""
    
    def __init__(self, logger=None):
        self.proxies: List[Proxy] = []
        self.current_index = 0
        self.logger = logger
        self.test_urls = [
            "http://httpbin.org/ip",
            "http://api.ipify.org",
            "http://icanhazip.com"
        ]
    
    def load_from_file(self, file_path: str) -> int:
        """
        Загружает прокси из файла
        Поддерживаемые форматы:
        - ip:port
        - ip:port:login:password
        - socks5://login:password@host:port
        - socks5://host:port
        - http://login:password@host:port
        - http://host:port
        (по одному на строку)
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        self.proxies = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    proxy = Proxy.from_string(line)
                    self.proxies.append(proxy)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Ошибка парсинга прокси '{line}': {e}")
                    continue
        
        return len(self.proxies)
    
    def add_proxy(self, proxy: Proxy):
        """Добавляет прокси"""
        self.proxies.append(proxy)
    
    def get_next_proxy(self) -> Optional[Proxy]:
        """Получает следующий прокси (ротация)"""
        if not self.proxies:
            return None
        
        # Используем только рабочие прокси, если есть
        working_proxies = [p for p in self.proxies if p.status == 'working']
        if working_proxies:
            # Сортируем по скорости для выбора самого быстрого
            working_proxies.sort(key=lambda x: x.response_time or float('inf'))
            proxy = working_proxies[self.current_index % len(working_proxies)]
            self.current_index += 1
            return proxy
        
        # Если нет рабочих, используем все
        proxy = self.proxies[self.current_index % len(self.proxies)]
        self.current_index += 1
        return proxy
    
    async def check_proxy_fast(self, proxy: Proxy, timeout: int = 5) -> bool:
        """
        Быстрая проверка прокси с измерением времени отклика
        """
        start_time = time.time()
        
        try:
            # Случайный выбор тестового URL
            test_url = random.choice(self.test_urls)
            
            if proxy.proxy_type == 'socks5':
                # Для SOCKS5 используем aiohttp-socks если доступен
                try:
                    from aiohttp_socks import ProxyConnector
                    connector = ProxyConnector.from_url(proxy.socks5_url)
                    async with aiohttp.ClientSession(connector=connector) as session:
                        async with session.get(
                            test_url,
                            timeout=aiohttp.ClientTimeout(total=timeout),
                            headers={'User-Agent': 'Mozilla/5.0'}
                        ) as response:
                            if response.status == 200:
                                response_time = time.time() - start_time
                                proxy.response_time = response_time
                                proxy.status = 'working'
                                proxy.last_check = datetime.now()
                                if self.logger:
                                    self.logger.info(f"✓ {proxy.host}:{proxy.port} ({proxy.proxy_type}) - {response_time:.3f}s")
                                return True
                except ImportError:
                    # Если aiohttp-socks не установлен, используем обычный HTTP
                    proxy_url = proxy.url
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            test_url,
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=timeout),
                            headers={'User-Agent': 'Mozilla/5.0'}
                        ) as response:
                            if response.status == 200:
                                response_time = time.time() - start_time
                                proxy.response_time = response_time
                                proxy.status = 'working'
                                proxy.last_check = datetime.now()
                                if self.logger:
                                    self.logger.info(f"✓ {proxy.host}:{proxy.port} ({proxy.proxy_type}) - {response_time:.3f}s")
                                return True
            else:
                # HTTP прокси
                proxy_url = proxy.url
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        test_url,
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        headers={'User-Agent': 'Mozilla/5.0'}
                    ) as response:
                        if response.status == 200:
                            response_time = time.time() - start_time
                            proxy.response_time = response_time
                            proxy.status = 'working'
                            proxy.last_check = datetime.now()
                            if self.logger:
                                self.logger.info(f"✓ {proxy.host}:{proxy.port} ({proxy.proxy_type}) - {response_time:.3f}s")
                            return True
                            
        except asyncio.TimeoutError:
            if self.logger:
                self.logger.debug(f"✗ {proxy.host}:{proxy.port} - timeout")
        except Exception as e:
            if self.logger:
                self.logger.debug(f"✗ {proxy.host}:{proxy.port} - {type(e).__name__}")
        
        proxy.status = 'not_working'
        proxy.last_check = datetime.now()
        proxy.response_time = None
        return False
    
    async def check_all_proxies(self, timeout: int = 5, max_concurrent: int = 50):
        """
        Быстрая параллельная проверка всех прокси
        """
        if not self.proxies:
            if self.logger:
                self.logger.warning("Нет прокси для проверки")
            return
        
        if self.logger:
            self.logger.info(f"⚡ Быстрая проверка {len(self.proxies)} прокси (параллельно: {max_concurrent}, таймаут: {timeout}s)")
        
        # Создаем семафор для ограничения одновременных запросов
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def check_with_semaphore(proxy):
            async with semaphore:
                return await self.check_proxy_fast(proxy, timeout)
        
        # Запускаем все проверки параллельно
        tasks = [check_with_semaphore(proxy) for proxy in self.proxies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Статистика
        stats = self.get_statistics()
        if self.logger:
            self.logger.info(f"✅ Проверка завершена: {stats['working']} рабочих, {stats['not_working']} не рабочих")
            
            # Показываем топ-5 самых быстрых прокси
            working_proxies = [p for p in self.proxies if p.status == 'working']
            if working_proxies:
                working_proxies.sort(key=lambda x: x.response_time or float('inf'))
                self.logger.info("🏆 Топ-5 самых быстрых прокси:")
                for i, proxy in enumerate(working_proxies[:5]):
                    self.logger.info(f"  {i+1}. {proxy.host}:{proxy.port} - {proxy.response_time:.3f}s")
    
    def get_statistics(self) -> Dict:
        """Возвращает статистику по прокси"""
        total = len(self.proxies)
        working = len([p for p in self.proxies if p.status == 'working'])
        not_working = len([p for p in self.proxies if p.status == 'not_working'])
        unchecked = len([p for p in self.proxies if p.status is None])
        
        # Среднее время отклика рабочих прокси
        working_proxies = [p for p in self.proxies if p.status == 'working' and p.response_time]
        avg_response_time = sum(p.response_time for p in working_proxies) / len(working_proxies) if working_proxies else 0
        
        return {
            'total': total,
            'working': working,
            'not_working': not_working,
            'unchecked': unchecked,
            'avg_response_time': avg_response_time
        }
    
    def get_fastest_proxy(self) -> Optional[Proxy]:
        """Возвращает самый быстрый рабочий прокси"""
        working_proxies = [p for p in self.proxies if p.status == 'working']
        if not working_proxies:
            return None
        
        return min(working_proxies, key=lambda x: x.response_time or float('inf'))
    
    def to_dict_list(self) -> List[Dict]:
        """Преобразует все прокси в список словарей"""
        return [proxy.to_dict() for proxy in self.proxies]