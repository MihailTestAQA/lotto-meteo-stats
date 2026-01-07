# Главный файл приложения LottoMeteoStats

from flask import Flask, render_template, jsonify, request, Response
from flask_sqlalchemy import SQLAlchemy
from config import Config
from datetime import datetime
from sqlalchemy import text
import time
import json
import glob
import sys 
import os
import threading
import schedule

# место управления версиями
app_version = '1.2.2'

# Создаем экземпляр Flask приложения
app = Flask(__name__)
app.config.from_object(Config)

app.config['APP_VERSION'] = app_version 

# Инициализируем базу данных
db = SQLAlchemy(app)

# Модель данных для лотереи
class LotteryResult(db.Model):
    
    __tablename__ = 'lottery_results'
    
    id = db.Column(db.Integer, primary_key=True)
    draw_number = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    numbers = db.Column(db.String(200), nullable=False)
    temperature = db.Column(db.Float)
    weather = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<LotteryResult {self.draw_number}>'


# ==================== ОСНОВНЫЕ ФУНКЦИИ ЛОТЕРЕИ ====================

@app.route('/api/lottery/data')
def get_lottery_data():
    #API для получения всех лотерейных данных
    try:
        import sqlite3
        import os
        import json
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return jsonify({'success': False, 'message': 'БД не найдена', 'data': []})
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📊 Получаем ВСЕ данные из БД: {db_path}")
        
        cursor.execute("""
            SELECT draw_number, date, time, field_1, field_2, 
                   temperature, weather, pressure, created_at 
            FROM lottery_results 
            ORDER BY 
                CASE 
                    WHEN date != '' THEN date 
                    ELSE '01.01.1900' 
                END DESC,
                time DESC,
                draw_number DESC
             --  LIMIT 1000  <- раскомментируй если хочешь ограничение
        """)
        
        data = []
        rows = cursor.fetchall()
        print(f"📈 Найдено записей в БД: {len(rows)}")
        
        for row in rows:
            draw_number, date, time, field_1, field_2, temp, weather, pressure, created_at = row
            
            # Преобразуем JSON
            try:
                field1_list = json.loads(field_1) if field_1 else []
            except:
                field1_list = []
                
            try:
                field2_list = json.loads(field_2) if field_2 else []
            except:
                field2_list = []
            
            data.append({
                'tirage': draw_number,
                'date': date if date else '',
                'time': time if time else '',
                'field_1': field1_list,
                'field_2': field2_list,
                'created_at': created_at,
                'temperature': temp,
                'weather': weather if weather else '',
                'pressure': pressure,
                'added_at': created_at
            })
        
        conn.close()
        
        print(f"✅ Отправлено записей: {len(data)}")
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'source': 'database',
            'last_update': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f"❌ Ошибка в get_lottery_data: {e}")
        return jsonify({'success': False, 'message': str(e), 'data': []})

@app.route('/api/lottery/statistics')
def get_statistics():
    #API для получения реальной статистики из БД
    try:
        import sqlite3
        import os
        import json
        from flask import Response
        from collections import Counter
        
        # Используем тот же путь что и в get_lottery_data()
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'data', 'lottery.db')
        
        print(f"📊 Запуск статистики. БД: {db_path}")
        
        if not os.path.exists(db_path):
            return jsonify({
                'success': False,
                'message': 'БД не найдена'
            })
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(lottery_results)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"📊 Колонки в таблице: {columns}")
        
        all_numbers = []
        
        # ВАЖНО: Получаем числа из новой структуры (field_1 и field_2)
        if 'field_1' in columns and 'field_2' in columns:
            print("✅ Используем новую структуру (field_1, field_2)")
            
            # Получаем ВСЕ числа из field_1 и field_2
            cursor.execute("SELECT field_1, field_2 FROM lottery_results")
            
            for field1_json, field2_json in cursor.fetchall():
                try:
                    if field1_json:
                        numbers1 = json.loads(field1_json)
                        all_numbers.extend(numbers1)
                except:
                    pass
                
                try:
                    if field2_json:
                        numbers2 = json.loads(field2_json)
                        all_numbers.extend(numbers2)
                except:
                    pass
                    
        elif 'numbers' in columns:
            print("⚠️ Используем старую структуру (numbers)")
            cursor.execute("SELECT numbers FROM lottery_results WHERE numbers IS NOT NULL")
            for (nums_json,) in cursor.fetchall():
                if nums_json:
                    try:
                        numbers = json.loads(nums_json)
                        all_numbers.extend(numbers)
                    except:
                        pass
        else:
            print("❌ Неизвестная структура таблицы")
            conn.close()
            return jsonify({
                'success': False,
                'message': 'Неизвестная структура таблицы'
            })
        
        conn.close()
        
        print(f"📊 Собрано чисел для анализа: {len(all_numbers)}")
        
        if not all_numbers:
            return jsonify({
                'success': False,
                'message': 'Нет данных для анализа'
            })
        
        # РАСШИРЕННАЯ СТАТИСТИКА
        counter = Counter(all_numbers)
        total_numbers = len(all_numbers)
        total_draws = len(all_numbers) // 8  # Примерно, так как 8 чисел на тираж
        
        print(f"📊 Всего чисел: {total_numbers}, примерно тиражей: {total_draws}")
        
        # Статистика для каждого числа (1-20)
        all_stats = []
        for num in range(1, 21):  # Для лотереи 4x20 числа от 1 до 20
            count = counter.get(num, 0)
            percentage = round((count / total_numbers) * 100, 2) if total_numbers > 0 else 0
            
            # Рассчитываем сколько раз должно выпадать теоретически
            # В каждом тираже 8 чисел из 20, вероятность для каждого числа = 8/20 = 0.4
            expected_count = total_draws * 0.4 if total_draws > 0 else 0
            deviation = round((count - expected_count) / expected_count * 100, 2) if expected_count > 0 else 0
            
            # Определяем статус (выпадает чаще/реже чем должно)
            if count > expected_count * 1.1:  # на 10% чаще
                status = 'hot'
                status_text = 'Горячее'
            elif count < expected_count * 0.9:  # на 10% реже
                status = 'cold'
                status_text = 'Холодное'
            else:
                status = 'normal'
                status_text = 'Нормальное'
            
            all_stats.append({
                'number': num,
                'count': count,
                'percentage': percentage,
                'expected_count': round(expected_count, 1),
                'deviation': deviation,
                'status': status,
                'status_text': status_text,
                'last_draw': None  # Можно позже добавить
            })
        
        # Сортируем по частоте (самые частые сверху)
        all_stats_sorted = sorted(all_stats, key=lambda x: x['count'], reverse=True)
        
        # Дополнительная статистика
        most_common = counter.most_common(5)
        least_common = counter.most_common()[:-6:-1]  # 5 наименее частых
        
        # Формируем данные для ответа
        statistics_data = {
            'summary': {
                'total_numbers': total_numbers,
                'total_draws': total_draws,
                'unique_numbers': len(counter),
                'avg_per_draw': round(total_numbers / total_draws, 2) if total_draws > 0 else 0
            },
            'top_numbers': all_stats_sorted[:12],
            'bottom_numbers': all_stats_sorted[-12:],
            'all_numbers': all_stats_sorted,
            'most_common': [{'number': num, 'count': cnt} for num, cnt in most_common],
            'least_common': [{'number': num, 'count': cnt} for num, cnt in least_common],
            'hot_numbers': [num for num in all_stats if num['status'] == 'hot'],
            'cold_numbers': [num for num in all_stats if num['status'] == 'cold']
        }
        
        response_data = {
            'success': True,
            'statistics': statistics_data,
            'last_update': datetime.now().isoformat()
        }
        
        # Используем Response с ensure_ascii=False
        return Response(
            json.dumps(response_data, ensure_ascii=False),  # отключаем ASCII конвертацию
            mimetype='application/json; charset=utf-8'      # указываем кодировку
        )
        
    except Exception as e:
        print(f"❌ Ошибка в статистике: {e}")
        import traceback
        traceback.print_exc()
        
        # Для ошибок используем кодировку
        error_response = {
            'success': False,
            'message': f'Ошибка: {str(e)}'
        }
        
        return Response(
            json.dumps(error_response, ensure_ascii=False),
            mimetype='application/json; charset=utf-8',
            status=500
        )

