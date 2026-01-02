import asyncio
import json
import sqlite3
from datetime import datetime
from playwright.async_api import async_playwright

class CorrectLotteryParser:
    def __init__(self):
        self.lottery_url = "https://www.lotonews.ru/draws/archive/4x20"
        self.db_path = r'D:\VS_code\lotto-meteo-stats\data\lottery.db'
        print(f"🎯 БД парсера: {self.db_path}")
    
    async def parse_and_save(self):
        """Правильный парсинг структурированной таблицы"""
        print("🔄 Запуск КОРРЕКТНОГО парсера...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(self.lottery_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)
                
                # Прокручиваем чтобы загрузить все
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                await page.evaluate('window.scrollTo(0, 0)')
                await asyncio.sleep(1)
                
                # ПАРСИМ ПРАВИЛЬНО - используем структуру таблицы
                data = await self._extract_correct_data(page)
                
                if data:
                    print(f"✅ Найдено тиражей: {len(data)}")
                    saved_count = self._save_to_db(data)
                    print(f"💾 Сохранено: {saved_count} записей")
                    return saved_count
                return 0
                    
            except Exception as e:
                print(f"💥 Ошибка: {e}")
                import traceback
                traceback.print_exc()
                return 0
            finally:
                await browser.close()
    
    async def _extract_correct_data(self, page):
        """Исправленный метод - парсим таблицу правильно"""
        try:
            data = await page.evaluate('''() => {
                const results = [];
                
                // Ищем ВСЮ таблицу результатов
                const table = document.querySelector('table');
                if (!table) {
                    console.log('Таблица не найдена, ищем div-таблицу');
                    // Ищем div-таблицу
                    const divTables = document.querySelectorAll('div[class*="table"], div[class*="archive"]');
                    if (divTables.length > 0) {
                        console.log('Найдена div-таблица');
                    }
                } else {
                    console.log('Найдена HTML таблица');
                }
                
                // ЛУЧШИЙ СПОСОБ: парсим по блокам тиражей
                // Ищем все элементы, содержащие тиражи
                const drawElements = document.querySelectorAll('[class*="draw"], [class*="tirazh"], tr, div[class*="row"]');
                console.log('Найдено элементов тиражей:', drawElements.length);
                
                for (let i = 0; i < drawElements.length; i++) {
                    const element = drawElements[i];
                    const elementText = element.textContent.trim();
                    
                    // Проверяем что это тираж (есть номер тиража 5 цифр)
                    const drawMatch = elementText.match(/\\b(\\d{5})\\b/);
                    if (!drawMatch) continue;
                    
                    const drawNumber = drawMatch[1];
                    
                    // Ищем дату и время (формат: "2.1.2026 22:00")
                    const dateTimeMatch = elementText.match(/(\\d{1,2}\\.\\d{1,2}\\.\\d{4})\\s+(\\d{1,2}:\\d{2})/);
                    if (!dateTimeMatch) continue;
                    
                    const drawDate = dateTimeMatch[1];
                    const drawTime = dateTimeMatch[2];
                    
                    console.log(`\\n🎰 Тираж ${drawNumber} от ${drawDate} ${drawTime}`);
                    
                    // ИЩЕМ ЧИСЛА ПРАВИЛЬНО - по структуре
                    // Способ 1: Ищем блоки с числами в текущем элементе
                    const numberBlocks = element.querySelectorAll('[class*="number"], [class*="ball"], [class*="comb"]');
                    let numbers = [];
                    
                    if (numberBlocks.length > 0) {
                        // Берем числа из специальных блоков
                        numberBlocks.forEach(block => {
                            const blockText = block.textContent.trim();
                            const blockNumbers = blockText.match(/\\b\\d{1,2}\\b/g);
                            if (blockNumbers) {
                                blockNumbers.forEach(num => {
                                    const n = parseInt(num, 10);
                                    if (n >= 1 && n <= 20 && !numbers.includes(n)) {
                                        numbers.push(n);
                                    }
                                });
                            }
                        });
                    }
                    
                    // Способ 2: Если не нашли, парсим структурированно
                    if (numbers.length < 8) {
                        // Ищем вертикальные списки чисел (как на сайте)
                        const allText = elementText;
                        
                        // Паттерн: 4 числа, потом |, потом 4 числа
                        const pattern1 = /(\\d{1,2})\\s+(\\d{1,2})\\s+(\\d{1,2})\\s+(\\d{1,2})\\s*\\|\\s*(\\d{1,2})\\s+(\\d{1,2})\\s+(\\d{1,2})\\s+(\\d{1,2})/;
                        const match1 = pattern1.exec(allText);
                        
                        if (match1) {
                            numbers = [];
                            for (let j = 1; j <= 8; j++) {
                                numbers.push(parseInt(match1[j], 10));
                            }
                        } else {
                            // Паттерн для чисел в столбик
                            const lines = allText.split(/\\n|\\r/);
                            const potentialNumbers = [];
                            
                            for (const line of lines) {
                                const trimmed = line.trim();
                                const num = parseInt(trimmed, 10);
                                if (!isNaN(num) && num >= 1 && num <= 20) {
                                    potentialNumbers.push(num);
                                }
                            }
                            
                            // Ищем последовательность из 8 чисел
                            for (let j = 0; j <= potentialNumbers.length - 8; j++) {
                                const slice = potentialNumbers.slice(j, j + 8);
                                // Проверяем что это действительно выигрышные числа (могут быть повторы в 4x20)
                                if (slice.every(n => n >= 1 && n <= 20)) {
                                    numbers = slice;
                                    break;
                                }
                            }
                        }
                    }
                    
                    // Разделяем на 2 поля по 4 числа
                    if (numbers.length >= 8) {
                        const field_1 = numbers.slice(0, 4);
                        const field_2 = numbers.slice(4, 8);
                        
                        console.log('Поле 1:', field_1);
                        console.log('Поле 2:', field_2);
                        
                        results.push({
                            draw_number: drawNumber,
                            draw_date: drawDate,
                            draw_time: drawTime,
                            numbers: numbers,
                            field_1: field_1,
                            field_2: field_2
                        });
                    } else {
                        console.log('Недостаточно чисел:', numbers);
                    }
                }
                
                console.log('Всего найдено тиражей:', results.length);
                return results;
            }''')
            
            # Обрабатываем полученные данные
            if data:
                print(f"\n📊 Получено {len(data)} записей")
                processed = []
                seen = set()
                
                for i, item in enumerate(data, 1):
                    draw_num = str(item['draw_number']).strip()
                    
                    if draw_num and draw_num not in seen:
                        seen.add(draw_num)
                        
                        # Проверяем что числа корректные
                        field_1 = item.get('field_1', [])
                        field_2 = item.get('field_2', [])
                        
                        if len(field_1) == 4 and len(field_2) == 4:
                            processed.append({
                                'draw_number': draw_num,
                                'date': item['draw_date'],
                                'time': item['draw_time'],
                                'field_1': json.dumps(field_1),
                                'field_2': json.dumps(field_2),
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            
                            print(f"✅ [{i}] Тираж {draw_num}: {item['draw_date']} {item['draw_time']}")
                            print(f"   Поле 1: {field_1}")
                            print(f"   Поле 2: {field_2}")
                        else:
                            print(f"⚠️ [{i}] Тираж {draw_num}: некорректные числа")
                
                print(f"\n🎯 Обработано {len(processed)} корректных записей")
                return processed
            
            return None
            
        except Exception as e:
            print(f"⚠️ Ошибка в _extract_correct_data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _save_to_db(self, data):
        """Сохраняет в БД"""
        if not data:
            print("⚠️ Нет данных для сохранения")
            return 0
        
        saved_count = 0
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаем таблицу если её нет
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS lottery_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draw_number TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                field_1 TEXT NOT NULL,
                field_2 TEXT NOT NULL,
                temperature REAL,
                weather TEXT,
                pressure REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            print(f"💾 Сохраняем {len(data)} записей в БД...")
            
            # Вставляем данные
            for i, item in enumerate(data, 1):
                try:
                    # ПРОВЕРЯЕМ что сохраняем правильные числа
                    field_1 = json.loads(item['field_1'])
                    field_2 = json.loads(item['field_2'])
                    
                    if len(field_1) != 4 or len(field_2) != 4:
                        print(f"⚠️ [{i}] Тираж {item['draw_number']}: пропускаем - некорректные данные")
                        continue
                    
                    cursor.execute('''
                    INSERT OR REPLACE INTO lottery_results 
                    (draw_number, date, time, field_1, field_2, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        item['draw_number'],
                        item['date'],
                        item['time'],
                        item['field_1'],
                        item['field_2'],
                        item['created_at']
                    ))
                    
                    saved_count += 1
                    if i <= 10:  # Показываем только первые 10
                        print(f"   [{i}] Сохранен тираж {item['draw_number']}")
                    
                except Exception as e:
                    print(f"⚠️ Ошибка сохранения тиража {item['draw_number']}: {e}")
            
            conn.commit()
            
            # Статистика
            cursor.execute("SELECT COUNT(*) FROM lottery_results")
            total_count = cursor.fetchone()[0]
            
            print(f"\n📊 СТАТИСТИКА БАЗЫ:")
            print(f"   • Добавлено/обновлено: {saved_count}")
            print(f"   • Всего записей: {total_count}")
            
            # Проверяем последние 3 записи
            cursor.execute("""
                SELECT draw_number, date, time, field_1, field_2 
                FROM lottery_results 
                ORDER BY draw_number DESC 
                LIMIT 3
            """)
            
            print(f"\n🔍 ПОСЛЕДНИЕ 3 ЗАПИСИ В БД:")
            for row in cursor.fetchall():
                draw_num, date, time, f1, f2 = row
                print(f"Тираж {draw_num} от {date} {time}:")
                print(f"   Поле 1: {json.loads(f1)}")
                print(f"   Поле 2: {json.loads(f2)}")
            
            cursor.close()
            conn.close()
            
            return saved_count
            
        except Exception as e:
            print(f"❌ Ошибка БД: {e}")
            import traceback
            traceback.print_exc()
            return 0

def run_parser_sync():
    """Синхронный запуск для Flask"""
    parser = CorrectLotteryParser()
    return asyncio.run(parser.parse_and_save())

if __name__ == "__main__":
    print("=" * 60)
    print("🎰 КОРРЕКТНЫЙ ПАРСЕР ЛОТЕРЕИ 4x20")
    print("=" * 60)
    result = asyncio.run(CorrectLotteryParser().parse_and_save())
    print(f"\n✨ Парсинг завершен. Сохранено записей: {result}")