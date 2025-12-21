#  Главный файл приложения LottoMeteoStats

from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from config import Config
import datetime
import json

# Создаем экземпляр Flask приложения
app = Flask(__name__)
app.config.from_object(Config)

# Инициализируем базу данных
db = SQLAlchemy(app)

# Модель данных (пока заглушка, детали добавим позже)
class LotteryResult(db.Model):
    """Модель для хранения результатов лотереи"""
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
        'total_records': 0,  # Просто 0 пока не создана БД
        'features': [
            'Анализ лотерейных данных',
            'Интеграция с погодными API',
            'Статистика выпадения номеров',
            'Визуализация результатов'
        ]
    }
    return render_template('index.html', **stats)

@app.route('/api/health')
def health_check():
    """Проверка работоспособности API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'database': 'connected' if hasattr(db, 'engine') else 'not_configured'
    })

@app.route('/admin')
def admin_panel():
    """Панель администратора"""
    return render_template('admin.html')

# Команды для инициализации базы данных
@app.cli.command("init-db")
def init_db_command():
    """Инициализировать базу данных"""
    db.create_all()
    print("База данных инициализирована.")

@app.cli.command("clear-db")
def clear_db_command():
    """Очистить базу данных"""
    db.drop_all()
    print("База данных очищена.")

if __name__ == '__main__':
    # Запускаем сервер БЕЗ автоматического создания БД
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