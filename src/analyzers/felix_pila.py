import sqlite3
from datetime import datetime

class FelixPilaAnalyzer:
    """Анализатор связи погоды и лотерейных чисел"""
    
    def __init__(self):
        self.db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
    
    def analyze_weather_correlation(self):
        """Анализирует корреляцию между погодой и выпадением чисел"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Группируем погодные условия
        weather_categories = {
            'ясно': ['ясно', 'солнечно', 'малооблачно'],
            'пасмурно': ['пасмурно', 'облачно', 'тучи'],
            'дождь': ['дождь', 'ливень', 'морось'],
            'снег': ['снег', 'метель']
        }
        
        # 2. Группируем температуру
        temp_ranges = [
            ('очень холодно', -50, -10),
            ('холодно', -10, 0),
            ('прохладно', 0, 10),
            ('комфортно', 10, 20),
            ('тепло', 20, 30),
            ('жарко', 30, 50)
        ]
        
        # 3. Группируем давление
        pressure_ranges = [
            ('очень низкое', 0, 720),
            ('низкое', 720, 740),
            ('нормальное', 740, 760),
            ('высокое', 760, 780),
            ('очень высокое', 780, 1000)
        ]
        
        analysis_results = {}
        
        # Анализ для каждого числа
        for number in range(1, 21):
            cursor.execute('''
                SELECT l.draw_number, l.date, l.temperature, l.weather, l.pressure, 
                       l.field_1, l.field_2
                FROM lottery_results l
                WHERE (l.field_1 LIKE ? OR l.field_2 LIKE ?)
                  AND l.temperature IS NOT NULL
                  AND l.weather IS NOT NULL
                ORDER BY l.date
            ''', (f'%{number}%', f'%{number}%'))
            
            records = cursor.fetchall()
            
            for record in records:
                draw_num, date, temp, weather, pressure, field1, field2 = record
                
                # Определяем категории
                weather_cat = self._categorize_weather(weather, weather_categories)
                temp_cat = self._categorize_temperature(temp, temp_ranges)
                pressure_cat = self._categorize_pressure(pressure, pressure_ranges)
                
                key = f"{weather_cat}_{temp_cat}_{pressure_cat}"
                
                if key not in analysis_results:
                    analysis_results[key] = {
                        'weather': weather_cat,
                        'temperature': temp_cat,
                        'pressure': pressure_cat,
                        'numbers': {n: 0 for n in range(1, 21)},
                        'total_draws': 0
                    }
                
                analysis_results[key]['numbers'][number] += 1
                analysis_results[key]['total_draws'] += 1
        
        conn.close()
        
        # Рассчитываем вероятности
        for key, data in analysis_results.items():
            total = data['total_draws']
            if total > 0:
                for num in range(1, 21):
                    count = data['numbers'][num]
                    data['numbers'][num] = {
                        'count': count,
                        'probability': round((count / total) * 100, 2)
                    }
        
        return analysis_results
    
    def _categorize_weather(self, weather_text, categories):
        """Категоризирует погоду"""
        weather_lower = weather_text.lower()
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in weather_lower:
                    return category
        return 'другое'
    
    def _categorize_temperature(self, temp, ranges):
        """Категоризирует температуру"""
        for name, min_temp, max_temp in ranges:
            if min_temp <= temp < max_temp:
                return name
        return 'неизвестно'
    
    def _categorize_pressure(self, pressure, ranges):
        """Категоризирует давление"""
        for name, min_press, max_press in ranges:
            if min_press <= pressure < max_press:
                return name
        return 'неизвестно'
    
    def predict_numbers(self, current_weather, current_temp, current_pressure):
        """Прогнозирует числа на основе текущей погоды"""
        analysis = self.analyze_weather_correlation()
        
        # Определяем категории текущей погоды
        weather_categories = {'ясно': ['ясно'], 'пасмурно': ['пасмурно']}
        temp_ranges = [('холодно', -10, 0), ('прохладно', 0, 10)]
        pressure_ranges = [('нормальное', 740, 760)]
        
        weather_cat = self._categorize_weather(current_weather, weather_categories)
        temp_cat = self._categorize_temperature(current_temp, temp_ranges)
        pressure_cat = self._categorize_pressure(current_pressure, pressure_ranges)
        
        key = f"{weather_cat}_{temp_cat}_{pressure_cat}"
        
        if key in analysis:
            numbers_data = analysis[key]['numbers']
            # Сортируем по вероятности
            sorted_numbers = sorted(
                [(num, data['probability']) for num, data in numbers_data.items()],
                key=lambda x: x[1],
                reverse=True
            )
            return sorted_numbers[:8]  # 8 самых вероятных чисел
        else:
            # Возвращаем самые частые числа вообще
            return [(12, 8.65), (16, 8.65), (1, 7.69), (13, 7.69)]