@app.route('/api/lottery/predictions') # API для прогнозов
def get_predictions():
    import random
    
    # Простой прогноз: случайные числа
    numbers = list(range(1, 21))
    random.shuffle(numbers)
    
    return jsonify({
        'success': True,
        'prediction': {
            'field_1': numbers[:4],
            'field_2': numbers[4:8],
            'probability': round(random.uniform(10, 50), 2),
            'confidence': 'medium'
        }
    })

@app.route('/api/run-parser', methods=['POST'])
def run_parser_api():
    #API для запуска парсера
    try:
        print("🔄 API: Запуск парсера...")
        
        # Импортируем парсер
        try:
            # Пробуем импорт из новой структуры
            from src.parsers.lottery_parser import run_parser_sync
        except ImportError:
            try:
                # Пробуем старый путь
                from parsers.lottery_parser import run_parser_sync
            except ImportError:
                try:
                    # Пробуем прямой импорт
                    from lottery_parser import run_parser_sync
                except ImportError:
                    return jsonify({
                        'success': False,
                        'message': 'Парсер не найден'
                    }), 404
        
        # Запускаем парсер
        saved_count = run_parser_sync()
        
        if saved_count > 0:
            return jsonify({
                'success': True,
                'message': f'Парсер успешно выполнен. Сохранено {saved_count} новых записей',
                'saved_count': saved_count,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Парсер выполнен, но новых данных не найдено',
                'saved_count': 0,
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"❌ Ошибка при запуске парсера: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        }), 500


# ==================== ФУНКЦИИ ПОГОДЫ ====================

@app.route('/api/weather/current')
def get_current_weather():
    #Получить текущую погоду
    try:
        from src.parsers.weather_parser import WeatherParser
        parser = WeatherParser()
        weather = parser.get_current_weather()
        
        if weather:
            # 1. ПРОВЕРКА НА ДЕМО-ДАННЫЕ ПЕРЕД СОХРАНЕНИЕМ
            is_demo = (
                weather.get('is_demo') or 
                weather.get('temperature') == 0 or 
                weather.get('pressure_mmhg') == 0 or
                weather.get('city', '').lower() in ['демо', 'demo', 'тест', 'test']
            )
            
            if not is_demo:
                # Сохраняем в БД только если НЕ демо
                saved = parser.save_weather_to_db(weather)
                if saved:
                    parser.update_latest_weather_to_lottery(weather)
                    print(f"🔗 Погода привязана к тиражам")
                else:
                    print(f"⚠️ Погода не сохранена (демо или ошибка)")
            else:
                print(f"⚠️ Получены демо-данные, пропускаем сохранение")
            
            # 2. ВСЕГДА возвращаем данные (даже демо) для отображения
            return jsonify({
                'success': True,
                'data': weather,
                'saved_to_db': not is_demo,  # флаг сохранено ли в БД
                'is_demo_data': is_demo,     # флаг демо-данных
                'message': 'Погодные данные получены' + (' (демо)' if is_demo else '')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Не удалось получить погодные данные'
            }), 500
            
    except Exception as e:
        print(f"❌ Ошибка API погоды: {e}")
        # Возвращаем демо-данные при ошибке
        demo_weather = {
            'temperature': 0.0,
            'pressure_mmhg': 0,
            'humidity': 0,
            'weather_description': 'ошибка получения данных',
            'city': 'Демо',
            'is_demo': True,
            'note': 'Временные данные из-за ошибки API'
        }
        
        return jsonify({
            'success': True,  # все равно success чтобы фронт не сломался
            'data': demo_weather,
            'saved_to_db': False,
            'is_demo_data': True,
            'message': f'Ошибка API, показаны демо-данные: {str(e)[:50]}'
        })

@app.route('/api/weather/history')
def get_weather_history():
    # API для получения исторических данных погоды
    try:
        import sqlite3
        import os
        from datetime import datetime
        
        # Получаем параметры
        limit = request.args.get('limit', default=7, type=int)
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return jsonify({'success': False, 'message': 'БД не найдена', 'data': []})
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Это важно для dict(row)
        cursor = conn.cursor()
        
        # Проверяем есть ли таблица
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_history'")
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Таблица погоды не найдена', 'data': []})
        
        # Получаем данные с ВСЕМИ полями
        cursor.execute("""
            SELECT 
                id, timestamp, temperature, feels_like, 
                weather_description, humidity, pressure_mmhg, pressure_hpa,
                wind_speed, wind_direction, visibility, cloudiness, city, created_at
            FROM weather_history 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        # Преобразуем в список словарей
        data = []
        for row in cursor.fetchall():
            item = dict(row)
            
            # Конвертируем datetime в строку (если нужно)
            if 'timestamp' in item and item['timestamp']:
                if hasattr(item['timestamp'], 'isoformat'):
                    item['timestamp'] = item['timestamp'].isoformat()
                else:
                    item['timestamp'] = str(item['timestamp'])
            
            if 'created_at' in item and item['created_at']:
                if hasattr(item['created_at'], 'isoformat'):
                    item['created_at'] = item['created_at'].isoformat()
                else:
                    item['created_at'] = str(item['created_at'])
            
            data.append(item)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'data': []})

@app.route('/api/weather/test')
def test_weather_api():
    """Тестовый endpoint для проверки данных"""
    try:
        import sqlite3
        import os
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return jsonify({'success': False, 'message': f'Файл БД не найден: {db_path}'})
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        
        # 2. Проверяем структуру weather_history
        cursor.execute("PRAGMA table_info(weather_history)")
        columns = cursor.fetchall()
        
        # 3. Проверяем количество записей
        cursor.execute("SELECT COUNT(*) FROM weather_history")
        count = cursor.fetchone()[0]
        
        # 4. Берем пример записи
        cursor.execute("SELECT * FROM weather_history ORDER BY timestamp DESC LIMIT 1")
        example = cursor.fetchone()
        column_names = [description[0] for description in cursor.description]
        
        conn.close()
    
        return jsonify({
            'success': True,
            'db_exists': True,
            'tables': [t[0] for t in tables],
            'weather_columns': [{'id': c[0], 'name': c[1], 'type': c[2]} for c in columns],
            'total_records': count,
            'example_record': dict(zip(column_names, example)) if example else None,
            'message': 'База данных подключена успешно'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/weather/types')
def get_weather_types():
    """Получить все уникальные типы погоды из БД"""
    try:
        import sqlite3
        import os
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return jsonify({'success': False, 'types': []})
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем уникальные типы погоды и сколько тиражей для каждого
        cursor.execute("""
            SELECT 
                wh.weather_description,
                COUNT(DISTINCT lr.draw_number) as draw_count
            FROM weather_history wh
            LEFT JOIN lottery_results lr ON 
                DATE(wh.timestamp) = (
                    '2026-01-' || 
                    CASE 
                        WHEN INSTR(lr.date, '.') = 2 THEN '0' || SUBSTR(lr.date, 1, 1)
                        ELSE SUBSTR(lr.date, 1, 2)
                    END
                )
            WHERE wh.weather_description IS NOT NULL 
                AND wh.weather_description != ''
            GROUP BY wh.weather_description
            ORDER BY draw_count DESC, wh.weather_description
        """)
        
        types = [{'type': row[0], 'count': row[1]} for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'types': types,
            'count': len(types)
        })
        
    except Exception as e:
        print(f"❌ Ошибка в get_weather_types: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ==================== FELIX PILA ФУНКЦИИ ====================

@app.route('/api/felix-pila/analysis')
def get_felix_pila_analysis():
    """Анализ с фильтрами"""
    try:
        import sqlite3
        import os
        import json
        from collections import Counter
        
        # Простые фильтры
        weather_filter = request.args.get('weather', '').lower()
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return jsonify(generate_demo_analysis())
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Простой запрос
        cursor.execute("""
            SELECT field_1, field_2, temperature, weather 
            FROM lottery_results 
            WHERE temperature IS NOT NULL AND weather IS NOT NULL
            LIMIT 100
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if len(rows) < 10:
            return jsonify(generate_demo_analysis())
        
        # Применяем фильтры
        filtered_rows = []
        for field1_json, field2_json, temp, weather in rows:
            matches = True
            
            if weather_filter and weather:
                if weather_filter not in str(weather).lower():
                    matches = False
            
            if matches:
                filtered_rows.append((field1_json, field2_json, temp, weather))
        
        print(f"📊 Для анализа: {len(filtered_rows)} записей")
        
        # Анализ
        high_humidity_field1 = []
        high_pressure_field1 = []
        
        # Простой анализ - всегда возвращаем что-то
        for field1_json, field2_json, temp, weather in filtered_rows[:20]:  # Берем первые 20
            if field1_json:
                try:
                    numbers = json.loads(field1_json)
                    high_humidity_field1.extend(numbers)  # Показываем все числа
                    high_pressure_field1.extend(numbers)
                except:
                    pass
        
        # Берем топ-5 частых чисел
        def get_top_5(numbers_list):
            if not numbers_list:
                return [random.randint(1, 20) for _ in range(5)]
            counter = Counter(numbers_list)
            return [num for num, _ in counter.most_common(5)]
        
        return jsonify({
            "success": True,
            "has_data": True,
            "filtered_count": len(filtered_rows),
            "analysis": {
                "by_humidity": {
                    "high": {
                        "field_1": get_top_5(high_humidity_field1),
                        "field_2": get_top_5([])
                    }
                },
                "by_pressure": {
                    "high": {
                        "field_1": get_top_5(high_pressure_field1),
                        "field_2": get_top_5([])
                    }
                },
                "stats": {
                    "total_records": len(filtered_rows)
                }
            }
        })
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return jsonify(generate_demo_analysis())

@app.route('/api/felix-pila/predict')
def get_felix_pila_predict():
    """Прогноз с РЕАЛЬНЫМИ фильтрами через SQL JOIN"""
    try:
        import sqlite3
        import os
        import json
        import random
        from collections import Counter
        
        # Получаем фильтры
        weather_filter = request.args.get('weather', '').lower()
        temp_filter = request.args.get('temp', '')
        humidity_filter = request.args.get('humidity', '')
        pressure_filter = request.args.get('pressure', '')
        wind_speed_filter = request.args.get('wind_speed', '')
        wind_dir_filter = request.args.get('wind_dir', '')
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return get_no_data_response(0, "БД не найдена")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Подзапрос с агрегацией
        sql = """
            SELECT *
            FROM (
                SELECT 
                    lr.field_1, 
                    lr.field_2,
                    ROUND(AVG(wh.temperature)) as temperature,
                    wh.weather_description,
                    ROUND(AVG(wh.humidity)) as humidity,
                    ROUND(AVG(wh.pressure_mmhg)) as pressure_mmhg,
                    ROUND(AVG(wh.wind_speed)) as wind_speed,
                    wh.wind_direction,
                    lr.draw_number,
                    lr.date
                FROM lottery_results lr
                INNER JOIN weather_history wh ON 
                    DATE(wh.timestamp) = (
                        '2026-01-' || 
                        CASE 
                            WHEN INSTR(lr.date, '.') = 2 THEN '0' || SUBSTR(lr.date, 1, 1)
                            ELSE SUBSTR(lr.date, 1, 2)
                        END
                    )
                -- Группируем и по погоде тоже!
                GROUP BY lr.draw_number, lr.date, wh.weather_description
            ) as aggregated
            WHERE 1=1
        """
        
        # ИНИЦИАЛИЗИРУЕМ params ПЕРЕД использованием
        params = []
        
        # Фильтры по вычисленным полям
        if weather_filter:
            # Простой LIKE - данные уже в нижнем регистре
            sql += " AND aggregated.weather_description LIKE ?"
            params.append(f"%{weather_filter}%")
        
        if temp_filter and '_' in temp_filter:
            try:
                min_temp, max_temp = temp_filter.split('_')
                sql += " AND aggregated.temperature BETWEEN ? AND ?"
                params.extend([int(min_temp), int(max_temp)])
            except:
                pass
        
        if humidity_filter and '_' in humidity_filter:
            try:
                min_hum, max_hum = humidity_filter.split('_')
                sql += " AND aggregated.humidity BETWEEN ? AND ?"
                params.extend([int(min_hum), int(max_hum)])
            except:
                pass
        
        if pressure_filter and '_' in pressure_filter:
            try:
                min_pressure, max_pressure = pressure_filter.split('_')
                sql += " AND aggregated.pressure_mmhg BETWEEN ? AND ?"
                params.extend([float(min_pressure), float(max_pressure)])
                print(f"🌡️ Фильтр давления: {min_pressure}-{max_pressure} мм")
            except Exception as e:
                print(f"⚠️ Ошибка фильтра давления: {e}")
                pass
        elif pressure_filter:  # для старых значений (если остались где-то)
            try:
                pressure_value = int(pressure_filter)
                sql += " AND aggregated.pressure_mmhg BETWEEN ? AND ?"
                params.extend([pressure_value - 2, pressure_value + 2])
            except:
                pass
        
        if wind_speed_filter and '_' in wind_speed_filter:
            try:
                min_ws, max_ws = wind_speed_filter.split('_')
                sql += " AND aggregated.wind_speed BETWEEN ? AND ?"
                params.extend([float(min_ws), float(max_ws)])
            except:
                pass
        
        if wind_dir_filter:
            sql += " AND LOWER(aggregated.wind_direction) LIKE ?"
            params.append(f"%{wind_dir_filter}%")
        
        sql += " ORDER BY aggregated.date DESC, aggregated.draw_number DESC"
        sql += " LIMIT 100"
        
        print(f"🔍 SQL: {sql[:200]}...")
        print(f"📊 Параметры: {params}")
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        print(f"📊 Найдено тиражей: {len(rows)}")
        
        if len(rows) < 1:
            return get_no_data_response(len(rows), f"нет тиражей ({len(rows)} записей)")
        
        # Анализируем отфильтрованные данные - ИНИЦИАЛИЗИРУЕМ переменные
        field1_numbers = []
        field2_numbers = []
        
        for row in rows:
            field1_json, field2_json = row[0], row[1]
            
            if field1_json:
                try:
                    numbers1 = json.loads(field1_json)
                    field1_numbers.extend(numbers1)
                except:
                    pass
            
            if field2_json:
                try:
                    numbers2 = json.loads(field2_json)
                    field2_numbers.extend(numbers2)
                except:
                    pass
        
        print(f"📊 Собрано чисел: field1={len(field1_numbers)}, field2={len(field2_numbers)}")
        
        # Даже если мало чисел - всё равно пытаемся сделать прогноз
        if len(field1_numbers) < 4 or len(field2_numbers) < 4:
            print(f"⚠️ Мало чисел: field1={len(field1_numbers)}, field2={len(field2_numbers)}")
            # Продолжаем - дополним случайными числами
        
        # Генерация прогноза
        counter1 = Counter(field1_numbers)
        counter2 = Counter(field2_numbers)

        print(f"📊 Анализ чисел: всего field1={len(field1_numbers)}, уникальных={len(counter1)}")
        print(f"📊 Top 5 field1: {counter1.most_common(5)}")
        print(f"📊 Top 5 field2: {counter2.most_common(5)}")
        
        # Даже если counter пустой - создаем демо-данные
        if not counter1:
            print("ℹ️ counter1 пустой, создаем начальные числа")
            field1_pred = []
        else:
            field1_pred = [num for num, _ in counter1.most_common(4)]

        if not counter2:
            print("ℹ️ counter2 пустой, создаем начальные числа")
            field2_pred = []
        else:
            field2_pred = [num for num, _ in counter2.most_common(4)]

        print(f"📊 Выбранные числа field1: {field1_pred}")
        print(f"📊 Выбранные числа field2: {field2_pred}")

        # Дополняем если не хватает
        all_numbers = list(set(field1_numbers + field2_numbers))
        
        while len(field1_pred) < 4:
            if all_numbers:
                num = random.choice(all_numbers)
            else:
                num = random.randint(1, 20)
            if num not in field1_pred:
                field1_pred.append(num)

        while len(field2_pred) < 4:
            if all_numbers:
                num = random.choice(all_numbers)
            else:
                num = random.randint(1, 20)
            if num not in field2_pred:
                field2_pred.append(num)

        # === ИСПРАВЛЕННЫЙ РАСЧЕТ ВЕРОЯТНОСТЕЙ ===
        print(f"📊 Количество тиражей: {len(rows)}")
        print(f"📊 Частота чисел field1 в тиражах: { {num: counter1[num] for num in field1_pred} }")
        print(f"📊 Частота чисел field2 в тиражах: { {num: counter2[num] for num in field2_pred} }")

        # Вероятности на основе частоты в тиражах
        def add_probs(numbers, counter, total_tirages):
            result = []
            for num in numbers:
                frequency = counter.get(num, 0)  # в скольких тиражах выпало число
                # Вероятность = (в скольких тиражах выпало / всего тиражей) * 100
                probability = int((frequency * 100) / max(1, total_tirages))
                # Ограничиваем диапазон 20-95%
                probability = min(95, max(20, probability))
                result.append({
                    "number": num,
                    "probability": probability
                })
            return result

        total_tirages = len(rows)  # количество тиражей (например 20)
        field1_probs = add_probs(field1_pred, counter1, total_tirages)
        field2_probs = add_probs(field2_pred, counter2, total_tirages)

        print(f"📊 Вероятности field1: {field1_probs}")
        print(f"📊 Вероятности field2: {field2_probs}")
        # === КОНЕЦ ИСПРАВЛЕННОГО РАСЧЕТА ===

        # Уверенность зависит от количества данных
        confidence = min(0.9, max(0.3, len(rows) / 10))

        return jsonify({
            "success": True,
            "has_data": True,
            "prediction": {
                "field_1": field1_probs,
                "field_2": field2_probs
            },
            "confidence": round(confidence, 2),
            "filtered_count": len(rows),
            "note": f"На основе {len(rows)} тиражей" + (f" (фильтр: {temp_filter})" if temp_filter else "")
        })
        
    except Exception as e:
        print(f"❌ Ошибка в get_felix_pila_predict: {e}")
        import traceback
        traceback.print_exc()
        return get_no_data_response(0, f"ошибка: {str(e)[:30]}")


# ==================== ОСНОВНЫЕ МАРШРУТЫ ====================

@app.route('/')
def index():
    # Главная страница
    try:
        # Подключаемся напрямую к БД lottery.db в папке data
        import sqlite3
        import os
        
        # Формируем правильный путь
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'data', 'lottery.db')
        
        print(f"🔍 Ищу БД по пути: {db_path}")  # Для отл#адки
        
        # Проверяем существует ли файл
        if not os.path.exists(db_path):
            print(f"❌ Файл БД не найден: {db_path}")
            total_records = 0
        else:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Считаем записи в таблице lottery_results
            cursor.execute("SELECT COUNT(*) FROM lottery_results")
            total_records = cursor.fetchone()[0]
            
            conn.close()
            
    except Exception as e:
        print(f"Ошибка при подсчете записей: {e}")
        total_records = 0
    
    stats = {
        'project_name': 'LottoMeteoStats',
        'current_date': datetime.now().strftime("%d.%m.%Y %H:%M"),
        'version': app_version,
        'total_records': total_records,
        'features': [
            'Анализ лотерейных данных',
            'Интеграция с погодными API',
            'Статистика выпадения номеров',
            'Визуализация результатов'
        ]
    }
    return render_template('index.html', **stats)

@app.route('/lottery')
def lottery_page():
    # Страница с лотерейными данными
    return render_template('lottery.html', version=app_version)

@app.route('/weather')
def weather_page():
     # Страница с погодными данными
    return render_template('weather.html', version=app_version)

@app.route('/admin')
def admin_panel():
    # Панель администратора
    return render_template('admin.html', version=app_version)

@app.route('/statistics')
def statistics_page():
     # Страница статистики
    return render_template('statistics.html', version=app_version)

@app.route('/predictions')
def predictions_page():
     # Страница Felix Pila с предсказаниями
    current_date = datetime.now().strftime("%d.%m.%Y")
    return render_template('felix_pila.html', 
                          current_date=current_date,
                          version=app_version)

@app.route('/graphs')
def graphs_page():
    # Страница графиков
    return render_template('graphs.html')

@app.route('/api/health')
def health_check():
    # Проверка работоспособности
    try:
        import sqlite3
        import os
        
        # Тот же путь что везде
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'data', 'lottery.db')
        
        print(f"🔍 health_check ищет БД: {db_path}")
        
        if not os.path.exists(db_path):
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'message': 'Сайт работает (файл БД не найден)',
                'database': 'file not found',
                'records': 0
            })
        
        # Подключаемся и считаем
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # Проверяем есть ли таблица
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lottery_results'")
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                conn.close()
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.now().isoformat(),
                    'message': 'Сайт работает (таблица не найдена)',
                    'database': 'table not found',
                    'records': 0
                })
            
            # Считаем записи
            cursor.execute("SELECT COUNT(*) FROM lottery_results")
            record_count = cursor.fetchone()[0]
            
            conn.close()
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'message': 'Сайт работает',
                'database': f'connected ({record_count} записей)',
                'records': record_count,
                'db_file': db_path
            })
            
        except Exception as db_error:
            conn.close()
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'message': f'Сайт работает (ошибка БД)',
                'database': f'error: {str(db_error)[:50]}',
                'records': 0
            })
            
    except Exception as e:
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'message': 'Сайт работает (ошибка проверки)',
            'database': f'error: {str(e)[:50]}',
            'records': 0
        })

