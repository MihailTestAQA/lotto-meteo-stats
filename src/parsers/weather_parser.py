import requests
import json
import sqlite3
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class WeatherParser:
    def __init__(self):
        # Берем ключ из переменных окружения
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "default_key_if_not_found")
        self.city = os.getenv("CITY", "Moscow")
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        
    def get_weather(self):
        if not self.api_key or self.api_key == "default_key_if_not_found":
            raise ValueError("API ключ не найден. Проверьте .env файл")
        
    def get_current_weather(self):
        """Получить текущую погоду с OpenWeatherMap"""
        try:
            params = {
                'q': self.city,
                'appid': self.api_key,
                'units': 'metric',  # метрическая система
                'lang': 'ru'        # русский язык
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Преобразуем данные в нужный формат
            weather = {
                'city': self.city,
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'weather_description': data['weather'][0]['description'],
                'humidity': data['main']['humidity'],
                'pressure_hpa': data['main']['pressure'],
                'pressure_mmhg': round(data['main']['pressure'] * 0.750062, 2),  # конвертация
                'wind_speed': data['wind']['speed'],
                'wind_direction': self._get_wind_direction(data['wind'].get('deg', 0)),
                'visibility': data.get('visibility', 10000) // 1000,  # в км
                'cloudiness': data['clouds']['all'],
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"🌤️ Погода получена: {weather['temperature']}°C")
            return weather
            
        except Exception as e:
            print(f"❌ Ошибка получения погоды: {e}")
            # Возвращаем заглушку если API не работает
            return self._get_fallback_weather()
    
    def _get_fallback_weather(self):
        """Запасные данные если API не работает"""
        return {
            'city': self.city,
            'temperature': 20.5,
            'feels_like': 19.0,
            'weather_description': 'ясно',
            'humidity': 65,
            'pressure_hpa': 1013,
            'pressure_mmhg': 760,
            'wind_speed': 3.0,
            'wind_direction': 'северо-восточный',
            'visibility': 10,
            'cloudiness': 20,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_wind_direction(self, degrees):
        """Преобразует градусы в направление ветра"""
        directions = ['северный', 'северо-восточный', 'восточный', 'юго-восточный',
                     'южный', 'юго-западный', 'западный', 'северо-западный']
        index = round(degrees / 45) % 8
        return directions[index]
    
    def save_weather_to_db(self, weather_data):
        """Сохраняет погодные данные в БД"""
        try:
            db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу если её нет
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS weather_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    temperature REAL NOT NULL,
                    feels_like REAL,
                    weather_description TEXT NOT NULL,
                    humidity INTEGER,
                    pressure_mmhg REAL,
                    pressure_hpa REAL,
                    wind_speed REAL,
                    wind_direction TEXT,
                    visibility INTEGER,
                    cloudiness INTEGER,
                    city TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute('''
                INSERT INTO weather_history 
                (timestamp, temperature, feels_like, weather_description, 
                 humidity, pressure_mmhg, pressure_hpa, wind_speed, 
                 wind_direction, visibility, cloudiness, city)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                weather_data.get('timestamp'),
                weather_data.get('temperature'),
                weather_data.get('feels_like'),
                weather_data.get('weather_description', ''),
                weather_data.get('humidity'),
                weather_data.get('pressure_mmhg'),
                weather_data.get('pressure_hpa'),
                weather_data.get('wind_speed'),
                weather_data.get('wind_direction', ''),
                weather_data.get('visibility'),
                weather_data.get('cloudiness'),
                weather_data.get('city', 'Москва')
            ))
            
            conn.commit()
            conn.close()
            print(f"💾 Погода сохранена в БД: {weather_data['temperature']}°C")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка сохранения погоды в БД: {e}")
            return False
    
    def update_latest_weather_to_lottery(self, weather_data):
        """Обновляет последние тиражи текущей погодой"""
        try:
            db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Обновляем последние 2 тиража  
            cursor.execute('''
                UPDATE lottery_results 
                SET temperature = ?, weather = ?, pressure = ?
                WHERE id IN (
                    SELECT id FROM lottery_results 
                    ORDER BY date DESC, time DESC 
                    LIMIT 2
                )
            ''', (
                weather_data.get('temperature'),
                weather_data.get('weather_description', ''),
                weather_data.get('pressure_mmhg')
            ))
            
            conn.commit()
            conn.close()
            print(f"🔗 Погода привязана к последним тиражам")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обновления погоды в тиражах: {e}")
            return False