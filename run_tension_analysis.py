import argparse
import logging
import os
import sys
from datetime import datetime

# Импортируем нашу LSTM модель и монитор
from tension_lstm_model import TensionLSTMModel
from tension_monitor import TensionMonitor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tension_analysis.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='Анализ и прогнозирование индекса социальной напряженности')
    
    parser.add_argument('--train', action='store_true', help='Обучить модель перед прогнозированием')
    parser.add_argument('--monitor', action='store_true', help='Запустить систему мониторинга')
    parser.add_argument('--visualize', action='store_true', help='Создать визуализацию прогноза')
    parser.add_argument('--days', type=int, default=3, help='Количество дней для прогноза (по умолчанию 3)')
    parser.add_argument('--lookback', type=int, default=7, help='Количество дней в истории для предсказания (по умолчанию 7)')
    
    return parser.parse_args()

def run_single_forecast(args):
    """Запуск однократного прогнозирования"""
    try:
        # Создаем модель с указанными параметрами
        model = TensionLSTMModel(lookback=args.lookback, forecast_days=args.days)
        
        if args.train:
            # Запускаем полный пайплайн с обучением
            logger.info("Запуск обучения модели и создания прогноза...")
            forecast = model.run_full_pipeline(train=True, visualize=args.visualize)
        else:
            # Только прогноз без переобучения
            logger.info("Создание прогноза без переобучения модели...")
            forecast = model.forecast_future()
            
            # Если нужна визуализация, создаем ее отдельно
            if args.visualize:
                logger.info("Создание визуализации...")
                os.makedirs('plots', exist_ok=True)
                current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
                save_path = f'plots/tension_forecast_{current_date}.png'
                model.visualize_forecast(save_path=save_path)
        
        if forecast is not None:
            print("\nПрогноз индекса социальной напряженности:")
            for i, row in forecast.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d')
                print(f"- {date_str}: {row['tension_index_forecast']:.2f}")
            print("\nПрогноз успешно создан!")
            
            # Анализ тренда
            if len(forecast) > 1:
                first_value = forecast['tension_index_forecast'].iloc[0]
                last_value = forecast['tension_index_forecast'].iloc[-1]
                change = ((last_value - first_value) / first_value) * 100
                
                if change > 5:
                    trend = "РОСТ"
                    print("\nТренд: РОСТ социальной напряженности")
                elif change < -5:
                    trend = "СНИЖЕНИЕ"
                    print("\nТренд: СНИЖЕНИЕ социальной напряженности")
                else:
                    trend = "СТАБИЛЬНОСТЬ"
                    print("\nТренд: СТАБИЛЬНЫЙ уровень социальной напряженности")
        else:
            print("\nНе удалось создать прогноз. Проверьте логи для получения дополнительной информации.")
    
    except Exception as e:
        logger.error(f"Ошибка при выполнении прогноза: {e}")
        print(f"\nПроизошла ошибка: {e}")

def main():
    """Основная функция"""
    args = parse_arguments()
    
    try:
        if args.monitor:
            # Запуск системы мониторинга
            print("Запуск системы мониторинга индекса социальной напряженности...")
            monitor = TensionMonitor(update_interval=24)  # Обновление раз в сутки
            monitor.start_monitoring()
        else:
            # Однократное прогнозирование
            run_single_forecast(args)
    
    except KeyboardInterrupt:
        print("\nПрограмма остановлена пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        print(f"\nКритическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("="*80)
    print("АНАЛИЗ И ПРОГНОЗИРОВАНИЕ ИНДЕКСА СОЦИАЛЬНОЙ НАПРЯЖЕННОСТИ")
    print("="*80)
    main()