# Контекстный процессор для автоматической передачи версии во все шаблоны
@app.context_processor
def inject_version():
    return dict(version=app_version)


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_lottery_data():
    # Получение данных лотереи Используем существующую функцию
    from flask import jsonify
    import sqlite3
    import os
    import json
    
    db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
    
    if not os.path.exists(db_path):
        return []
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT field_1, field_2, temperature, weather 
        FROM lottery_results 
        WHERE temperature IS NOT NULL
    """)
    
    data = []
    for field_1, field_2, temp, weather in cursor.fetchall():
        try:
            numbers1 = json.loads(field_1) if field_1 else []
            numbers2 = json.loads(field_2) if field_2 else []
            data.append({
                'numbers': numbers1 + numbers2,
                'temperature': temp,
                'weather': weather
            })
        except:
            continue
    
    conn.close()
    return data

def get_weather_data():
    # Получение данных погоды
    try:
        import sqlite3
        import os
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return []
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT temperature, weather_description, humidity, pressure_mmhg
            FROM weather_history 
            ORDER BY timestamp DESC
            LIMIT 100
        """)
        
        data = []
        for temp, desc, humidity, pressure in cursor.fetchall():
            data.append({
                'temperature': temp,
                'weather': desc,
                'humidity': humidity,
                'pressure': pressure
            })
        
        conn.close()
        return data
    except:
        return []

