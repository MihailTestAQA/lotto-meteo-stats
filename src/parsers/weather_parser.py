# Создаем Модуль для получения погодных данных с OpenWeatherMap API

import requests
from datetime import datetime
from config import Config
import json
import os

class WeatherParser:
    """Парсер погодных данных"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or Config.WEATHER_API_KEY
        self.base_url = Config.WEATHER_API_URL
        self.city = Config.CITY_NAME
        self.country_code = Config.COUNTRY_CODE
        
        if not self.api_key:
            raise ValueError("API ключ OpenWeatherMap не найден. Добавь WEATHER_API_KEY в .env файл")
    
    def get_current_weather(self):
        """Получить текущую погоду"""
        params = {
            'q': f'{self.city},{self.country_code}',
            'appid': self.api_key,
            'units': 'metric',  # градусы Цельсия
            'lang': 'ru'        # русский язык
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_weather_data(data)
            
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе погоды: {e}")
            return None
    
    def get_weather_by_date(self, date):
        """
        Получить погоду на конкретную дату
        Note: Бесплатный тариф OpenWeatherMap не дает исторических данных
        Для исторических данных нужен платный тариф
        """
        print(f"Запрос исторической погоды для {date} - требуется платный API")
        return self.get_current_weather()  # Возвращаем текущую как заглушку
    
    def _parse_weather_data(self, data):
        """Разобрать данные погоды"""
        if data.get('cod') != 200:
            print(f"Ошибка API: {data.get('message', 'Unknown error')}")
            return None
        
        # Конвертируем давление из hPa в мм рт.ст.
        pressure_hpa = data['main']['pressure']
        pressure_mmhg = self._hpa_to_mmhg(pressure_hpa)
        
        weather_data = {
            'timestamp': datetime.fromtimestamp(data['dt']).isoformat(),
            'city': data['name'],
            'country': data['sys']['country'],
            'temperature': data['main']['temp'],
            'feels_like': data['main']['feels_like'],
            'temp_min': data['main']['temp_min'],
            'temp_max': data['main']['temp_max'],
            'pressure_hpa': pressure_hpa,           # hPa
            'pressure_mmhg': pressure_mmhg,         # мм рт.ст.
            'humidity': data['main']['humidity'],   # %
            'weather_main': data['weather'][0]['main'],
            'weather_description': data['weather'][0]['description'],
            'weather_icon': data['weather'][0]['icon'],
            'wind_speed': data['wind']['speed'],    # m/s
            'wind_deg': data['wind'].get('deg', 0),
            'cloudiness': data['clouds']['all'],    # %
            'visibility': data.get('visibility', 0), # meters
            'sunrise': datetime.fromtimestamp(data['sys']['sunrise']).isoformat(),
            'sunset': datetime.fromtimestamp(data['sys']['sunset']).isoformat()
        }
        
        return weather_data
    
    def _hpa_to_mmhg(self, pressure_hpa):
        """Конвертировать давление из hPa в мм рт.ст."""
        # 1 hPa = 0.750062 мм рт.ст.
        return round(pressure_hpa * 0.750062, 1)
    
    def save_weather_to_cache(self, weather_data, date=None):
        """Сохранить погодные данные в кэш"""
        if not weather_data:
            return
        
        cache_dir = Config.CACHE_DIR
        date_str = date or datetime.now().strftime('%Y-%m-%d')
        filename = f"weather_{date_str}.json"
        filepath = os.path.join(cache_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(weather_data, f, ensure_ascii=False, indent=2)
            print(f"Погодные данные сохранены в кэш: {filepath}")
        except Exception as e:
            print(f"Ошибка сохранения в кэш: {e}")
    
    def load_weather_from_cache(self, date=None):
        """Загрузить погодные данные из кэша"""
        cache_dir = Config.CACHE_DIR
        date_str = date or datetime.now().strftime('%Y-%m-%d')
        filename = f"weather_{date_str}.json"
        filepath = os.path.join(cache_dir, filename)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки из кэш: {e}")
        
        return None

# Пример использования
if __name__ == '__main__':
    parser = WeatherParser()
    weather = parser.get_current_weather()
    
    if weather:
        print("Текущая погода в Москве:")
        print(f"Температура: {weather['temperature']}°C")
        print(f"Ощущается как: {weather['feels_like']}°C")
        print(f"Погода: {weather['weather_description']}")
        print(f"Влажность: {weather['humidity']}%")
        print(f"Давление: {weather['pressure_mmhg']} мм рт.ст. ({weather['pressure_hpa']} hPa)")
        print(f"Ветер: {weather['wind_speed']} m/s")
        
        # Сохраняем в кэш
        parser.save_weather_to_cache(weather)