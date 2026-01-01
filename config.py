#Конфигурация приложения LottoMeteoStats

import os
from dotenv import load_dotenv

# Создаем папку data если ее нет
if not os.path.exists('data'):
    os.makedirs('data')


# Загружаем переменные окружения из .env файла
load_dotenv()

class Config:
    """Базовые настройки приложения"""
    
    # Безопасность
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Путь к БД в папке data (База данных)
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'data', 'lottery.db') # Путь к БД
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # API ключи
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', '')
    WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
    
    # Настройки лотереи
    LOTTERY_URL = os.getenv('LOTTERY_URL', '')
    LOTTERY_NAME = os.getenv('LOTTERY_NAME', 'RussianLotto')
    
    # Город для погоды
    CITY_NAME = os.getenv('CITY_NAME', 'Moscow')
    COUNTRY_CODE = os.getenv('COUNTRY_CODE', 'RU')
    
    # Настройки приложения
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    UPDATE_INTERVAL_HOURS = int(os.getenv('UPDATE_INTERVAL_HOURS', '24'))
    
    # Пути к файлам
    DATA_DIR = 'data'
    CACHE_DIR = os.path.join(DATA_DIR, 'cache')
    EXPORTS_DIR = os.path.join(DATA_DIR, 'exports')
    
    # Создаем необходимые директории
    @staticmethod
    def create_directories():
        """Создает необходимые директории для работы приложения"""
        directories = [
            Config.DATA_DIR,
            Config.CACHE_DIR,
            Config.EXPORTS_DIR
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Создана директория: {directory}")

# Создаем директории при импорте конфигурации
Config.create_directories()

# Погодные настройки
WEATHER_API_BASE_URL = "https://api.openweathermap.org/data/2.5"
WEATHER_CURRENT_URL = f"{WEATHER_API_BASE_URL}/weather"
WEATHER_FORECAST_URL = f"{WEATHER_API_BASE_URL}/forecast"