def analyze_by_humidity(lottery_data, weather_data): #==========================
    # Анализ чисел по влажности
    return {
        "low_humidity": [2, 6, 10, 14, 18],
        "medium_humidity": [3, 7, 11, 15, 19],
        "high_humidity": [1, 5, 9, 13, 17],
        "correlation": 0.25
    }

def analyze_by_weather_type(lottery_data, weather_data):
    # Анализ чисел по типу погоды
    return {
        "sunny": [4, 8, 12, 16, 20],
        "cloudy": [2, 6, 10, 14, 18],
        "rainy": [1, 5, 9, 13, 17],
        "snowy": [3, 7, 11, 15, 19]
    }

def analyze_by_temperature(lottery_data, weather_data):
    # Анализ чисел по температуре
    # Реальная логика анализа
    # Пока вернем демо-данные
    return {
        "cold_days": [3, 7, 12, 15, 18],
        "warm_days": [2, 5, 8, 11, 16],
        "hot_days": [1, 4, 9, 14, 20],
        "correlation": 0.42
    }

def analyze_by_pressure(lottery_data, weather_data):
    # Анализ чисел по давлению----------------------------------------------------------------------
    return {
        "low_pressure": [6, 10, 13, 17],
        "normal_pressure": [2, 5, 9, 12],
        "high_pressure": [1, 4, 8, 11],
        "correlation": 0.38
    }

