"""
Менеджер для сохранения данных в базу
"""

import json
import os
from datetime import datetime
from .. import db  # Импортируем из __init__.py
from ..models import LotteryResult, WeatherData  # Будут созданы позже

class DataManager:
    """Управление сохранением данных"""
    
    @staticmethod
    def save_lottery_data(data):
        """Сохраняет лотерейные данные в БД"""
        if not data:
            return 0
        
        saved_count = 0
        for item in data:
            # Проверяем, нет ли уже такого тиража
            existing = LotteryResult.query.filter_by(
                draw_number=item.get('draw_number')
            ).first()
            
            if not existing:
                lottery = LotteryResult(
                    draw_number=item.get('draw_number'),
                    date=item.get('draw_date'),
                    numbers=json.dumps(item.get('numbers', [])),
                    temperature=None,  # Будет добавлено позже из погоды
                    weather=None
                )
                db.session.add(lottery)
                saved_count += 1
        
        if saved_count > 0:
            db.session.commit()
        
        return saved_count
    
    @staticmethod
    def get_latest_data(count=50):
        """Получает последние данные из БД"""
        results = LotteryResult.query.order_by(
            LotteryResult.date.desc()
        ).limit(count).all()
        
        data = []
        for r in results:
            data.append({
                'draw_number': r.draw_number,
                'date': r.date.strftime('%d.%m.%Y') if r.date else '',
                'numbers': json.loads(r.numbers) if r.numbers else [],
                'temperature': r.temperature,
                'weather': r.weather
            })
        
        return data