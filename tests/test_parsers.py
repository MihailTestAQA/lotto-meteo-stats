# Парсер playwright лотереи 4x20 с lotonews.ru с правильными селекторами

import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

class LotteryParser:
    """Парсер лотерейных данных с lotonews.ru"""
    
    def __init__(self):
        self.lottery_url = "https://www.lotonews.ru/draws/archive/4x20"
    
    async def parse(self):
        """Основной метод для парсинга данных"""
        print("🔄 Запуск парсера лотереи 4x20...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) # Изменить для настройки и проверки парсера
            page = await browser.new_page()
            
            try:
                print(f"🌐 Загрузка: {self.lottery_url}")
                await page.goto(self.lottery_url, wait_until="networkidle", timeout=60000)
                
                # Ждем появления данных
                print("⏳ Ожидание загрузки данных...")
                await page.wait_for_selector('.content-main__circ-render-table-row', timeout=15000)
                
                # Извлекаем данные
                data = await self._extract_with_correct_selectors(page)
                
                if data:
                    print(f"✅ Найдено тиражей: {len(data)}")
                    self._save_to_json(data)
                    return data
                else:
                    print("❌ Не удалось собрать данные")
                    return None
                    
            except Exception as e:
                print(f"💥 Ошибка: {e}")
                return None
            finally:
                await browser.close()
    
    async def _extract_with_correct_selectors(self, page):
        """Извлекает данные используя правильные селекторы"""
        print("🎯 Извлечение данных...")
    
        try:
            data = await page.evaluate('''() => {
                const results = [];
            
                // 1. Находим ВСЕ строки с тиражами
                const rows = document.querySelectorAll('.content-main__circ-render-table-row');
            
                for (const row of rows) {
                    try {
                        // 2. НОМЕР ТИРАЖА ИЗ ССЫЛКИ
                        let drawNumber = '';
                    
                        const linkElement = row.querySelector('a[href*="/draws/archive/4x20/"]');
                        if (linkElement) {
                            const href = linkElement.getAttribute('href');
                            const match = href.match(/\\/draws\\/archive\\/4x20\\/(\\d+)/);
                            if (match) {
                                drawNumber = match[1];
                            }
                        }
                    
                        // 3. ДАТА
                        let drawDate = '';
                        const dateElement = row.querySelector('.content-main__circ-render-table-row-cell-title');
                        if (dateElement) {
                            const dateText = dateElement.textContent.trim();
                            const dateMatch = dateText.match(/(\\d{2}\\.\\d{2}\\.\\d{4}\\s+\\d{2}:\\d{2})/);
                            if (dateMatch) {
                                drawDate = dateMatch[1];
                            }
                        }
                    
                        // 4. ЧИСЛА - из контейнера
                        const numbersContainer = row.querySelector('.content-main__circ-render-table-row-cell-comb-container');
                        if (!numbersContainer) continue;
                    
                        const containerText = numbersContainer.textContent.trim();
                    
                        // Разделяем на Поле_1 и Поле_2
                        let поле_1 = [];
                        let поле_2 = [];
                    
                        if (containerText.includes('|')) {
                            const parts = containerText.split('|');
                        
                            // Первые 4 числа (до черты) -> Поле_1
                            const firstPart = parts[0].trim();
                            const firstMatches = firstPart.match(/\\b(\\d{1,2})\\b/g);
                            if (firstMatches) {
                                поле_1 = firstMatches.slice(0, 4).map(num => parseInt(num));
                            }
                        
                            // Дополнительные 4 числа (после черты) -> Поле_2
                            if (parts.length > 1) {
                                const secondPart = parts[1].trim();
                                const secondMatches = secondPart.match(/\\b(\\d{1,2})\\b/g);
                                if (secondMatches) {
                                    поле_2 = secondMatches.slice(0, 4).map(num => parseInt(num));
                                }
                            }
                        } else {
                            // Если нет черты, берем первые 8 чисел
                            const allMatches = containerText.match(/\\b(\\d{1,2})\\b/g);
                            if (allMatches) {
                                const allNumbers = allMatches.map(num => parseInt(num));
                                поле_1 = allNumbers.slice(0, 4);
                                поле_2 = allNumbers.slice(4, 8);
                            }
                        }
                    
                        // 5. СОХРАНЯЕМ РЕЗУЛЬТАТ
                        if (поле_1.length >= 4) {
                            const result = {
                                draw_number: drawNumber || 'Неизвестно',
                                draw_date: drawDate || '',
                                поле_1: поле_1,
                                поле_2: поле_2,
                                source: 'lotonews.ru',
                                extracted_at: new Date().toISOString()
                            };
                            
                            results.push(result);
                        }
                    
                    } catch (error) {
                        console.error('Ошибка обработки строки:', error);
                    }
                }
            
                return results;
            }''')
        
            # Убираем дубликаты
            if data:
                unique_data = []
                seen = set()
            
                for item in data:
                    key = f"{item['draw_number']}_{'_'.join(str(n) for n in item.get('поле_1', []))}"
                
                    if key not in seen:
                        seen.add(key)
                        unique_data.append(item)
            
                return unique_data
            
            return data
        
        except Exception as e:
            print(f"⚠️ Ошибка извлечения: {e}")
            return None
    
    def _save_to_json(self, data):
        """Сохраняет данные только в JSON"""
        if not data:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = f"data/lottery_{timestamp}.json"
        
        os.makedirs("data", exist_ok=True)
        
        # Сохраняем в JSON
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Данные сохранены в JSON: {json_file}")

async def run_parser():
    """Асинхронный запуск парсера"""
    parser = LotteryParser()
    return await parser.parse()

def run_parser_sync():
    """Синхронный запуск для интеграции с Flask"""
    return asyncio.run(run_parser())

if __name__ == "__main__":
    print("=" * 80)
    print("🎰 ПАРСЕР 4x20")
    print("=" * 80)
    
    data = asyncio.run(run_parser())
    
    if data:
        print(f"\n✅ УСПЕХ! Собрано {len(data)} тиражей")
        
        # Показываем первые тиражи
        print("\n📊 ПЕРВЫЕ 9 ТИРАЖЕЙ:")
        print("=" * 80)
        for i, item in enumerate(data[:9]):
            поле_1 = ' '.join(f"{n:>2}" for n in item.get('поле_1', []))
            поле_2 = ' '.join(f"{n:>2}" for n in item.get('поле_2', []))
            print(f"{i+1}. {item['draw_date']} | Тираж {item['draw_number']}")
            print(f"   Поле 1: {поле_1}")
            print(f"   Поле 2: {поле_2}")
            print("-" * 80)
    else:
        print("\n❌ Данные не собраны")