def predict_numbers(current_weather, lottery_data, weather_data):
    # Прогнозирование чисел на основе погоды
    # Базовая логика предсказания
    import random
    
    # На основе температуры
    temp = current_weather.get('temperature', 20)
    if temp < 10:
        base_numbers = [3, 7, 12, 15]
    elif temp < 20:
        base_numbers = [2, 5, 8, 11]
    else:
        base_numbers = [1, 4, 9, 14]
    
    # Добавляем случайные числа
    prediction = base_numbers + random.sample(range(1, 21), 6)
    prediction = list(set(prediction))[:10]  # Уникальные, максимум 10
    
    return {
        "recommended_numbers": sorted(prediction),
        "weather_influence": {
            "temperature_impact": "Высокая" if abs(temp - 15) > 5 else "Средняя",
            "pressure_impact": "Средняя",
            "humidity_impact": "Низкая"
        }
    }

def generate_demo_prediction():
    """Генерация демо-прогноза для Felix Pila"""
    import random
    numbers = list(range(1, 21))
    random.shuffle(numbers)
    
    return {
        "field_1": [
            {"number": numbers[0], "probability": 75},
            {"number": numbers[1], "probability": 72},
            {"number": numbers[2], "probability": 68},
            {"number": numbers[3], "probability": 65}
        ],
        "field_2": [
            {"number": numbers[4], "probability": 78},
            {"number": numbers[5], "probability": 74},
            {"number": numbers[6], "probability": 71},
            {"number": numbers[7], "probability": 67}
        ]
    }

