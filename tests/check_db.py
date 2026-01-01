# check_lottery_db.py - проверяем БД от парсера
import sqlite3
import os
import json
from collections import Counter

print("📊 ПРОВЕРКА БАЗЫ ДАННЫХ ОТ ПАРСЕРА")
print("=" * 50)

# Путь к БД
script_dir = os.path.dirname(os.path.abspath(__file__))  # tests
project_root = os.path.dirname(script_dir)  # lotto-meteo-stats
db_path = os.path.join(project_root, 'data', 'lottery.db')

print(f"🔍 Ищем БД по пути: {db_path}")

if os.path.exists(db_path):
    print(f"✅ Файл БД найден! Размер: {os.path.getsize(db_path):,} байт")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        print(f"\n📋 Таблицы в БД: {[t[0] for t in tables] if tables else 'Нет таблиц'}")
        
        if ('lottery_results',) in tables:
            print("\n🎰 СТРУКТУРА lottery_results:")
            print("-" * 50)
            
            # Получаем информацию о колонках
            cursor.execute("PRAGMA table_info(lottery_results)")
            columns = cursor.fetchall()
            
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                nullable = 'NULL' if col[3] else 'NOT NULL'
                is_pk = 'PK' if col[5] else ''
                print(f"{col_name:15} {col_type:15} {nullable:10} {is_pk}")
            
            # Количество записей
            cursor.execute("SELECT COUNT(*) FROM lottery_results")
            count = cursor.fetchone()[0]
            print(f"\n📊 Всего записей в таблице: {count:,}")
            
            # Последние тиражи по дате
            if count > 0:
                print("\n📋 ПОСЛЕДНИЕ 5 ТИРАЖЕЙ:")
                cursor.execute("SELECT * FROM lottery_results ORDER BY date DESC LIMIT 5")
    
                field_names = ["ID", "Тираж", "Дата", "Числа", "Температура", "Погода", "Добавлен"]
    
                for i, row in enumerate(cursor.fetchall(), 1):
                    print(f"\n{i}. ", end="")
                    for j in range(min(len(row), 7)):
                        if j == 3 and row[j]:  # numbers
                            try:
                                nums = json.loads(row[j])[:8]
                                if len(nums) == 8:
                                    print(f"{field_names[j]}: {nums[:4]}/{nums[4:8]} ", end="")
                            except:
                                print(f"{field_names[j]}: {row[j][:20]} ", end="")
                        elif j == 4 or j == 5:  # temperature, weather
                            if row[j]:
                                print(f"{field_names[j]}: {row[j]} ", end="")
                        elif j == 6:  # created_at
                            print(f"{field_names[j]}: {row[j]} ", end="")
                    
                # Статистика по числам
                print("\n📈 СТАТИСТИКА ПО ЧИСЛАМ:")
                print("-" * 50)
                
                # Получаем все числа
                all_numbers = []
                cursor.execute("SELECT numbers FROM lottery_results")
                all_records = cursor.fetchall()
                
                for (nums_json,) in all_records:
                    if nums_json:
                        try:
                            numbers = json.loads(nums_json)
                            all_numbers.extend(numbers)
                        except:
                            pass
                
                if all_numbers:
                    counter = Counter(all_numbers)
                    
                    print("Частота чисел (топ-10):")
                    sorted_numbers = sorted(counter.items(), key=lambda x: x[1], reverse=True)
                    for num, freq in sorted_numbers[:10]:
                        percentage = (freq / len(all_numbers)) * 100
                        print(f"  Число {num:2}: {freq:3} раз ({percentage:.1f}%)")
                    
                    print(f"\n📊 Всего чисел проанализировано: {len(all_numbers):,}")
                    
                # Проверка целостности данных
                print("\n🔍 ПРОВЕРКА ЦЕЛОСТНОСТИ ДАННЫХ:")
                print("-" * 50)

                try:
                    # Проверяем дубликаты тиражей
                    cursor.execute("""
                        SELECT draw_number, COUNT(*) as cnt 
                        FROM lottery_results 
                        GROUP BY draw_number 
                        HAVING cnt > 1
                    """)
                    duplicates = cursor.fetchall()
                    
                    if duplicates:
                        print(f"⚠️  Найдены дубликаты тиражей: {len(duplicates)} шт.")
                        for dup in duplicates[:5]:
                            print(f"  Тираж {dup[0]}: {dup[1]} записей")
                    else:
                        print("✅ Дубликатов тиражей не найдено")
                        
                except Exception as e:
                    print(f"⚠️  Ошибка проверки дубликатов: {e}")

                try:
                    # Проверяем пустые поля
                    cursor.execute("SELECT COUNT(*) FROM lottery_results WHERE draw_number IS NULL OR date IS NULL")
                    null_fields = cursor.fetchone()[0]
                    if null_fields > 0:
                        print(f"⚠️  Найдено записей с пустыми полями: {null_fields}")
                    else:
                        print("✅ Все записи имеют основные данные")
                        
                except Exception as e:
                    print(f"⚠️  Ошибка проверки пустых полей: {e}")

                try:
                    # Проверяем формат чисел
                    cursor.execute("SELECT COUNT(*) FROM lottery_results WHERE numbers IS NOT NULL")
                    has_numbers = cursor.fetchone()[0]
                    
                    valid_json = 0
                    cursor.execute("SELECT numbers FROM lottery_results WHERE numbers IS NOT NULL")
                    for (nums,) in cursor.fetchall():
                        try:
                            json.loads(nums)
                            valid_json += 1
                        except:
                            pass
                    
                    if has_numbers > 0:
                        print(f"✅ Числа в JSON формате: {valid_json}/{has_numbers} записей")
                        
                except Exception as e:
                    print(f"⚠️  Ошибка проверки формата чисел: {e}")
        
        else:
            print("\n❌ Таблица lottery_results не найдена в lottery.db!")
            
            if tables:
                print("Существующие таблицы:")
                for table in tables:
                    print(f"  - {table[0]}")
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    print(f"    Записей: {count}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при работе с БД: {e}")
        
else:
    print(f"❌ Файл lottery.db не найден!")
    
    print(f"\n📁 Содержимое папки {basedir}:")
    for f in os.listdir(basedir):
        full_path = os.path.join(basedir, f)
        if os.path.isfile(full_path):
            size = os.path.getsize(full_path)
            ext = os.path.splitext(f)[1]
            if ext in ['.db', '.sqlite', '.sqlite3']:
                print(f"  📂 БД: {f} ({size:,} байт)")
    
    print("\n🔍 Поиск SQLite файлов...")
    sqlite_files = [f for f in os.listdir(basedir) 
                   if f.endswith(('.db', '.sqlite', '.sqlite3'))]
    
    if sqlite_files:
        print(f"Найдены SQLite файлы: {', '.join(sqlite_files)}")
        print("Запустите парсер, чтобы создать lottery.db с данными!")

print("\n" + "=" * 50)
print("💡 Для создания БД запустите: python lottery_parser.py")