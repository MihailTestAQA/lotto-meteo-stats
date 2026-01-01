# Главный файл приложения LottoMeteoStats

from flask import Flask, render_template, jsonify, request
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

# Создаем экземпляр Flask приложения
app = Flask(__name__)
app.config.from_object(Config)

# Инициализируем базу данных
db = SQLAlchemy(app)

# Модель данных для лотереи
class LotteryResult(db.Model):
    """Модель для хранения результатов лотереи"""
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

# Маршруты приложения
@app.route('/')
def index():
    """Главная страница"""
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
        'version': '1.0.3',
        'total_records': total_records, #----------
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
    """Страница с лотерейными данными"""
    return render_template('lottery.html')

@app.route('/weather')
def weather_page():
    """Страница с погодными данными"""
    return render_template('weather.html')

@app.route('/admin')
def admin_panel():
    """Панель администратора"""
    return render_template('admin.html')

# Добавь после других роутов

@app.route('/statistics')
def statistics_page():
    """Страница статистики"""
    return render_template('statistics.html')

@app.route('/predictions')
def predictions_page():
    """Страница прогнозов Felix Pila"""
    return render_template('predictions.html')

@app.route('/graphs')
def graphs_page():
    """Страница графиков"""
    return render_template('graphs.html')

@app.route('/api/lottery/statistics')
def get_statistics():
    """API для получения реальной статистики из БД"""
    try:
        import sqlite3
        import os
        import json
        from flask import Response  # ← ДОБАВЬ ИМПОРТ
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
            # Старый код для обратной совместимости
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
        
        # ВАЖНО: Используем Response с ensure_ascii=False
        return Response(
            json.dumps(response_data, ensure_ascii=False),  # ← ОТКЛЮЧАЕМ ASCII КОНВЕРТАЦИЮ
            mimetype='application/json; charset=utf-8'      # ← УКАЗЫВАЕМ КОДИРОВКУ
        )
        
    except Exception as e:
        print(f"❌ Ошибка в статистике: {e}")
        import traceback
        traceback.print_exc()
        
        # Для ошибок тоже используем правильную кодировку
        error_response = {
            'success': False,
            'message': f'Ошибка: {str(e)}'
        }
        
        return Response(
            json.dumps(error_response, ensure_ascii=False),
            mimetype='application/json; charset=utf-8',
            status=500
        )

@app.route('/api/lottery/predictions')
def get_predictions():
    """API для прогнозов"""
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

# API endpoints
@app.route('/api/health')
def health_check():
    """Проверка работоспособности"""
    try:
        import sqlite3
        import os
        
        # Тот же путь что везде
        basedir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(basedir, 'data', 'lottery.db')
        
        print(f"🔍 health_check ищет БД: {db_path}")  # Отладка
        
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
                'records': record_count,  # ← ВАЖНО: должно быть число > 0
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

@app.route('/api/lottery/data')
def get_lottery_data():
    """API для получения всех лотерейных данных"""
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
        
        # ЗДЕСЬ ИЗМЕНЕНИЕ: УБИРАЕМ LIMIT ИЛИ СТАВИМ БОЛЬШОЙ
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
            -- LIMIT 1000  ← раскомментируй если хочешь ограничение
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
                'time': time if time else '15:00',
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

@app.route('/api/weather/current')
def get_current_weather():
    """Получить текущую погоду"""
    try:
        from src.parsers.weather_parser import WeatherParser
        parser = WeatherParser()
        weather = parser.get_current_weather()
        
        if weather:
            # Сохраняем в БД и привязываем к тиражам
            parser.save_weather_to_db(weather)
            parser.update_latest_weather_to_lottery(weather)  # ← ДОБАВЬ ЭТУ СТРОКУ!
            
            print(f"🔗 Погода привязана к тиражам")
            
            return jsonify({
                'success': True,
                'data': weather,
                'message': 'Погодные данные получены'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Не удалось получить погодные данные'
            }), 500
            
    except Exception as e:
        print(f"❌ Ошибка API погоды: {e}")
        return jsonify({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        }), 500

