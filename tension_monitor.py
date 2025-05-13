import os
import sys
import time
import logging
import schedule
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# Импортируем нашу LSTM модель
from tension_lstm_model import TensionLSTMModel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tension_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TensionMonitor:
    """Класс для мониторинга и автоматического обновления прогнозов
    индекса социальной напряженности"""
    
    def __init__(self, model=None, update_interval=24, 
                 reports_dir='reports', plots_dir='plots'):
        """Инициализация монитора
        
        Args:
            model (TensionLSTMModel): Модель LSTM для прогнозирования
            update_interval (int): Интервал обновления прогноза в часах
            reports_dir (str): Директория для сохранения отчетов
            plots_dir (str): Директория для сохранения графиков
        """
        self.model = model if model else TensionLSTMModel()
        self.update_interval = update_interval
        self.reports_dir = reports_dir
        self.plots_dir = plots_dir
        
        # Создаем директории для отчетов и графиков
        os.makedirs(reports_dir, exist_ok=True)
        os.makedirs(plots_dir, exist_ok=True)
        
        # Последний прогноз
        self.last_forecast = None
        self.last_update_time = None
    
    def update_forecast(self, train=False):
        """Обновление прогноза индекса напряженности
        
        Args:
            train (bool): Нужно ли переобучать модель
            
        Returns:
            bool: Успешно ли обновлен прогноз
        """
        try:
            logger.info("Начало обновления прогноза...")
            
            # Получаем новый прогноз
            if train:
                # Запускаем полный пайплайн с обучением
                forecast = self.model.run_full_pipeline(train=True, visualize=False)
            else:
                # Только прогноз без переобучения
                forecast = self.model.forecast_future()
            
            if forecast is None:
                logger.error("Не удалось получить прогноз")
                return False
            
            # Сохраняем прогноз
            self.last_forecast = forecast
            self.last_update_time = datetime.now()
            
            # Создаем и сохраняем визуализацию
            self._create_visualization()
            
            # Создаем и сохраняем отчет
            self._create_report()
            
            logger.info("Прогноз успешно обновлен")
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении прогноза: {e}")
            return False
    
    def _create_visualization(self):
        """Создание и сохранение визуализации прогноза"""
        try:
            # Получаем исторические данные
            df_history = self.model.fetch_data_from_clickhouse(days=14)  # Данные за 14 дней
            if df_history is None or len(df_history) < 7:  # Минимум 7 дней для визуализации
                logger.error("Недостаточно исторических данных для визуализации")
                return
            
            # Настройка стиля графика
            sns.set(style="whitegrid")
            plt.figure(figsize=(12, 6))
            
            # Построение графика исторических данных
            plt.plot(df_history['date'], df_history['tension_index'], 
                     marker='o', linestyle='-', color='blue', label='Исторические данные')
            
            # Построение графика прогноза
            plt.plot(self.last_forecast['date'], self.last_forecast['tension_index_forecast'], 
                     marker='o', linestyle='--', color='red', label='Прогноз')
            
            # Добавление вертикальной линии, разделяющей историю и прогноз
            plt.axvline(x=df_history['date'].iloc[-1], color='gray', linestyle='--', alpha=0.7)
            
            # Настройка графика
            plt.title('Индекс социальной напряженности: история и прогноз', fontsize=16)
            plt.xlabel('Дата', fontsize=12)
            plt.ylabel('Индекс напряженности', fontsize=12)
            plt.legend(fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Сохранение графика
            current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = os.path.join(self.plots_dir, f'tension_forecast_{current_date}.png')
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Визуализация сохранена в {save_path}")
        
        except Exception as e:
            logger.error(f"Ошибка при создании визуализации: {e}")
    
    def _create_report(self):
        """Создание и сохранение текстового отчета о прогнозе"""
        try:
            # Получаем исторические данные для сравнения
            df_history = self.model.fetch_data_from_clickhouse(days=7)  # Данные за последнюю неделю
            if df_history is None or len(df_history) < 3:  # Минимум 3 дня для сравнения
                logger.error("Недостаточно исторических данных для отчета")
                return
            
            # Вычисляем среднее значение индекса за последние 3 дня
            last_3days_avg = df_history['tension_index'].tail(3).mean()
            
            # Вычисляем среднее прогнозируемое значение
            forecast_avg = self.last_forecast['tension_index_forecast'].mean()
            
            # Вычисляем изменение в процентах
            change_percent = ((forecast_avg - last_3days_avg) / last_3days_avg) * 100
            
            # Определяем тренд
            if change_percent > 5:
                trend = "РОСТ"
                trend_description = "повышение социальной напряженности"
            elif change_percent < -5:
                trend = "СНИЖЕНИЕ"
                trend_description = "снижение социальной напряженности"
            else:
                trend = "СТАБИЛЬНОСТЬ"
                trend_description = "стабильный уровень социальной напряженности"
            
            # Формируем отчет
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            report = f"""ОТЧЕТ О ПРОГНОЗЕ ИНДЕКСА СОЦИАЛЬНОЙ НАПРЯЖЕННОСТИ
            
Дата создания: {current_date}

ТЕКУЩАЯ СИТУАЦИЯ:
- Средний индекс напряженности за последние 3 дня: {last_3days_avg:.2f}

ПРОГНОЗ:
- Прогнозируемый средний индекс на следующие {len(self.last_forecast)} дней: {forecast_avg:.2f}
- Изменение: {change_percent:.2f}%
- Тренд: {trend}

ИНТЕРПРЕТАЦИЯ:
Прогноз указывает на {trend_description} в ближайшие дни.

ДЕТАЛИ ПРОГНОЗА:
"""
            
            # Добавляем детали по дням
            for i, row in self.last_forecast.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d')
                report += f"- {date_str}: {row['tension_index_forecast']:.2f}\n"
            
            # Сохраняем отчет
            report_filename = f"tension_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_path = os.path.join(self.reports_dir, report_filename)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"Отчет сохранен в {report_path}")
        
        except Exception as e:
            logger.error(f"Ошибка при создании отчета: {e}")
    
    def start_monitoring(self):
        """Запуск мониторинга с регулярным обновлением прогноза"""
        logger.info(f"Запуск мониторинга с интервалом обновления {self.update_interval} часов")
        
        # Первоначальное обновление прогноза с обучением модели
        self.update_forecast(train=True)
        
        # Настройка расписания для регулярного обновления
        # Каждый день обновляем прогноз без переобучения
        schedule.every(self.update_interval).hours.do(self.update_forecast)
        
        # Раз в неделю переобучаем модель
        schedule.every().monday.at("03:00").do(lambda: self.update_forecast(train=True))
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Проверка расписания каждую минуту
        except KeyboardInterrupt:
            logger.info("Мониторинг остановлен пользователем")
        except Exception as e:
            logger.error(f"Ошибка в процессе мониторинга: {e}")

def main():
    """Основная функция для запуска мониторинга"""
    try:
        # Создание и запуск монитора
        monitor = TensionMonitor(update_interval=24)  # Обновление раз в сутки
        monitor.start_monitoring()
    except Exception as e:
        logger.error(f"Ошибка при запуске мониторинга: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()