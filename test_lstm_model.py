import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import logging
from datetime import datetime, timedelta

# Импортируем нашу LSTM модель
from tension_lstm_model import TensionLSTMModel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_lstm.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MockClickHouseClient:
    """Мок-класс для имитации работы с ClickHouse"""
    
    def __init__(self):
        """Инициализация мок-клиента"""
        pass
    
    def execute(self, query, data=None):
        """Имитация выполнения запроса к ClickHouse"""
        if "SELECT 1" in query:
            return [[1]]
        elif "telegram_daily" in query and "israil_daily" in query:
            # Генерируем синтетические данные для тестирования
            return self._generate_synthetic_data(60)  # 60 дней данных
        else:
            return []
    
    def _generate_synthetic_data(self, days):
        """Генерация синтетических данных для тестирования
        
        Args:
            days (int): Количество дней для генерации
            
        Returns:
            list: Список кортежей с данными
        """
        np.random.seed(42)  # Для воспроизводимости результатов
        
        # Базовые значения
        base_telegram_count = 50
        base_telegram_length = 500
        base_israil_count = 30
        
        # Тренд (линейный рост)
        trend_telegram = np.linspace(0, 20, days)
        trend_israil = np.linspace(0, 10, days)
        
        # Сезонность (недельный цикл)
        seasonality_telegram = 10 * np.sin(np.linspace(0, 2 * np.pi * (days / 7), days))
        seasonality_israil = 5 * np.sin(np.linspace(0, 2 * np.pi * (days / 7), days))
        
        # Случайный шум
        noise_telegram_count = np.random.normal(0, 5, days)
        noise_telegram_length = np.random.normal(0, 50, days)
        noise_israil_count = np.random.normal(0, 3, days)
        
        # Генерация данных
        data = []
        start_date = datetime.now() - timedelta(days=days)
        
        # Определяем дату, соответствующую 9 мая в нашем диапазоне
        may_9_index = None
        for i in range(days):
            date = start_date + timedelta(days=i)
            if date.month == 5 and date.day == 9:
                may_9_index = i
                break
        
        # Если 9 мая не попадает в наш диапазон, создаем искусственную дату
        if may_9_index is None:
            may_9_index = days - 7  # Размещаем "9 мая" за неделю до конца периода
        
        for i in range(days):
            date = start_date + timedelta(days=i)
            
            # Создаем средний уровень напряженности до 9 мая
            spike = 0
            
            # Большой всплеск в день 9 мая и несколько дней после
            if i == may_9_index:
                spike = 100  # Очень большой всплеск в сам день 9 мая
            elif i == may_9_index - 1:
                spike = 40   # Повышение накануне
            elif may_9_index < i <= may_9_index + 3:
                spike = 70 - (i - may_9_index) * 15  # Постепенное снижение после пика
            
            # Добавляем небольшой всплеск в середине периода (если он не пересекается с 9 мая)
            if days // 3 <= i <= days // 3 + 5 and abs(i - may_9_index) > 7:
                spike += 20
            
            telegram_count = max(1, int(base_telegram_count + trend_telegram[i] + seasonality_telegram[i] + noise_telegram_count[i] + spike))
            telegram_length = max(100, int(base_telegram_length + noise_telegram_length[i] + spike * 2))
            israil_count = max(1, int(base_israil_count + trend_israil[i] + seasonality_israil[i] + noise_israil_count[i] + spike * 0.7))
            
            data.append((date.date(), telegram_count, telegram_length, israil_count))
        
        return data

def patch_clickhouse_connection(model):
    """Заменяет метод подключения к ClickHouse на мок-версию"""
    model.connect_to_clickhouse = lambda *args, **kwargs: MockClickHouseClient()

