# Создаем Главный файл приложения LottoMeteoStats

from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from src.parsers.weather_parser import WeatherParser
from config import Config
import datetime

# Создаем экземпляр Flask приложения
app = Flask(__name__)
app.config.from_object(Config)

# Инициализируем базу данных
db = SQLAlchemy(app)

# Модель данных
class LotteryResult(db.Model):
    """Модель для хранения результатов лотереи"""
    __tablename__ = 'lottery_results'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    numbers = db.Column(db.String(100), nullable=False)
    temperature = db.Column(db.Float)
    weather = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Маршруты приложения
@app.route('/')
def index():
    """Главная страница"""
    stats = {
        'project_name': 'LottoMeteoStats',
        'current_date': datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),
        'version': '1.0.0',
        'total_records': 0,
        'features': [
            'Анализ лотерейных данных',
            'Интеграция с погодными API',
            'Статистика выпадения номеров',
            'Визуализация результатов'
        ]
    }
    return render_template('index.html', **stats)

@app.route('/weather')
def weather_page():
    """Страница с погодой"""
    return render_template('weather.html')

@app.route('/api/weather/current')
def get_current_weather():
    """Получить текущую погоду"""
    try:
        parser = WeatherParser()
        weather = parser.get_current_weather()
        
        if weather:
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
        return jsonify({
            'success': False,
            'message': f'Ошибка: {str(e)}'
        }), 500

@app.route('/api/weather/test')
def test_weather_api():
    """Тестовый endpoint для проверки API"""
    parser = WeatherParser()
    weather = parser.get_current_weather()
    
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

@app.route('/admin')
def admin_panel():
    """Панель администратора"""
    return "Панель управления (в разработке)"

if __name__ == '__main__':
    print("=" * 50)
    print("🎰 LottoMeteoStats запущен!")
    print(f"📅 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("🌐 Откройте в браузере: http://localhost:5000")
    print("=" * 50)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config['DEBUG']
    )