import asyncio
import json
import os
import sqlite3
from datetime import datetime
from playwright.async_api import async_playwright

class LotteryParser:
    def __init__(self):
        self.lottery_url = "https://www.lotonews.ru/draws/archive/4x20"
        
        # Создаем путь к папке data относительно этого файла
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, 'data')
        
        # Создаем папку data если её нет
        os.makedirs(data_dir, exist_ok=True)
        
        self.db_path = os.path.join(data_dir, 'lottery.db')
    
    async def parse_and_save(self):
        """Парсит и сохраняет в БД совместимую с Flask"""
        print("🔄 Запуск парсера...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(self.lottery_url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)
                
                # Прокручиваем страницу чтобы загрузить все данные
                print("🔍 Прокручиваем страницу для загрузки всех данных...")
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await asyncio.sleep(2)
                await page.evaluate('window.scrollTo(0, 0)')
                await asyncio.sleep(1)
                
                # Сохраняем HTML для отладки
                html_content = await page.content()
                with open('debug_page.html', 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print("📄 HTML сохранен как debug_page.html")
                
                # Выводим количество найденных строк для отладки
                rows_count = await page.evaluate('''() => {
                    return document.querySelectorAll('.content-main__circ-render-table-row').length;
                }''')
                print(f"🔍 Найдено строк в таблице: {rows_count}")
                
                data = await self._extract_data(page)
                
                if data:
                    print(f"✅ Найдено тиражей: {len(data)}")
                    saved_count = self._save_to_flask_db(data)
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
    
    async def _extract_data(self, page):
        """Извлекает данные - УЛУЧШЕННАЯ ВЕРСИЯ"""
        try:
            data = await page.evaluate('''() => {
                const results = [];
                const rows = document.querySelectorAll('.content-main__circ-render-table-row');
                
                console.log('Всего строк найдено:', rows.length);
                
                for (let i = 0; i < rows.length; i++) {
                    const row = rows[i];
                    console.log(`\\n--- Обработка строки ${i+1} ---`);
                    
                    try {
                        // 1. НОМЕР ТИРАЖА - ИЩЕМ РАЗНЫМИ СПОСОБАМИ
                        let drawNumber = '';
                        
                        // Способ 1: Из ссылки
                        const links = row.querySelectorAll('a');
                        for (const link of links) {
                            const href = link.getAttribute('href') || '';
                            if (href.includes('/draws/archive/4x20/')) {
                                const match = href.match(/\\/draws\\/archive\\/4x20\\/(\\d+)/);
                                if (match) {
                                    drawNumber = match[1];
                                    break;
                                }
                            }
                        }
                        
                        // Способ 2: Из текста с номером
                        if (!drawNumber) {
                            const numberElements = row.querySelectorAll('[class*="number"], [class*="num"], .draw-number');
                            for (const elem of numberElements) {
                                const text = elem.textContent.trim();
                                const match = text.match(/№?\\s*(\\d+)/);
                                if (match) {
                                    drawNumber = match[1];
                                    break;
                                }
                            }
                        }
                        
                        // Способ 3: Из любого текста в строке
                        if (!drawNumber) {
                            const rowText = row.textContent;
                            const match = rowText.match(/\\b(\\d{4,5})\\b/);
                            if (match && match[1] > 1000) {
                                drawNumber = match[1];
                            }
                        }
                        
                        console.log('Номер тиража:', drawNumber);
                        
                        // 2. ДАТА И ВРЕМЯ
                        let drawDate = '';
                        let drawTime = '';
                        
                        // Получаем весь текст строки
                        const rowText = row.textContent;
                        
                        // Паттерны для поиска
                        const dateTimePattern = /(\\d{2}\\.\\d{2}\\.\\d{4})\\s+(\\d{2}:\\d{2})/;
                        const datePattern = /(\\d{2}\\.\\d{2}\\.\\d{4})/;
                        const timePattern = /(\\d{2}:\\d{2})/;
                        
                        // Пробуем найти дату и время вместе
                        const dateTimeMatch = rowText.match(dateTimePattern);
                        if (dateTimeMatch) {
                            drawDate = dateTimeMatch[1];
                            drawTime = dateTimeMatch[2];
                        } else {
                            // Ищем отдельно дату и время
                            const dateMatch = rowText.match(datePattern);
                            if (dateMatch) drawDate = dateMatch[1];
                            
                            const timeMatch = rowText.match(timePattern);
                            if (timeMatch) drawTime = timeMatch[1];
                        }
                        
                        console.log('Дата/время:', drawDate, drawTime);
                        
                        // 3. ЧИСЛА - ИЩЕМ ВСЕ ЧИСЛА В СТРОКЕ
                        const allNumbers = [];
                        
                        // Способ 1: Из специальных контейнеров
                        const numberContainers = row.querySelectorAll('.content-main__circ-render-table-row-cell-comb-container, .numbers, .balls');
                        for (const container of numberContainers) {
                            const text = container.textContent;
                            const matches = text.match(/\\b\\d{1,2}\\b/g);
                            if (matches) {
                                matches.forEach(match => {
                                    const num = parseInt(match, 10);
                                    if (!isNaN(num)) allNumbers.push(num);
                                });
                            }
                        }
                        
                        // Способ 2: Ищем все span/div с числами
                        const numberElements = row.querySelectorAll('span, div');
                        for (const elem of numberElements) {
                            const text = elem.textContent.trim();
                            const num = parseInt(text, 10);
                            if (!isNaN(num) && num >= 1 && num <= 20) {
                                allNumbers.push(num);
                            }
                        }
                        
                        // Способ 3: Ищем числа во всем тексте строки
                        const allMatches = rowText.match(/\\b\\d{1,2}\\b/g);
                        if (allMatches) {
                            allMatches.forEach(match => {
                                const num = parseInt(match, 10);
                                if (!isNaN(num) && num >= 1 && num <= 20 && !allNumbers.includes(num)) {
                                    allNumbers.push(num);
                                }
                            });
                        }
                        
                        // Убираем дубликаты и сортируем
                        const uniqueNumbers = [...new Set(allNumbers)].sort((a, b) => a - b);
                        
                        console.log('Все найденные числа:', uniqueNumbers);
                        
                        // Разделяем на два поля (по 4 числа в каждом)
                        if (uniqueNumbers.length >= 8) {
                            const field_1 = uniqueNumbers.slice(0, 4);
                            const field_2 = uniqueNumbers.slice(4, 8);
                            
                            console.log('Поле 1:', field_1);
                            console.log('Поле 2:', field_2);
                            
                            results.push({
                                draw_number: drawNumber,
                                draw_date: drawDate,
                                draw_time: drawTime || '15:00',
                                numbers: uniqueNumbers,
                                field_1: field_1,
                                field_2: field_2
                            });
                        } else {
                            console.log('Недостаточно чисел:', uniqueNumbers.length);
                        }
                        
                    } catch (error) {
                        console.error('Ошибка в обработке строки:', error);
                    }
                }
                
                console.log('Всего обработано записей:', results.length);
                return results;
            }''')
        
            # Обрабатываем данные
            if data:
                print(f"\n📊 Извлечено {len(data)} записей")
                processed = []
                seen = set()
            
                for i, item in enumerate(data, 1):
                    draw_num = str(item['draw_number']).strip()
                    
                    if draw_num and draw_num not in seen:
                        seen.add(draw_num)
                        
                        # Обрабатываем дату и время
                        date_str = item['draw_date']
                        time_str = item['draw_time'] if item['draw_time'] else '15:00'
                        
                        # Проверяем числа
                        if len(item.get('field_1', [])) == 4 and len(item.get('field_2', [])) == 4:
                            processed.append({
                                'draw_number': draw_num,
                                'date': date_str,
                                'time': time_str,
                                'numbers': json.dumps(item.get('numbers', [])),
                                'field_1': json.dumps(item.get('field_1', [])),
                                'field_2': json.dumps(item.get('field_2', [])),
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            
                            print(f"✅ [{i}] Тираж {draw_num}: {date_str} {time_str}")
                            print(f"   Поле 1: {item.get('field_1', [])}")
                            print(f"   Поле 2: {item.get('field_2', [])}")
                        else:
                            print(f"⚠️ [{i}] Тираж {draw_num}: некорректные числа")
            
                print(f"\n🎯 Обработано {len(processed)} корректных записей")
                return processed
        
            return None
        
        except Exception as e:
            print(f"⚠️ Ошибка в _extract_data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _save_to_flask_db(self, data):
        """Сохраняет в БД совместимую с Flask моделью"""
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
            
            # Создаем индекс если его нет
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_draw_number ON lottery_results(draw_number)
            ''')
            
            print(f"💾 Сохраняем {len(data)} записей в БД...")
            
            # Вставляем данные
            for i, item in enumerate(data, 1):
                try:
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
                    print(f"   [{i}] Сохранен тираж {item['draw_number']}")
                    
                except Exception as e:
                    print(f"⚠️ Ошибка сохранения тиража {item['draw_number']}: {e}")
            
            conn.commit()
            
            # Показываем статистику
            cursor.execute("SELECT COUNT(*) FROM lottery_results")
            total_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT MAX(created_at) FROM lottery_results")
            last_update = cursor.fetchone()[0]
            
            print(f"\n📊 СТАТИСТИКА БАЗЫ ДАННЫХ:")
            print(f"   • Добавлено новых: {saved_count}")
            print(f"   • Всего записей: {total_count}")
            print(f"   • Последнее обновление: {last_update}")
            
            cursor.close()
            conn.close()
            
            return saved_count
            
        except Exception as e:
            print(f"❌ Ошибка при работе с БД: {e}")
            import traceback
            traceback.print_exc()
            return 0

def run_parser_sync():
    """Синхронный запуск для Flask"""
    parser = LotteryParser()
    return asyncio.run(parser.parse_and_save())

if __name__ == "__main__":
    print("=" * 60)
    print("🎰 ПАРСЕР ЛОТЕРЕИ 4x20 - ПОЛНАЯ ВЕРСИЯ")
    print("=" * 60)
    result = asyncio.run(LotteryParser().parse_and_save())
    print(f"\n✨ Парсинг завершен. Сохранено записей: {result}")