def test_lstm_model():
    """Тестирование LSTM модели на синтетических данных"""
    print("\nЗапуск тестирования LSTM модели на синтетических данных...")
    
    try:
        # Создаем модель
        model = TensionLSTMModel(lookback=7, forecast_days=5)
        
        # Заменяем подключение к ClickHouse на мок-версию
        patch_clickhouse_connection(model)
        
        # Запускаем полный пайплайн
        print("\nОбучение модели на синтетических данных...")
        forecast = model.run_full_pipeline(train=True, visualize=False)
        
        if forecast is not None:
            print("\nМодель успешно обучена на синтетических данных!")
            print("\nПрогноз индекса социальной напряженности:")
            for i, row in forecast.iterrows():
                date_str = row['date'].strftime('%Y-%m-%d')
                print(f"- {date_str}: {row['tension_index_forecast']:.2f}")
            
            # Создаем визуализацию
            print("\nСоздание визуализации...")
            os.makedirs('plots', exist_ok=True)
            current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = f'plots/test_tension_forecast_{current_date}.png'
            
            # Получаем исторические данные
            df_history = pd.DataFrame(
                model.connect_to_clickhouse()._generate_synthetic_data(14),
                columns=['date', 'telegram_count', 'telegram_avg_length', 'israil_count']
            )
            
            # Вычисляем интегральный индекс социальной напряженности
            # I_t = α∙Neg_t + β∙Emot_t + γ∙Eng_t, где α+β+γ=1
            
            # Нормализуем компоненты
            df_history['neg_component'] = df_history['telegram_count'] / df_history['telegram_count'].max() if df_history['telegram_count'].max() > 0 else 0
            df_history['emot_component'] = df_history['telegram_avg_length'] / df_history['telegram_avg_length'].max() if df_history['telegram_avg_length'].max() > 0 else 0
            df_history['eng_component'] = df_history['israil_count'] / df_history['israil_count'].max() if df_history['israil_count'].max() > 0 else 0
            
            # Веса компонентов (α, β, γ)
            alpha, beta, gamma = 0.5, 0.3, 0.2  # α+β+γ=1
            
            # Расчет интегрального индекса напряженности
            df_history['tension_index'] = alpha * df_history['neg_component'] + beta * df_history['emot_component'] + gamma * df_history['eng_component']
            
            # Расчет индекса всплеска S_t = (I_t - I_(t-1)) / I_(t-1)
            df_history['surge_index'] = df_history['tension_index'].pct_change() * 100  # в процентах
            df_history['surge_index'] = df_history['surge_index'].fillna(0)
            
            # Определение аномальных всплесков (рост более 30% за период)
            df_history['is_anomaly'] = df_history['surge_index'] > 30
            
            # Создаем фигуру с двумя графиками (subplots)
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
            
            # 1. Верхний график - Интегральный индекс напряженности
            # Построение графика исторических данных
            ax1.plot(df_history['date'], df_history['tension_index'], 
                    marker='o', linestyle='-', color='blue', label='Исторические данные')
            
            # Построение графика прогноза
            ax1.plot(forecast['date'], forecast['tension_index_forecast'], 
                    marker='o', linestyle='--', color='red', label='Прогноз')
            
            # Отмечаем аномальные всплески на историческом графике
            anomaly_points = df_history[df_history['is_anomaly'] == True]
            if not anomaly_points.empty:
                ax1.scatter(anomaly_points['date'], anomaly_points['tension_index'], 
                           color='yellow', s=100, zorder=5, edgecolor='black', label='Аномальные всплески')
            
            # Находим дату 9 мая или ближайшую к ней в наших данных
            may_9_date = None
            for date in df_history['date']:
                if date.month == 5 and date.day == 9:
                    may_9_date = date
                    break
            
            # Если не нашли 9 мая, берем дату с максимальным индексом напряженности
            if may_9_date is None:
                max_tension_idx = df_history['tension_index'].idxmax()
                may_9_date = df_history.loc[max_tension_idx, 'date']
            
            # Выделяем 9 мая на графике
            may_9_data = df_history[df_history['date'] == may_9_date]
            if not may_9_data.empty:
                ax1.scatter([may_9_date], [may_9_data['tension_index'].values[0]], 
                           color='red', s=150, zorder=6, edgecolor='black', marker='*', 
                           label='9 мая (пик напряженности)')
                
                # Добавляем аннотацию с датой и значением
                ax1.annotate(f'9 мая: {may_9_data["tension_index"].values[0]:.2f}',
                            xy=(may_9_date, may_9_data['tension_index'].values[0]),
                            xytext=(10, 20), textcoords='offset points',
                            arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=.2'),
                            fontsize=12, fontweight='bold')
            
            # Добавление вертикальной линии, разделяющей историю и прогноз
            ax1.axvline(x=df_history['date'].iloc[-1], color='gray', linestyle='--', alpha=0.7)
            
            # Настройка верхнего графика
            ax1.set_title('Интегральный индекс социальной напряженности', fontsize=16)
            ax1.set_ylabel('Значение индекса', fontsize=12)
            ax1.legend(fontsize=12, loc='upper left')
            ax1.grid(True, alpha=0.3)
            
            # Устанавливаем диапазон оси Y с запасом для аннотаций
            y_max = max(df_history['tension_index'].max(), forecast['tension_index_forecast'].max()) * 1.2
            ax1.set_ylim(0, y_max)
            
            # 2. Нижний график - Индекс всплеска
            bars = ax2.bar(df_history['date'], df_history['surge_index'], alpha=0.7, label='Индекс всплеска')
            
            # Раскрашиваем столбцы в зависимости от значения
            for i, bar in enumerate(bars):
                if df_history['surge_index'].iloc[i] > 50:  # Очень высокий всплеск
                    bar.set_color('red')
                elif df_history['surge_index'].iloc[i] > 30:  # Высокий всплеск
                    bar.set_color('orange')
                else:  # Нормальный уровень
                    bar.set_color('green')
            
            # Выделяем 9 мая на графике всплесков
            may_9_surge_data = df_history[df_history['date'] == may_9_date]
            if not may_9_surge_data.empty:
                ax2.bar([may_9_date], [may_9_surge_data['surge_index'].values[0]], 
                       color='darkred', alpha=1.0, label='Всплеск 9 мая')
                
                # Добавляем аннотацию с процентом всплеска
                ax2.annotate(f'{may_9_surge_data["surge_index"].values[0]:.1f}%',
                            xy=(may_9_date, may_9_surge_data['surge_index'].values[0]),
                            xytext=(0, 5), textcoords='offset points',
                            ha='center', fontsize=10, fontweight='bold')
            
            # Добавляем горизонтальную линию для порога аномалии (30%)
            ax2.axhline(y=30, color='red', linestyle='--', alpha=0.7, label='Порог аномалии (30%)')
            
            # Настройка нижнего графика
            ax2.set_title('Индекс всплеска (относительное изменение)', fontsize=14)
            ax2.set_xlabel('Дата', fontsize=12)
            ax2.set_ylabel('Изменение, %', fontsize=12)
            ax2.legend(fontsize=10)
            ax2.grid(True, alpha=0.3)
            
            # Убираем пояснительный текст с формулами
            
            plt.tight_layout()
            # Не оставляем дополнительное место внизу, так как формулы удалены
            plt.subplots_adjust(bottom=0.05)
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"\nВизуализация сохранена в {save_path}")
            print("\nТестирование успешно завершено!")
            return True
        else:
            print("\nНе удалось создать прогноз. Проверьте логи для получения дополнительной информации.")
            return False
    
    except Exception as e:
        logger.error(f"Ошибка при тестировании модели: {e}")
        print(f"\nПроизошла ошибка при тестировании: {e}")
        return False

def main():
    """Основная функция"""
    print("="*80)
    print("ТЕСТИРОВАНИЕ LSTM МОДЕЛИ НА СИНТЕТИЧЕСКИХ ДАННЫХ")
    print("="*80)
    print("\nЭтот скрипт позволяет протестировать LSTM модель без подключения к реальной базе данных.")
    print("Будут сгенерированы синтетические данные, имитирующие реальные показатели.")
    
    test_lstm_model()

if __name__ == "__main__":
    main()