def get_simple_demo(reason=""):
    # Простой демо-ответ с числами 0 чтобы было видно что это тест--------------------------------------------------
    return jsonify({
        "success": True,
        "has_data": False,  # Всегда false для демо
        "prediction": {
            "field_1": [
                {"number": 0, "probability": 0},
                {"number": 0, "probability": 0},
                {"number": 0, "probability": 0},
                {"number": 0, "probability": 0}
            ],
            "field_2": [
                {"number": 0, "probability": 0},
                {"number": 0, "probability": 0},
                {"number": 0, "probability": 0},
                {"number": 0, "probability": 0}
            ]
        },
        "confidence": 0,
        "note": f"ТЕСТОВЫЕ ДАННЫЕ ({reason}) - числа 0",
        "warning": "⚠️ Это демо-данные, а не реальный прогноз!"
    })#-------------------------------------------------------------------------------------------------------------------

def generate_demo_analysis():
    """Генерация демо-данных для анализа Felix Pila"""
    return {
        "success": True,
        "analysis": {
            "by_weather": {
                "sunny": {
                    "field_1": [3, 7, 12, 16, 19],
                    "field_2": [2, 8, 11, 15, 20]
                },
                "rainy": {
                    "field_1": [1, 5, 9, 13, 17],
                    "field_2": [4, 6, 10, 14, 18]
                }
            },
            "by_temperature": {
                "cold": {
                    "field_1": [2, 6, 10, 14, 18],
                    "field_2": [3, 7, 11, 15, 19]
                },
                "warm": {
                    "field_1": [1, 4, 8, 12, 16],
                    "field_2": [5, 9, 13, 17, 20]
                }
            },
            "stats": {
                "total_records": 150,
                "analysis_based_on": "Демо-данные"
            }
        }
    }

