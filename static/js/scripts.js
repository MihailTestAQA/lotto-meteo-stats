// Базовые скрипты для LottoMeteoStats

document.addEventListener('DOMContentLoaded', function() {
    console.log('LottoMeteoStats загружен!');
    
    // Проверка здоровья API
    checkApiHealth();
    
    // Инициализация текущей даты
    updateCurrentTime();
    
    // Инициализация tooltips
    initTooltips();
});

// Проверка статуса API
function checkApiHealth() {
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            console.log('Статус API:', data.status);
            updateStatusIndicator(data.status);
        })
        .catch(error => {
            console.error('Ошибка проверки API:', error);
            updateStatusIndicator('error');
        });
}

// Обновление индикатора статуса
function updateStatusIndicator(status) {
    const indicator = document.querySelector('.stat-status');
    if (indicator) {
        indicator.textContent = status === 'healthy' ? 'Активен' : 'Ошибка';
        indicator.className = 'stat-status ' + (status === 'healthy' ? 'active' : 'error');
    }
}

// Обновление текущего времени
function updateCurrentTime() {
    const timeElement = document.querySelector('.current-date');
    if (timeElement) {
        const now = new Date();
        const options = { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        timeElement.textContent = now.toLocaleDateString('ru-RU', options);
    }
}

// Инициализация подсказок
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const tooltipText = event.target.getAttribute('data-tooltip');
    if (tooltipText) {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.textContent = tooltipText;
        document.body.appendChild(tooltip);
        
        const rect = event.target.getBoundingClientRect();
        tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
        tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
        
        event.target._tooltip = tooltip;
    }
}

function hideTooltip(event) {
    if (event.target._tooltip) {
        event.target._tooltip.remove();
        delete event.target._tooltip;
    }
}

// Функция для обновления данных
function updateData() {
    const button = event?.target || document.querySelector('.btn-primary');
    if (button) {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Обновление...';
        button.disabled = true;
        
        // Имитация обновления данных
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
            alert('Данные обновлены!');
        }, 2000);
    }
}

// Экспорт функций для глобального использования
window.LottoMeteoStats = {
    updateData: updateData,
    checkApiHealth: checkApiHealth
};