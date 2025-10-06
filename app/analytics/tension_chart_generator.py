"""
Модуль для построения графиков социальной напряженности с прогнозом
Аналогично примеру test_tension_forecast_20250508_174617.png
"""
import matplotlib
matplotlib.use('Agg')  # Для работы без GUI

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np
from typing import List, Tuple, Dict
import io
import base64

# Настройка шрифтов для русского языка
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False


class TensionChartGenerator:
    """Генератор графиков социальной напряженности"""
    
    def __init__(self):
        self.colors = {
            'historical': '#1f77b4',  # Синий
            'forecast': '#d62728',     # Красный
            'threshold': '#ff7f0e',    # Оранжевый
            'burst': '#2ca02c'         # Зеленый
        }
    
    def generate_tension_forecast_chart(
        self,
        historical_data: List[Tuple[datetime, float]],
        forecast_data: List[Tuple[datetime, float]],
        title: str = "Интегральный индекс социальной напряженности"
    ) -> str:
        """
        Генерирует график с историческими данными и прогнозом
        
        Args:
            historical_data: Список (дата, значение) для исторических данных
            forecast_data: Список (дата, значение) для прогноза
            title: Заголовок графика
            
        Returns:
            Base64-encoded изображение графика
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                       gridspec_kw={'height_ratios': [2, 1]})
        
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
        
        # === ВЕРХНИЙ ГРАФИК: Интегральный индекс ===
        
        if historical_data:
            hist_dates = [d[0] for d in historical_data]
            hist_values = [d[1] for d in historical_data]
            
            # Добавляем сглаживание для лучшей визуализации
            if len(hist_values) > 1:
                from scipy import interpolate
                import numpy as np
                
                # Создаем более плотную сетку для сглаживания
                hist_dates_numeric = [d.timestamp() for d in hist_dates]
                hist_dates_numeric = np.array(hist_dates_numeric)
                hist_values = np.array(hist_values)
                
                # Интерполяция для сглаживания
                if len(hist_dates_numeric) >= 3:
                    f = interpolate.interp1d(hist_dates_numeric, hist_values, 
                                           kind='cubic', bounds_error=False, fill_value='extrapolate')
                    dense_times = np.linspace(hist_dates_numeric.min(), hist_dates_numeric.max(), 100)
                    dense_values = f(dense_times)
                    dense_dates = [datetime.fromtimestamp(t) for t in dense_times]
                    
                    ax1.plot(dense_dates, dense_values, 
                            linewidth=3, alpha=0.7,
                            color=self.colors['historical'],
                            label='Исторические данные (сглаженные)',
                            zorder=2)
            
            # Основная линия с точками
            ax1.plot(hist_dates, hist_values, 
                    marker='o', linewidth=2, markersize=8,
                    color=self.colors['historical'],
                    label='Исторические данные',
                    zorder=3)
        
        if forecast_data:
            forecast_dates = [d[0] for d in forecast_data]
            forecast_values = [d[1] for d in forecast_data]
            
            ax1.plot(forecast_dates, forecast_values,
                    marker='o', linewidth=2, markersize=6,
                    color=self.colors['forecast'],
                    linestyle='--',
                    label='Прогноз',
                    zorder=3)
        
        # Линия границы между историей и прогнозом
        if historical_data and forecast_data:
            transition_date = forecast_data[0][0]
            ax1.axvline(x=transition_date, color='gray', 
                       linestyle='--', linewidth=1, alpha=0.5)
        
        ax1.set_xlabel('', fontsize=12)
        ax1.set_ylabel('Значение индекса', fontsize=12)
        ax1.legend(loc='upper right', fontsize=10)
        ax1.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax1.set_ylim(0, 1.0)
        
        # Форматирование дат на оси X
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # === НИЖНИЙ ГРАФИК: Индекс всплеска ===
        
        # Рассчитываем индекс всплеска (относительное изменение)
        burst_dates = []
        burst_values = []
        
        if historical_data and len(historical_data) > 1:
            for i in range(1, len(historical_data)):
                prev_val = historical_data[i-1][1]
                curr_val = historical_data[i][1]
                curr_date = historical_data[i][0]
                
                if prev_val > 0:
                    # Процентное изменение
                    change = ((curr_val - prev_val) / prev_val) * 100
                    burst_dates.append(curr_date)
                    burst_values.append(change)
        
        if burst_dates:
            # Цвета баров: зеленый для положительных, красный для отрицательных
            colors = [self.colors['burst'] if v >= 0 else self.colors['forecast'] 
                     for v in burst_values]
            
            ax2.bar(burst_dates, burst_values, 
                   color=colors, alpha=0.7, width=0.8)
            
            # Порог аномалии (30%)
            threshold = 30
            ax2.axhline(y=threshold, color=self.colors['threshold'], 
                       linestyle='--', linewidth=2, 
                       label=f'Порог аномалии ({threshold}%)')
            ax2.axhline(y=-threshold, color=self.colors['threshold'], 
                       linestyle='--', linewidth=2)
        
        ax2.set_xlabel('Дата', fontsize=12)
        ax2.set_ylabel('Изменение, %', fontsize=12)
        ax2.legend(loc='upper left', fontsize=10)
        ax2.grid(True, alpha=0.3, linestyle='-', linewidth=0.5, axis='y')
        
        # Форматирование дат
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Конвертируем в base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
    
    def generate_category_comparison_chart(
        self,
        category_data: Dict[str, List[Tuple[datetime, float]]],
        title: str = "Сравнение напряженности по категориям"
    ) -> str:
        """
        Генерирует график сравнения напряженности по категориям
        
        Args:
            category_data: Словарь {название_категории: [(дата, значение), ...]}
            title: Заголовок графика
            
        Returns:
            Base64-encoded изображение графика
        """
        fig, ax = plt.subplots(figsize=(14, 8))
        
        colors_list = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for idx, (category, data) in enumerate(category_data.items()):
            if data:
                dates = [d[0] for d in data]
                values = [d[1] for d in data]
                
                ax.plot(dates, values,
                       marker='o', linewidth=2, markersize=4,
                       color=colors_list[idx % len(colors_list)],
                       label=category,
                       alpha=0.8)
        
        ax.set_xlabel('Дата', fontsize=12)
        ax.set_ylabel('Индекс напряженности', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_ylim(0, 1.0)
        
        # Форматирование дат
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Конвертируем в base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
    
    def simple_forecast(
        self,
        historical_data: List[Tuple[datetime, float]],
        forecast_days: int = 5
    ) -> List[Tuple[datetime, float]]:
        """
        Простой прогноз на основе экспоненциального сглаживания
        
        Args:
            historical_data: Исторические данные
            forecast_days: Количество дней для прогноза
            
        Returns:
            Список прогнозных значений
        """
        if not historical_data or len(historical_data) < 3:
            return []
        
        # Берем последние значения
        recent_values = [d[1] for d in historical_data[-7:]]
        
        # Экспоненциальное сглаживание
        alpha = 0.3
        smoothed = [recent_values[0]]
        for i in range(1, len(recent_values)):
            smoothed.append(alpha * recent_values[i] + (1 - alpha) * smoothed[-1])
        
        # Тренд
        trend = (smoothed[-1] - smoothed[0]) / len(smoothed)
        
        # Генерируем прогноз
        last_date = historical_data[-1][0]
        last_value = smoothed[-1]
        
        forecast = []
        for i in range(1, forecast_days + 1):
            forecast_date = last_date + timedelta(days=i)
            # Добавляем некоторый спад
            forecast_value = max(0, last_value + trend * i - 0.05 * i)
            forecast.append((forecast_date, min(forecast_value, 1.0)))
        
        return forecast


# Глобальный экземпляр
chart_generator = TensionChartGenerator()