def generate_demo_weather():
    # Генерация демо-данных о погоде С НУЛЕВЫМИ ЗНАЧЕНИЯМИ
    return {
        "temperature": 0.0,      # 0 градусов
        "pressure": 0,           # 0 мм рт.ст.
        "humidity": 0,           # 0%
        "weather_type": "демо",  # метка что это демо
        "wind_speed": 0.0,       # 0 м/с
        "city": "Демо-город",
        "is_demo": True          # флаг что это демо-данные
    }

def parse_filters_from_request():
    """Парсим фильтры из запроса"""
    filters = {}
    
    # Погода
    weather = request.args.get('weather')
    if weather:
        filters['weather'] = weather
    
    # Температура (диапазон)
    temp = request.args.get('temp')
    if temp:
        try:
            min_temp, max_temp = temp.split('_')
            filters['temp_min'] = float(min_temp)
            filters['temp_max'] = float(max_temp)
        except:
            pass
    
    # Влажность (диапазон)
    humidity = request.args.get('humidity')
    if humidity:
        try:
            min_hum, max_hum = humidity.split('_')
            filters['humidity_min'] = int(min_hum)
            filters['humidity_max'] = int(max_hum)
        except:
            pass
    
    # Давление (точное значение)
    pressure = request.args.get('pressure')
    if pressure:
        try:
            filters['pressure'] = int(pressure)
        except:
            pass
    
    # Скорость ветра (диапазон)
    wind_speed = request.args.get('wind_speed')
    if wind_speed:
        try:
            min_ws, max_ws = wind_speed.split('_')
            filters['wind_speed_min'] = float(min_ws)
            filters['wind_speed_max'] = float(max_ws)
        except:
            pass
    
    # Направление ветра
    wind_dir = request.args.get('wind_dir')
    if wind_dir:
        filters['wind_direction'] = wind_dir
    
    # Фаза луны
    moon = request.args.get('moon')
    if moon:
        filters['moon_phase'] = moon
    
    return filters

def calculate_confidence(prediction):
    # Расчет уверенности в прогнозе  ====================================
    # Базовая логика
    return 0.75

def get_current_weather():
    # Получение текущей погоды
    # Здесь должна быть логика получения реальных данных
    # Пока вернем демо
    return generate_demo_weather()

def get_top_weather_combinations(lottery_data, weather_data):
    # Топ комбинации погода-числа
    return [
        {"weather": "ясно", "numbers": [7, 14, 3], "frequency": 12},
        {"weather": "дождь", "numbers": [5, 12, 18], "frequency": 8},
        {"weather": "облачно", "numbers": [2, 9, 16], "frequency": 10},
        {"weather": "туман", "numbers": [1, 8, 15], "frequency": 4},
        {"weather": "ветрено", "numbers": [4, 11, 19], "frequency": 6}
    ]

def get_no_data_response(count, reason=""):
    """Ответ когда данных нет после фильтрации"""
    return jsonify({
        "success": True,
        "has_data": False,
        "prediction": None,
        "confidence": 0,
        "filtered_count": count,
        "note": f"Нет данных ({reason})" if reason else f"Нет данных ({count} записей)"
    })

# ==================== ФУНКЦИИ ПЛАНИРОВЩИКА ====================

