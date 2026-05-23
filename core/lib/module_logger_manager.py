# module_logger_manager.py
import logging
import sys
import inspect
from datetime import datetime
from typing import Optional
from pathlib import Path

class LoggerManager:
    """
    Простой и эффективный менеджер логгера
    """
    
    def __init__(self, 
                 name: str = "AppLogger",
                 log_file: Optional[str] = None,
                 level: str = "INFO",
                 console_output: bool = True,
                 file_output: bool = True):
        """
        Инициализация логгера
        """
        self.name = name
        self.log_file = log_file
        self.level = getattr(logging, level.upper())
        
        # Создаем логгер
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        
        # Очищаем существующие обработчики
        self.logger.handlers.clear()
        
        # Создаем форматтер
        self.formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Настраиваем консольный вывод
        if console_output:
            self._setup_console_handler()
        
        # Настраиваем файловый вывод
        if file_output and log_file:
            self._setup_file_handler(log_file)
    
    def _setup_console_handler(self):
        """Настройка вывода в консоль"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self, log_file: str):
        """Настройка записи в файл"""
        try:
            # Создаем директорию если не существует
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(self.level)
            file_handler.setFormatter(self.formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Ошибка настройки файлового логгера: {e}")
    
    def _get_caller_info(self) -> str:
        """Получает информацию о вызывающем модуле и функции"""
        try:
            # Получаем фрейм вызывающей функции
            frame = inspect.currentframe()
            # Пропускаем фреймы: _get_caller_info -> debug/info/etc -> вызывающий код
            for _ in range(3):
                if frame.f_back:
                    frame = frame.f_back
            
            module_name = frame.f_globals.get('__name__', 'unknown')
            function_name = frame.f_code.co_name
            
            # Укорачиваем имя модуля
            if '.' in module_name:
                module_name = module_name.split('.')[-1]
            
            return f"[{module_name}.{function_name}]"
        except:
            return "[unknown.unknown]"
    
    def info(self, message: str):
        """Логирование информации"""
        caller_info = self._get_caller_info()
        self.logger.info(f"{caller_info} {message}")
    
    def warning(self, message: str):
        """Логирование предупреждений"""
        caller_info = self._get_caller_info()
        self.logger.warning(f"{caller_info} {message}")
    
    def error(self, message: str, exc_info: Optional[Exception] = None):
        """Логирование ошибок"""
        caller_info = self._get_caller_info()
        if exc_info:
            self.logger.error(f"{caller_info} {message}", exc_info=exc_info)
        else:
            self.logger.error(f"{caller_info} {message}")
    
    def debug(self, message: str):
        """Логирование отладочной информации"""
        caller_info = self._get_caller_info()
        self.logger.debug(f"{caller_info} {message}")


# Глобальный экземпляр логгера для удобства
_default_logger = None

def get_logger(name: str = "AppLogger", **kwargs) -> LoggerManager:
    """Фабрика для получения логгера"""
    global _default_logger
    if _default_logger is None:
        _default_logger = LoggerManager(name, **kwargs)
    return _default_logger