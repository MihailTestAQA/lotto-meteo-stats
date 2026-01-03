"""
Планировщик для автоматического сбора данных
"""

import schedule
import time
from datetime import datetime
from src.parsers.lottery_parser import run_parser_sync
from src.parsers.weather_parser import WeatherParser

def job_lottery():
    """Задача для сбора лотерейных данных"""
    print(f"\n{'='*50}")
    print(f"⏰ Автосбор лотереи: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    try:
        data = run_parser_sync()  # Используем РАБОЧИЙ парсер
        
        if data:
            print(f"✅ Лотерея: собрано {len(data)} тиражей")
            # Показываем последний тираж
            last = data[0]
            if isinstance(last['draw_date'], datetime):
                date_str = last['draw_date'].strftime('%d.%m.%Y %H:%M')
            else:
                date_str = str(last['draw_date'])
            
            print(f"📅 Последний тираж: №{last['draw_number']} от {date_str}")
            print(f"🎯 Номера: {last['numbers']}")
            return True
        else:
            print("❌ Лотерея: не удалось собрать данные")
            return False
            
    except Exception as e:
        print(f"💥 Ошибка сбора лотереи: {e}")
        return False

def job_weather():
    """Задача для сбора погодных данных с сохранением в БД"""
    print(f"\n🌤️ Сбор погоды: {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        parser = WeatherParser()
        weather = parser.get_current_weather()
        
        if weather:
            # 1. Сохраняем в историю погоды
            parser.save_weather_to_db(weather)
            
            # 2. Обновляем последние тиражи
            parser.update_latest_weather_to_lottery(weather)
            
            print(f"✅ Погода: {weather['temperature']}°C в {weather['city']}")
            print(f"📊 Давление: {weather['pressure_mmhg']} мм рт.ст.")
            print(f"💧 Влажность: {weather.get('humidity', 'N/A')}%")
            return True
        else:
            print("❌ Погода: не удалось собрать данные")
            return False
            
    except Exception as e:
        print(f"💥 Ошибка сбора погоды: {e}")
        return False

def job_lottery_with_weather():
    """Сбор и лотереи и погоды одновременно"""
    print(f"\n{'='*60}")
    print(f"🎰🌤️ Сбор лотереи и погоды: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Сначала погода
    weather_success = job_weather()
    
    # Потом лотерея
    lottery_success = job_lottery()
    
    return weather_success and lottery_success

def run_scheduler():
    """Запускает планировщик задач"""
    print("=" * 60)
    print("🚀 АВТОМАТИЧЕСКИЙ СБОР ДАННЫХ LottoMeteoStats")
    print("=" * 60)
    print("📅 Расписание:")
    print("  • Лотерея+Погода: 10:00, 12:00, 13:00, 16:00, 16:22, 18:00, 20:00, 22:00")
    print("  • Только погода: каждые 30 минут с 8:00 до 23:00")
    print("🛑 Для остановки нажмите Ctrl+C\n")
    
    # Исправленные времена лотереи (без минутного смещения)
    lottery_times = ["10:00", "12:00", "13:00", "16:00", "16:22", "18:00", "20:00", "22:00"]
    
    # Основные задачи: лотерея + погода
    for t in lottery_times:
        schedule.every().day.at(t).do(job_lottery_with_weather)
        print(f"  ⏰ Настроено: лотерея+погода в {t}")
    
    # Только погода каждые 30 минут
    # Создаем список всех времен для избежания дублирования
    all_scheduled_times = set(lottery_times)
    
    for hour in range(8, 24):  # с 8:00 до 23:00
        for minute in [0, 30]:  # каждый час и каждые полчаса
            time_str = f"{hour:02d}:{minute:02d}"
            if time_str not in all_scheduled_times:
                schedule.every().day.at(time_str).do(job_weather)
                all_scheduled_times.add(time_str)
                print(f"  🌤️ Настроено: только погода в {time_str}")
    
    print(f"\n✅ Всего задач: {len(schedule.jobs)}")
    print("▶️ Планировщик настроен. Ожидание задач...\n")
    
    # ПЕРВЫЙ ЗАПУСК ПРЯМО СЕЙЧАС
    print("🔧 Первый запуск погоды...")
    job_weather()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту

if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\n👋 Планировщик остановлен пользователем")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()