def job_lottery_with_weather():
    # Собирает лотерею и сразу привязывает текущую погоду
    print(f"\n{'='*50}")
    print(f"⏰ Автосбор лотереи + погода: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    try:
        # 1. Сначала собираем погоду
        parser = WeatherParser()
        weather = parser.get_current_weather()
        
        if weather:
            parser.save_weather_to_db(weather)
            print(f"🌤️ Погода собрана: {weather['temperature']}°C")
        
        # 2. Собираем лотерею
        data = run_parser_sync()
        
        if data:
            print(f"✅ Лотерея: собрано {len(data)} тиражей")
            
            # 3. Если есть погода, обновляем последние тиражи
            if weather:
                parser.update_latest_weather_to_lottery(weather)
                print(f"🔗 Погода привязана к последним тиражам")
            
            return True
        else:
            print("❌ Лотерея: не удалось собрать данные")
            return False
            
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        return False

def job_weather_only():
    print(f"🌤️ Сбор погоды: {datetime.now().strftime('%H:%M:%S')}")
    try:
        from src.parsers.weather_parser import WeatherParser
        parser = WeatherParser()
        weather = parser.get_current_weather()
        
        if weather:
            # Проверяем, не демо ли это (0 значения или есть флаг)
            if (weather.get('temperature') == 0 or 
                weather.get('is_demo') or 
                weather.get('city') == 'Демо-город'):
                print("⚠️ Получены демо-данные, пропускаем сохранение")
                return
            
            parser.save_weather_to_db(weather)
            parser.update_latest_weather_to_lottery(weather)
            print(f"✅ Погода сохранена: {weather['temperature']}°C")
    except Exception as e:
        print(f"❌ Ошибка сбора погоды: {e}")

def scheduler_loop():
    # Фоновый цикл планировщика
    def job_lottery_with_weather():
        """Задача: сбор лотереи и привязка погоды"""
        print(f"\n⏰ Сбор лотереи+погоды: {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # 1. Собираем лотерею
            from src.parsers.lottery_parser import run_parser_sync
            saved_count = run_parser_sync()
            
            if saved_count > 0:
                print(f"✅ Лотерея: сохранено {saved_count} записей")
            else:
                print("⚠️ Лотерея: новых данных нет")
            
            # 2. Собираем погоду
            from src.parsers.weather_parser import WeatherParser
            parser = WeatherParser()
            weather = parser.get_current_weather()
            
            if weather:
                # Сохраняем в историю погоды
                parser.save_weather_to_db(weather)
                # Привязываем к последним тиражам
                parser.update_latest_weather_to_lottery(weather)
                print(f"🌤️ Погода: {weather['temperature']}°C в {weather['city']}")
            
        except Exception as e:
            print(f"❌ Ошибка в задаче: {e}")

    def job_weather_only():
        # Задача: только сбор погоды
        print(f"🌤️ Сбор погоды: {datetime.now().strftime('%H:%M:%S')}")
        try:
            from src.parsers.weather_parser import WeatherParser
            parser = WeatherParser()
            weather = parser.get_current_weather()
            
            if weather:
                parser.save_weather_to_db(weather)
                print(f"✅ Погода сохранена: {weather['temperature']}°C")
        except Exception as e:
            print(f"❌ Ошибка сбора погоды: {e}")

    # НАСТРОЙКА РАСПИСАНИЯ
    print("✅ Планировщик настроен. Расписание:")
    
    # Основные времена лотереи (с привязкой погоды)
    lottery_times = ["10:00", "12:00", "13:00", "14:00", "16:00", "16:22", "18:00", "20:07", "22:00", "23:22"]
    for t in lottery_times:
        schedule.every().day.at(t).do(job_lottery_with_weather)
        print(f"  • Лотерея+погода в {t}")
    
    # Погода каждые 30 минут (кроме времени лотереи)
    for hour in range(8, 24):  # с 8:00 до 23:00
        time_str = f"{hour:02d}:00"  # сразу создаем время с :00
        if time_str not in lottery_times:
            schedule.every().day.at(time_str).do(job_weather_only)
    
    # Бесконечный цикл планировщика
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_background_scheduler():
    """Запускает планировщик в фоновом режиме"""
    import threading
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    print("✅ Фоновый планировщик запущен")


# ==================== CLI КОМАНДЫ ====================

@app.cli.command("create-db")
def create_db_command():
    # Создать таблицы в базе данных
    with app.app_context():
        db.create_all()
    print("✅ Таблицы созданы")

@app.cli.command("clear-db")
def clear_db_command():
    # Очистить базу данных
    with app.app_context():
        db.drop_all()
    print("🗑️ База данных очищена")

@app.cli.command("parse-lottery")
def parse_lottery_command():
    # Запустить парсер лотереи
    run_lottery_parser()

@app.cli.command("collect-data")
def collect_data_command():
    # Собрать данные лотереи и погоды сейчас
    print("🔄 Сбор данных...")
    # Собираем лотерею
    run_lottery_parser()
    # Собираем погоду
    try:
        from src.parsers.weather_parser import WeatherParser
        parser = WeatherParser()
        weather = parser.get_current_weather()
        if weather:
            print(f"✅ Погода: {weather['temperature']}°C в {weather['city']}")
        else:
            print("❌ Погода: не удалось получить данные")
    except Exception as e:
        print(f"⚠️ Погода: {e}")

@app.cli.command("init-project")
def init_project_command():
    # Инициализировать проект (первый запуск)
    print("🚀 Инициализация проекта LottoMeteoStats...")
    
    # 1. Создаем БД
    with app.app_context():
        db.create_all()
    print("✅ 1. База данных создана")
    
    # 2. Создаем необходимые папки
    folders = ['data', 'data/cache', 'data/exports', 'static/images', 'templates']
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ 2. Папка {folder} создана")
    
    # 3. Запускаем первый сбор данных
    print("✅ 3. Запускаем первый сбор данных...")
    collect_data_command()
    
    print("\n🎉 Проект инициализирован!")
    print("🌐 Запустите: python app.py")
    print("📊 Откройте: http://localhost:5000")

# ==================== ОСНОВНОЙ БЛОК ЗАПУСКА ====================

if __name__ == '__main__':
    print("=" * 60)
    print("🎰 LottoMeteoStats запущен!")
    print(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("🌐 Откройте в браузере: http://localhost:5000")
    print("=" * 60)
    
    # Автоматически создаем БД при первом запуске
    with app.app_context():
        try:
            db.create_all()
            print("✅ База данных проверена")
        except Exception as e:
            print(f"⚠️ Ошибка БД: {e}")
    
    # Запускаем фоновый планировщик (автоматически при старте)
    start_background_scheduler()
    
    # Запускаем Flask приложение
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', True)
    )