@app.route('/api/weather/history')
def get_weather_history():
    """API для получения исторических данных погоды"""
    try:
        import sqlite3
        import os
        import json
        from datetime import datetime, timedelta
        
        db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        
        if not os.path.exists(db_path):
            return jsonify({'success': False, 'message': 'БД не найдена', 'data': []})
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем есть ли таблица
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weather_history'")
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': 'Таблица погоды не найдена', 'data': []})
        
        # Получаем данные за последние 7 дней
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        cursor.execute("""
            SELECT timestamp, temperature, weather_description, 
                   humidity, pressure_mmhg, wind_speed, city
            FROM weather_history 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (week_ago,))
        
        data = []
        for row in cursor.fetchall():
            timestamp, temp, desc, humidity, pressure, wind_speed, city = row
            
            # Преобразуем timestamp
            try:
                dt = datetime.fromisoformat(timestamp)
                date_str = dt.strftime('%Y-%m-%d')
                time_str = dt.strftime('%H:%M')
            except:
                date_str = timestamp[:10]
                time_str = timestamp[11:16]
            
            data.append({
                'date': date_str,
                'time': time_str,
                'temperature': temp,
                'weather': desc,
                'humidity': humidity,
                'pressure': pressure,
                'wind_speed': wind_speed,
                'city': city
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'last_update': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'data': []})

@app.route('/api/weather/test')
def test_weather_api():
    """Тестовый endpoint для проверки API"""
    try:
        from src.parsers.weather_parser import WeatherParser
        parser = WeatherParser()
        weather = parser.get_current_weather()
    except ImportError:
        weather = None
    
    if weather:
        return f"""
        <h2>Погода в {weather['city']}:</h2>
        <p>🌡️ Температура: {weather['temperature']}°C</p>
        <p>🤔 Ощущается как: {weather['feels_like']}°C</p>
        <p>☁️ Погода: {weather['weather_description']}</p>
        <p>💧 Влажность: {weather['humidity']}%</p>
        <p>📊 Давление: {weather['pressure_mmhg']} мм рт.ст. ({weather['pressure_hpa']} hPa)</p>
        <p>💨 Ветер: {weather['wind_speed']} м/с</p>
        """
    else:
        return "<h2>Не удалось получить погодные данные. Проверь API ключ.</h2>"

# Функции для парсинга
@app.route('/api/run-parser', methods=['POST'])
def run_parser_api():
    """API для запуска парсера"""
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

@app.route('/api/felix-pila/analysis')
def get_felix_pila_analysis():
    """API для анализа связи погоды и чисел"""
    # Анализ: какие числа выпадают при какой погоде
    pass

@app.route('/api/felix-pila/predict')
def get_felix_pila_predict():
    """API для прогноза на основе текущей погоды"""
    # Прогноз: какие числа вероятнее выпадут сегодня
    pass

def job_lottery_with_weather():
    """Собирает лотерею и сразу привязывает текущую погоду"""
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
    """Задача: только сбор погоды"""
    print(f"🌤️ Сбор погоды: {datetime.now().strftime('%H:%M:%S')}")
    try:
        from src.parsers.weather_parser import WeatherParser
        parser = WeatherParser()
        weather = parser.get_current_weather()
        
        if weather:
            # ВАЖНО: оба метода должны вызываться!
            parser.save_weather_to_db(weather)
            parser.update_latest_weather_to_lottery(weather)  # ← ЭТОГО НЕТ!
            print(f"✅ Погода сохранена: {weather['temperature']}°C")
    except Exception as e:
        print(f"❌ Ошибка сбора погоды: {e}")



# CLI КОМАНДЫ (оставляем эти)
@app.cli.command("create-db")
def create_db_command():
    """Создать таблицы в базе данных"""
    with app.app_context():
        db.create_all()
    print("✅ Таблицы созданы")

@app.cli.command("clear-db")
def clear_db_command():
    """Очистить базу данных"""
    with app.app_context():
        db.drop_all()
    print("🗑️ База данных очищена")

@app.cli.command("parse-lottery")
def parse_lottery_command():
    """Запустить парсер лотереи"""
    run_lottery_parser()

@app.cli.command("collect-data")
def collect_data_command():
    """Собрать данные лотереи и погоды сейчас"""
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
    """Инициализировать проект (первый запуск)"""
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

# ФОНГОВЫЙ ПЛАНИРОВЩИК (НОВАЯ ВЕРСИЯ)

def scheduler_loop():
    """Фоновый цикл планировщика"""
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
        """Задача: только сбор погоды"""
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
    lottery_times = ["10:00", "12:07", "13:52", "16:07", "16:22", "18:00", "20:07", "22:00"]
    for t in lottery_times:
        schedule.every().day.at(t).do(job_lottery_with_weather)
        print(f"  • Лотерея+погода в {t}")
    
    # Погода каждый час (кроме времени лотереи)
    for hour in range(8, 24):  # с 8:00 до 23:00
        time_str = f"{hour:02d}:30"  # в 30 минут каждого часа
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

# ОСНОВНОЙ БЛОК ЗАПУСКА

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