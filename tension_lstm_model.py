import os
import time
import pickle
from datetime import datetime, timedelta
import logging
import sys

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import tensorflow as tf
from clickhouse_driver import Client
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("tension_lstm.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TensionLSTMModel:
    """Класс для анализа и прогнозирования индекса социальной напряжённости
    с использованием LSTM нейронной сети"""
    
    def __init__(self, model_path='models/tension_lstm_model.keras', 
                 scaler_path='models/tension_scaler.pkl',
                 lookback=5, forecast_days=2):
        """Инициализация модели
        
        Args:
            model_path (str): Путь для сохранения/загрузки модели
            scaler_path (str): Путь для сохранения/загрузки нормализатора
            lookback (int): Количество дней в истории для предсказания
            forecast_days (int): Количество дней для прогноза
        """
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.lookback = lookback
        self.forecast_days = forecast_days
        self.model = None
        self.scaler = None
        self.features = None
        
        # Создаем директорию для моделей, если она не существует
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Попытка загрузить существующую модель и скейлер
        self._load_model_and_scaler()
    
    def _load_model_and_scaler(self):
        """Загрузка сохраненной модели и скейлера, если они существуют"""
        try:
            if os.path.exists(self.model_path):
                try:
                    # Пробуем загрузить модель в новом формате SavedModel
                    self.model = tf.keras.models.load_model(self.model_path)
                    logger.info(f"Модель загружена из {self.model_path} в формате SavedModel")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить модель в формате SavedModel: {e}")
                    # Пробуем загрузить в старом формате .h5
                    h5_path = f"{self.model_path}.h5"
                    if os.path.exists(h5_path):
                        self.model = load_model(h5_path)
                        logger.info(f"Модель загружена из {h5_path} в формате H5")
            
            if os.path.exists(self.scaler_path):
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                logger.info(f"Скейлер загружен из {self.scaler_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели или скейлера: {e}")
    
    def connect_to_clickhouse(self, max_retries=3, retry_delay=2):
        """Установка соединения с базой данных ClickHouse"""
        for attempt in range(max_retries):
            try:
                client = Client(
                    host=Config.CLICKHOUSE_HOST, 
                    port=Config.CLICKHOUSE_NATIVE_PORT,
                    user=Config.CLICKHOUSE_USER,
                    password=Config.CLICKHOUSE_PASSWORD,
                    settings={
                        'max_block_size': 100000,
                        'connect_timeout': 10,
                        'receive_timeout': 300,
                        'send_timeout': 300
                    }
                )
                # Проверка соединения
                client.execute('SELECT 1')
                return client
            except Exception as e:
                logger.error(f"Ошибка подключения к ClickHouse (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Повторная попытка через {retry_delay} секунд...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Не удалось подключиться к ClickHouse")
                    return None
    
    def fetch_data_from_clickhouse(self, days=30):
        """Получение данных из ClickHouse за указанный период
        
        Args:
            days (int): Количество дней для выборки данных
            
        Returns:
            pandas.DataFrame: Данные из ClickHouse
        """
        client = self.connect_to_clickhouse()
        if not client:
            logger.error("Не удалось получить данные из ClickHouse")
            return None
        
        try:
            # Получаем данные из таблиц telegram_headlines и israil_headlines
            # Агрегируем по дням и вычисляем метрики
            query = f"""
            WITH 
                telegram_daily AS (
                    SELECT 
                        toDate(parsed_date) AS date,
                        count() AS message_count,
                        avg(length(content)) AS avg_content_length
                    FROM news.telegram_headlines
                    WHERE parsed_date >= now() - INTERVAL {days} DAY
                    GROUP BY date
                ),
                israil_daily AS (
                    SELECT 
                        toDate(parsed_date) AS date,
                        count() AS message_count
                    FROM news.israil_headlines
                    WHERE parsed_date >= now() - INTERVAL {days} DAY
                    GROUP BY date
                )
            SELECT 
                t.date,
                t.message_count AS telegram_count,
                t.avg_content_length AS telegram_avg_length,
                i.message_count AS israil_count
            FROM telegram_daily t
            FULL OUTER JOIN israil_daily i ON t.date = i.date
            ORDER BY t.date
            """
            
            result = client.execute(query)
            
            # Преобразуем результат в DataFrame
            df = pd.DataFrame(result, columns=['date', 'telegram_count', 'telegram_avg_length', 'israil_count'])
            
            # Заполняем пропущенные значения
            df = df.fillna(0)
            
            # Вычисляем интегральный индекс социальной напряженности
            # I_t = α∙Neg_t + β∙Emot_t + γ∙Eng_t, где α+β+γ=1
            # Neg_t - доля сообщений с негативной тональностью (используем telegram_count как прокси)
            # Emot_t - индекс интенсивности негативных эмоций (используем telegram_avg_length как прокси)
            # Eng_t - индекс вовлечённости (используем israil_count как прокси)
            
            # Нормализуем компоненты
            df['neg_component'] = df['telegram_count'] / df['telegram_count'].max() if df['telegram_count'].max() > 0 else 0
            df['emot_component'] = df['telegram_avg_length'] / df['telegram_avg_length'].max() if df['telegram_avg_length'].max() > 0 else 0
            df['eng_component'] = df['israil_count'] / df['israil_count'].max() if df['israil_count'].max() > 0 else 0
            
            # Веса компонентов (α, β, γ)
            alpha, beta, gamma = 0.5, 0.3, 0.2  # α+β+γ=1
            
            # Расчет интегрального индекса напряженности
            df['tension_index'] = alpha * df['neg_component'] + beta * df['emot_component'] + gamma * df['eng_component']
            
            # Расчет индекса всплеска S_t = (I_t - I_(t-1)) / I_(t-1)
            df['surge_index'] = df['tension_index'].pct_change() * 100  # в процентах
            df['surge_index'] = df['surge_index'].fillna(0)
            
            # Определение аномальных всплесков (рост более 30% за период)
            df['is_anomaly'] = df['surge_index'] > 30
            
            logger.info(f"Получено {len(df)} записей из ClickHouse")
            return df
        
        except Exception as e:
            logger.error(f"Ошибка при получении данных из ClickHouse: {e}")
            return None
    
    def prepare_data(self, df):
        """Подготовка данных для обучения LSTM модели
        
        Args:
            df (pandas.DataFrame): Исходные данные
            
        Returns:
            tuple: (X_train, y_train, X_test, y_test)
        """
        if df is None or len(df) < self.lookback + self.forecast_days:
            logger.error("Недостаточно данных для подготовки")
            return None
        
        # Сохраняем список признаков
        self.features = ['telegram_count', 'telegram_avg_length', 'israil_count', 'tension_index']
        
        # Выбираем только числовые признаки
        data = df[self.features].values
        
        # Нормализация данных
        if self.scaler is None:
            self.scaler = MinMaxScaler(feature_range=(0, 1))
            data_scaled = self.scaler.fit_transform(data)
            
            # Сохраняем скейлер
            with open(self.scaler_path, 'wb') as f:
                pickle.dump(self.scaler, f)
            logger.info(f"Скейлер сохранен в {self.scaler_path}")
        else:
            data_scaled = self.scaler.transform(data)
        
        # Создаем последовательности для LSTM
        X, y = [], []
        for i in range(len(data_scaled) - self.lookback - self.forecast_days + 1):
            X.append(data_scaled[i:(i + self.lookback)])
            y.append(data_scaled[i + self.lookback:i + self.lookback + self.forecast_days, -1])  # Прогнозируем только tension_index
        
        X, y = np.array(X), np.array(y)
        
        # Аугментация данных для малого набора
        if len(X) < 30:  # Если данных мало, генерируем синтетические
            logger.info("Применяется аугментация данных для увеличения обучающей выборки")
            X_augmented, y_augmented = self._augment_data(X, y)
            X = np.vstack([X, X_augmented])
            y = np.vstack([y, y_augmented])
            logger.info(f"Размер данных после аугментации: X: {X.shape}, y: {y.shape}")
        
        # Разделение на обучающую и тестовую выборки (80/20)
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        
        logger.info(f"Подготовлены данные: X_train: {X_train.shape}, y_train: {y_train.shape}, X_test: {X_test.shape}, y_test: {y_test.shape}")
        
        return X_train, y_train, X_test, y_test
        
    def _augment_data(self, X, y, augmentation_factor=2):
        """Аугментация данных для малых наборов
        
        Args:
            X (numpy.ndarray): Исходные входные данные
            y (numpy.ndarray): Исходные целевые данные
            augmentation_factor (int): Коэффициент увеличения данных
            
        Returns:
            tuple: (X_augmented, y_augmented)
        """
        n_samples, timesteps, n_features = X.shape
        X_augmented = []
        y_augmented = []
        
        for _ in range(augmentation_factor):
            # Создаем копии с небольшим шумом
            noise_level = 0.05
            for i in range(n_samples):
                # Добавляем случайный шум к временным рядам
                noise = np.random.normal(0, noise_level, (timesteps, n_features))
                X_noisy = X[i] + noise
                
                # Добавляем шум к целевым значениям
                y_noise = np.random.normal(0, noise_level, y[i].shape)
                y_noisy = y[i] + y_noise
                
                X_augmented.append(X_noisy)
                y_augmented.append(y_noisy)
                
        return np.array(X_augmented), np.array(y_augmented)
    
    def build_model(self, input_shape):
        """Создание архитектуры LSTM модели
        
        Args:
            input_shape (tuple): Форма входных данных (lookback, n_features)
            
        Returns:
            tensorflow.keras.models.Sequential: Модель LSTM
        """
        model = Sequential()
        
        # Упрощенная архитектура для малого набора данных
        # Один LSTM слой с меньшим количеством нейронов
        model.add(LSTM(20, input_shape=input_shape, 
                      kernel_regularizer=tf.keras.regularizers.l2(0.001)))
        model.add(Dropout(0.3))
        
        # Выходной слой (прогноз на forecast_days дней вперед)
        model.add(Dense(self.forecast_days, 
                       kernel_regularizer=tf.keras.regularizers.l2(0.001)))
        
        # Компиляция модели
        model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), 
                     loss='mse', metrics=['mae'])
        
        logger.info(f"Создана упрощенная LSTM модель для малого набора данных")
        model.summary(print_fn=logger.info)
        return model
    
    def train_model(self, X_train, y_train, X_test, y_test, epochs=50, batch_size=16):
        """Обучение LSTM модели
        
        Args:
            X_train, y_train, X_test, y_test: Обучающие и тестовые данные
            epochs (int): Количество эпох обучения (уменьшено для малых данных)
            batch_size (int): Размер батча (уменьшен для малых данных)
            
        Returns:
            tensorflow.keras.models.Sequential: Обученная модель
        """
        if X_train is None or y_train is None:
            logger.error("Нет данных для обучения")
            return None
        
        # Создаем модель, если она еще не создана
        if self.model is None:
            self.model = self.build_model((X_train.shape[1], X_train.shape[2]))
        
        # Настройка ранней остановки и сохранения лучшей модели
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True),
            # Используем ReduceLROnPlateau для адаптивного изменения скорости обучения
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=5, min_lr=0.0001, verbose=1
            )
        ]
        
        # Обучение модели
        history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            batch_size=batch_size,
            validation_data=(X_test, y_test),
            callbacks=callbacks,
            verbose=1,
            # Используем class_weight для балансировки, если данных мало
            shuffle=True
        )
        
        logger.info(f"Модель обучена за {len(history.history['loss'])} эпох")
        
        # Оценка модели на тестовых данных
        test_loss = self.model.evaluate(X_test, y_test, verbose=0)
        if isinstance(test_loss, list):
            logger.info(f"Ошибка на тестовых данных: MSE={test_loss[0]:.4f}, MAE={test_loss[1]:.4f}")
        else:
            logger.info(f"Ошибка на тестовых данных (MSE): {test_loss:.4f}")
        
        # Сохраняем модель в формате SavedModel
        self.model.save(self.model_path)
        logger.info(f"Модель сохранена в {self.model_path} в формате SavedModel")
        
        return self.model
    
    def predict(self, X):
        """Прогнозирование с помощью обученной модели
        
        Args:
            X (numpy.ndarray): Входные данные для прогноза
            
        Returns:
            numpy.ndarray: Прогноз индекса напряженности
        """
        if self.model is None:
            logger.error("Модель не обучена")
            return None
        
        # Прогноз
        predictions = self.model.predict(X)
        
        # Преобразование прогноза обратно в исходный масштаб
        # Создаем массив с нулями для всех признаков, кроме tension_index
        pred_full = np.zeros((predictions.shape[0], predictions.shape[1], len(self.features)))
        # Заполняем последний столбец (tension_index) предсказанными значениями
        pred_full[:, :, -1] = predictions
        
        # Изменяем форму для обратного преобразования
        pred_full_reshaped = pred_full.reshape(pred_full.shape[0] * pred_full.shape[1], pred_full.shape[2])
        
        # Обратное преобразование
        pred_full_inverted = self.scaler.inverse_transform(pred_full_reshaped)
        
        # Извлекаем только tension_index
        tension_index_pred = pred_full_inverted[:, -1].reshape(predictions.shape[0], predictions.shape[1])
        
        # Ограничиваем значения индекса положительными числами
        tension_index_pred = np.maximum(tension_index_pred, 0)
        
        # Применяем сглаживание для устранения резких скачков
        for i in range(tension_index_pred.shape[0]):
            if tension_index_pred.shape[1] > 2:  # Если есть достаточно точек для сглаживания
                # Применяем скользящее среднее
                smoothed = np.convolve(tension_index_pred[i], np.ones(2)/2, mode='same')
                # Для первой и последней точки используем исходные значения
                smoothed[0] = tension_index_pred[i, 0]
                smoothed[-1] = tension_index_pred[i, -1]
                tension_index_pred[i] = smoothed
        
        return tension_index_pred
    
    def evaluate_model(self, X_test, y_test):
        """Оценка качества модели на тестовых данных
        
        Args:
            X_test, y_test: Тестовые данные
            
        Returns:
            dict: Метрики качества модели
        """
        if self.model is None:
            logger.error("Модель не обучена")
            return None
        
        # Прогноз на тестовых данных
        y_pred = self.predict(X_test)
        
        # Преобразование y_test обратно в исходный масштаб
        y_test_full = np.zeros((y_test.shape[0], y_test.shape[1], len(self.features)))
        y_test_full[:, :, -1] = y_test
        y_test_full_reshaped = y_test_full.reshape(y_test_full.shape[0] * y_test_full.shape[1], y_test_full.shape[2])
        y_test_full_inverted = self.scaler.inverse_transform(y_test_full_reshaped)
        y_test_inverted = y_test_full_inverted[:, -1].reshape(y_test.shape[0], y_test.shape[1])
        
        # Расчет метрик для каждого дня прогноза
        metrics = {}
        for day in range(self.forecast_days):
            day_metrics = {
                'mse': mean_squared_error(y_test_inverted[:, day], y_pred[:, day]),
                'rmse': np.sqrt(mean_squared_error(y_test_inverted[:, day], y_pred[:, day])),
                'mae': mean_absolute_error(y_test_inverted[:, day], y_pred[:, day]),
                'r2': r2_score(y_test_inverted[:, day], y_pred[:, day])
            }
            metrics[f'day_{day+1}'] = day_metrics
            logger.info(f"Метрики для дня {day+1}: MSE={day_metrics['mse']:.4f}, RMSE={day_metrics['rmse']:.4f}, MAE={day_metrics['mae']:.4f}, R2={day_metrics['r2']:.4f}")
        
        # Общие метрики
        metrics['overall'] = {
            'mse': mean_squared_error(y_test_inverted.flatten(), y_pred.flatten()),
            'rmse': np.sqrt(mean_squared_error(y_test_inverted.flatten(), y_pred.flatten())),
            'mae': mean_absolute_error(y_test_inverted.flatten(), y_pred.flatten()),
            'r2': r2_score(y_test_inverted.flatten(), y_pred.flatten())
        }
        logger.info(f"Общие метрики: MSE={metrics['overall']['mse']:.4f}, RMSE={metrics['overall']['rmse']:.4f}, MAE={metrics['overall']['mae']:.4f}, R2={metrics['overall']['r2']:.4f}")
        
        return metrics
    
    def forecast_future(self, days=None):
        """Прогнозирование индекса напряженности на будущее
        
        Args:
            days (int): Количество дней для прогноза (по умолчанию self.forecast_days)
            
        Returns:
            pandas.DataFrame: Прогноз индекса напряженности
        """
        if days is None:
            days = self.forecast_days
        
        if self.model is None:
            logger.error("Модель не обучена")
            return None
        
        # Получаем последние данные
        df = self.fetch_data_from_clickhouse(days=self.lookback + 5)  # Берем с запасом
        if df is None or len(df) < self.lookback:
            logger.error("Недостаточно данных для прогноза")
            return None
        
        # Берем последние lookback записей
        last_data = df.iloc[-self.lookback:][self.features].values
        
        # Нормализация данных
        last_data_scaled = self.scaler.transform(last_data)
        
        # Подготовка входных данных для модели
        X = np.array([last_data_scaled])
        
        # Прогноз
        predictions = self.predict(X)[0]  # Берем первый (и единственный) прогноз
        
        # Получаем последнее известное значение индекса для сглаживания перехода
        last_known_index = df['tension_index'].iloc[-1]
        
        # Дополнительное сглаживание прогноза для более плавного перехода
        if len(predictions) > 0:
            # Сглаживаем переход от последнего известного значения к первому прогнозируемому
            predictions[0] = (last_known_index + predictions[0]) / 2
            
            # Дополнительное сглаживание всего прогноза
            if len(predictions) > 2:
                # Применяем экспоненциальное сглаживание
                alpha = 0.7  # Коэффициент сглаживания (0 < alpha < 1)
                smoothed = np.copy(predictions)
                for i in range(1, len(predictions)):
                    smoothed[i] = alpha * predictions[i] + (1 - alpha) * smoothed[i-1]
                predictions = smoothed
        
        # Создаем DataFrame с прогнозом
        last_date = df['date'].iloc[-1]
        forecast_dates = [last_date + timedelta(days=i+1) for i in range(len(predictions))]
        forecast_df = pd.DataFrame({
            'date': forecast_dates,
            'tension_index_forecast': predictions
        })
        
        logger.info(f"Создан прогноз на {len(predictions)} дней")
        return forecast_df
    
    def visualize_forecast(self, history_days=14, save_path=None):
        """Визуализация исторических данных и прогноза
        
        Args:
            history_days (int): Количество дней истории для отображения
            save_path (str): Путь для сохранения графика
            
        Returns:
            matplotlib.figure.Figure: Объект графика
        """
        # Получаем исторические данные
        df_history = self.fetch_data_from_clickhouse(days=history_days + 5)  # Берем с запасом
        if df_history is None or len(df_history) < history_days:
            logger.error("Недостаточно исторических данных для визуализации")
            return None
        
        # Берем последние history_days записей
        df_history = df_history.iloc[-history_days:]
        
        # Получаем прогноз
        df_forecast = self.forecast_future()
        if df_forecast is None:
            logger.error("Не удалось получить прогноз для визуализации")
            return None
        
        # Создаем фигуру с двумя графиками (subplots)
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # Настройка стиля графика
        sns.set(style="whitegrid")
        
        # 1. Верхний график - Интегральный индекс напряженности
        # Построение графика исторических данных
        ax1.plot(df_history['date'], df_history['tension_index'], 
                marker='o', linestyle='-', color='blue', label='Исторические данные')
        
        # Построение графика прогноза
        ax1.plot(df_forecast['date'], df_forecast['tension_index_forecast'], 
                marker='o', linestyle='--', color='red', label='Прогноз')
        
        # Отмечаем аномальные всплески на историческом графике
        if 'is_anomaly' in df_history.columns:
            anomaly_points = df_history[df_history['is_anomaly'] == True]
            if not anomaly_points.empty:
                ax1.scatter(anomaly_points['date'], anomaly_points['tension_index'], 
                           color='yellow', s=100, zorder=5, edgecolor='black', label='Аномальные всплески')
        
        # Добавление вертикальной линии, разделяющей историю и прогноз
        ax1.axvline(x=df_history['date'].iloc[-1], color='gray', linestyle='--', alpha=0.7)
        
        # Настройка верхнего графика
        ax1.set_title('Интегральный индекс социальной напряженности', fontsize=16)
        ax1.set_ylabel('Значение индекса', fontsize=12)
        ax1.legend(fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # 2. Нижний график - Индекс всплеска
        if 'surge_index' in df_history.columns:
            ax2.bar(df_history['date'], df_history['surge_index'], color='green', alpha=0.7, label='Индекс всплеска')
            
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
        
        # Сохранение графика, если указан путь
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"График сохранен в {save_path}")
        
        return plt.gcf()
    
    def run_full_pipeline(self, train=True, visualize=True):
        """Запуск полного пайплайна: загрузка данных, обучение модели, прогноз
        
        Args:
            train (bool): Нужно ли обучать модель
            visualize (bool): Нужно ли визуализировать результаты
            
        Returns:
            pandas.DataFrame: Прогноз индекса напряженности
        """
        # Загрузка данных
        df = self.fetch_data_from_clickhouse(days=60)  # Берем данные за 60 дней для обучения
        if df is None:
            logger.error("Не удалось загрузить данные")
            return None
        
        # Если нужно обучить модель
        if train:
            # Подготовка данных
            train_data = self.prepare_data(df)
            if train_data is None:
                logger.error("Не удалось подготовить данные для обучения")
                return None
            
            X_train, y_train, X_test, y_test = train_data
            
            # Обучение модели
            self.train_model(X_train, y_train, X_test, y_test)
            
            # Оценка модели
            metrics = self.evaluate_model(X_test, y_test)
            if metrics is None:
                logger.error("Не удалось оценить модель")
        
        # Прогноз на будущее
        forecast = self.forecast_future()
        if forecast is None:
            logger.error("Не удалось создать прогноз")
            return None
        
        # Визуализация результатов
        if visualize:
            # Создаем директорию для графиков, если она не существует
            os.makedirs('plots', exist_ok=True)
            
            # Генерируем имя файла с текущей датой
            current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = f'plots/tension_forecast_{current_date}.png'
            
            # Визуализация
            self.visualize_forecast(save_path=save_path)
        
        return forecast


def main():
    """Основная функция для запуска модели"""
    # Создание и запуск модели
    model = TensionLSTMModel()
    
    # Запуск полного пайплайна
    forecast = model.run_full_pipeline(train=True, visualize=True)
    
    if forecast is not None:
        print("\nПрогноз индекса социальной напряженности:")
        print(forecast)
        print("\nМодель успешно обучена и создан прогноз!")
    else:
        print("\nНе удалось создать прогноз. Проверьте логи для получения дополнительной информации.")

if __name__ == "__main__":
    main()