"""
Модуль для создания графиков и визуализации данных трендов СВО
"""

import matplotlib
matplotlib.use('Agg')  # Используем non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import io
import base64
from .svo_trends_analyzer import TrendData, SVOAnalysisResult
import logging

logger = logging.getLogger(__name__)

# Настройка стиля графиков
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class SVOVisualizer:
    """Класс для создания визуализаций данных СВО"""
    
    def __init__(self):
        # Настройка русского языка для графиков
        plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
        
        # Цветовая схема
        self.colors = {
            'interest': '#2E86AB',      # Синий для интереса
            'tension': '#A23B72',       # Пурпурный для напряженности
            'sentiment': '#F18F01',     # Оранжевый для настроений
            'mentions': '#C73E1D',      # Красный для упоминаний
            'background': '#F8F9FA',    # Светлый фон
            'grid': '#E9ECEF'          # Сетка
        }
    
    def create_interest_dynamics_chart(self, data: List[TrendData]) -> str:
        """Создает график динамики интереса к темам СВО"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        dates = [d.date for d in data]
        interest_levels = [d.interest_level for d in data]
        
        # Основная линия тренда
        ax.plot(dates, interest_levels, 
                color=self.colors['interest'], 
                linewidth=3, 
                label='Уровень интереса к темам СВО',
                alpha=0.8)
        
        # Заливка под графиком
        ax.fill_between(dates, interest_levels, 
                       alpha=0.3, 
                       color=self.colors['interest'])
        
        # Добавляем тренд линию
        x_numeric = mdates.date2num(dates)
        z = np.polyfit(x_numeric, interest_levels, 1)
        p = np.poly1d(z)
        slope_value = z[0] if z[0] is not None else 0.0
        ax.plot(dates, p(x_numeric), 
                "--", 
                color='red', 
                alpha=0.8, 
                linewidth=2,
                label=f'Тренд (наклон: {slope_value:.2f})')
        
        # Выделяем ключевые события
        self._add_key_events_markers(ax, dates, interest_levels)
        
        # Настройка осей
        ax.set_xlabel('Период', fontsize=12, fontweight='bold')
        ax.set_ylabel('Уровень интереса (проценты)', fontsize=12, fontweight='bold')
        ax.set_title('Динамика интереса к темам СВО (2022-2025)\nЗначительное падение интереса со временем', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Форматирование дат
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        # Сетка и стиль
        ax.grid(True, alpha=0.3, color=self.colors['grid'])
        ax.legend(loc='upper right', fontsize=10)
        ax.set_facecolor(self.colors['background'])
        
        # Добавляем аннотации
        self._add_trend_annotations(ax, dates, interest_levels)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_social_tension_chart(self, data: List[TrendData]) -> str:
        """Создает график роста социальной напряженности"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        dates = [d.date for d in data]
        tension_levels = [d.social_tension for d in data]
        
        # Основная линия
        ax.plot(dates, tension_levels, 
                color=self.colors['tension'], 
                linewidth=3, 
                label='Уровень социальной напряженности',
                alpha=0.8)
        
        # Заливка с градиентом
        ax.fill_between(dates, tension_levels, 
                       alpha=0.4, 
                       color=self.colors['tension'])
        
        # Тренд линия
        x_numeric = mdates.date2num(dates)
        z = np.polyfit(x_numeric, tension_levels, 1)
        p = np.poly1d(z)
        slope_value = z[0] if z[0] is not None else 0.0
        ax.plot(dates, p(x_numeric), 
                "--", 
                color='darkred', 
                alpha=0.8, 
                linewidth=2,
                label=f'Тренд роста (наклон: +{slope_value:.2f})')
        
        # Зоны напряженности
        ax.axhspan(0, 30, alpha=0.1, color='green', label='Низкая напряженность')
        ax.axhspan(30, 60, alpha=0.1, color='yellow', label='Умеренная напряженность')
        ax.axhspan(60, 100, alpha=0.1, color='red', label='Высокая напряженность')
        
        # Настройка осей
        ax.set_xlabel('Период', fontsize=12, fontweight='bold')
        ax.set_ylabel('Уровень социальной напряженности (проценты)', fontsize=12, fontweight='bold')
        ax.set_title('Рост социальной напряженности (2022-2025)\nПостоянный рост напряженности в обществе', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Форматирование дат
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        # Сетка и стиль
        ax.grid(True, alpha=0.3, color=self.colors['grid'])
        ax.legend(loc='upper left', fontsize=10)
        ax.set_facecolor(self.colors['background'])
        ax.set_ylim(0, 100)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_combined_trends_chart(self, data: List[TrendData]) -> str:
        """Создает комбинированный график интереса и напряженности"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)
        
        dates = [d.date for d in data]
        interest_levels = [d.interest_level for d in data]
        tension_levels = [d.social_tension for d in data]
        
        # График интереса
        ax1.plot(dates, interest_levels, 
                color=self.colors['interest'], 
                linewidth=3, 
                label='Интерес к темам СВО')
        ax1.fill_between(dates, interest_levels, 
                        alpha=0.3, 
                        color=self.colors['interest'])
        
        ax1.set_ylabel('Уровень интереса (проценты)', fontsize=12, fontweight='bold')
        ax1.set_title('Сравнительная динамика: Интерес vs Социальная напряженность', 
                     fontsize=16, fontweight='bold', pad=20)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_facecolor(self.colors['background'])
        
        # График напряженности
        ax2.plot(dates, tension_levels, 
                color=self.colors['tension'], 
                linewidth=3, 
                label='Социальная напряженность')
        ax2.fill_between(dates, tension_levels, 
                        alpha=0.3, 
                        color=self.colors['tension'])
        
        ax2.set_xlabel('Период', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Уровень напряженности (проценты)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.set_facecolor(self.colors['background'])
        
        # Форматирование дат
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_correlation_heatmap(self, data: List[TrendData]) -> str:
        """Создает тепловую карту корреляций"""
        # Подготовка данных
        df = pd.DataFrame([{
            'Интерес к СВО': d.interest_level,
            'Социальная напряженность': d.social_tension,
            'Количество упоминаний': d.mentions_count,
            'Настроения': d.sentiment_score
        } for d in data])
        
        # Вычисление корреляций
        correlation_matrix = df.corr()
        
        # Создание графика
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Тепловая карта
        sns.heatmap(correlation_matrix, 
                   annot=True, 
                   cmap='RdYlBu_r', 
                   center=0,
                   square=True,
                   fmt='.3f',
                   cbar_kws={'label': 'Коэффициент корреляции'},
                   ax=ax)
        
        ax.set_title('Корреляционная матрица показателей СВО', 
                    fontsize=16, fontweight='bold', pad=20)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_sentiment_analysis_chart(self, data: List[TrendData]) -> str:
        """Создает график анализа настроений"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        dates = [d.date for d in data]
        sentiment_scores = [d.sentiment_score for d in data]
        
        # Цветовая карта для настроений
        colors = ['red' if s < -0.1 else 'orange' if s < 0.1 else 'green' for s in sentiment_scores]
        
        # Столбчатый график
        bars = ax.bar(dates, sentiment_scores, 
                     color=colors, 
                     alpha=0.7, 
                     width=7)
        
        # Линия тренда
        x_numeric = mdates.date2num(dates)
        z = np.polyfit(x_numeric, sentiment_scores, 1)
        p = np.poly1d(z)
        ax.plot(dates, p(x_numeric), 
                "--", 
                color='black', 
                alpha=0.8, 
                linewidth=2,
                label=f'Тренд настроений')
        
        # Горизонтальные линии для зон
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax.axhspan(-1, -0.1, alpha=0.1, color='red', label='Негативные настроения')
        ax.axhspan(-0.1, 0.1, alpha=0.1, color='orange', label='Нейтральные настроения')
        ax.axhspan(0.1, 1, alpha=0.1, color='green', label='Позитивные настроения')
        
        # Настройка осей
        ax.set_xlabel('Период', fontsize=12, fontweight='bold')
        ax.set_ylabel('Индекс настроений', fontsize=12, fontweight='bold')
        ax.set_title('Динамика общественных настроений по темам СВО\nПостепенное ухудшение настроений', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Форматирование дат
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        # Сетка и стиль
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend(loc='upper right', fontsize=10)
        ax.set_facecolor(self.colors['background'])
        ax.set_ylim(-0.6, 0.4)
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def create_mentions_volume_chart(self, data: List[TrendData]) -> str:
        """Создает график объема упоминаний"""
        fig, ax = plt.subplots(figsize=(14, 8))
        
        dates = [d.date for d in data]
        mentions = [d.mentions_count for d in data]
        
        # Столбчатый график
        bars = ax.bar(dates, mentions, 
                     color=self.colors['mentions'], 
                     alpha=0.7, 
                     width=5)
        
        # Скользящее среднее
        window_size = min(4, len(mentions) // 4)
        if window_size > 1:
            moving_avg = pd.Series(mentions).rolling(window=window_size).mean()
            ax.plot(dates, moving_avg, 
                   color='darkred', 
                   linewidth=3, 
                   label=f'Скользящее среднее ({window_size} недель)')
        
        # Настройка осей
        ax.set_xlabel('Период', fontsize=12, fontweight='bold')
        ax.set_ylabel('Количество упоминаний', fontsize=12, fontweight='bold')
        ax.set_title('Объем упоминаний тем СВО в социальных сетях', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Форматирование дат
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.xticks(rotation=45)
        
        # Сетка и стиль
        ax.grid(True, alpha=0.3, axis='y')
        if window_size > 1:
            ax.legend()
        ax.set_facecolor(self.colors['background'])
        
        plt.tight_layout()
        return self._fig_to_base64(fig)
    
    def _add_key_events_markers(self, ax, dates, values):
        """Добавляет маркеры ключевых событий"""
        key_events = [
            (datetime(2022, 2, 24), 'Начало СВО'),
            (datetime(2022, 9, 21), 'Частичная мобилизация'),
            (datetime(2023, 6, 24), 'События с ЧВК'),
            (datetime(2024, 3, 22), 'Теракт в Крокусе')
        ]
        
        for event_date, event_name in key_events:
            if dates[0] <= event_date <= dates[-1]:
                # Находим ближайшую дату в данных
                closest_idx = min(range(len(dates)), 
                                key=lambda i: abs((dates[i] - event_date).days))
                
                ax.annotate(event_name, 
                           xy=(dates[closest_idx], values[closest_idx]),
                           xytext=(10, 20), 
                           textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.3', 
                                   facecolor='yellow', 
                                   alpha=0.7),
                           arrowprops=dict(arrowstyle='->', 
                                         connectionstyle='arc3,rad=0'),
                           fontsize=9)
    
    def _add_trend_annotations(self, ax, dates, values):
        """Добавляет аннотации трендов"""
        # Вычисляем общий тренд
        x_numeric = mdates.date2num(dates)
        slope = np.polyfit(x_numeric, values, 1)[0]
        
        # Добавляем текстовую аннотацию
        direction = '↓' if slope < 0 else '↑'
        trend_text = f"Общий тренд: {direction} {abs(slope):.2f} пунктов в неделю"
        ax.text(0.02, 0.98, trend_text, 
               transform=ax.transAxes, 
               fontsize=12, 
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    def _fig_to_base64(self, fig) -> str:
        """Конвертирует matplotlib figure в base64 строку"""
        img_buffer = io.BytesIO()
        fig.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close(fig)  # Освобождаем память
        return img_str
    
    def create_dashboard_charts(self, data: List[TrendData]) -> Dict[str, str]:
        """Создает все графики для дашборда"""
        charts = {}
        
        try:
            charts['interest_dynamics'] = self.create_interest_dynamics_chart(data)
            charts['social_tension'] = self.create_social_tension_chart(data)
            charts['combined_trends'] = self.create_combined_trends_chart(data)
            charts['correlation_heatmap'] = self.create_correlation_heatmap(data)
            charts['sentiment_analysis'] = self.create_sentiment_analysis_chart(data)
            charts['mentions_volume'] = self.create_mentions_volume_chart(data)
            
            logger.info(f"Создано {len(charts)} графиков для дашборда")
            
        except Exception as e:
            logger.error(f"Ошибка при создании графиков: {e}")
            
        return charts
    
    def create_network_graph(self, data: List[TrendData]) -> Dict:
        """Создает данные для сетевого графа связей между темами СВО"""
        try:
            # Создаем узлы (темы)
            nodes = [
                {"id": "svo_main", "name": "СВО", "group": 1, "size": 30},
                {"id": "ukraine", "name": "Украина", "group": 2, "size": 25},
                {"id": "russia", "name": "Россия", "group": 3, "size": 25},
                {"id": "nato", "name": "НАТО", "group": 4, "size": 20},
                {"id": "sanctions", "name": "Санкции", "group": 5, "size": 18},
                {"id": "energy", "name": "Энергетика", "group": 6, "size": 15},
                {"id": "military", "name": "Военные действия", "group": 7, "size": 22},
                {"id": "diplomacy", "name": "Дипломатия", "group": 8, "size": 16},
                {"id": "economy", "name": "Экономика", "group": 9, "size": 19},
                {"id": "media", "name": "СМИ", "group": 10, "size": 14}
            ]
            
            # Создаем связи между узлами
            links = [
                {"source": "svo_main", "target": "ukraine", "value": 10, "type": "conflict"},
                {"source": "svo_main", "target": "russia", "value": 10, "type": "conflict"},
                {"source": "ukraine", "target": "nato", "value": 8, "type": "support"},
                {"source": "russia", "target": "sanctions", "value": 9, "type": "impact"},
                {"source": "sanctions", "target": "economy", "value": 7, "type": "impact"},
                {"source": "sanctions", "target": "energy", "value": 6, "type": "impact"},
                {"source": "military", "target": "svo_main", "value": 9, "type": "direct"},
                {"source": "diplomacy", "target": "svo_main", "value": 5, "type": "indirect"},
                {"source": "media", "target": "svo_main", "value": 6, "type": "coverage"},
                {"source": "economy", "target": "russia", "value": 7, "type": "impact"},
                {"source": "economy", "target": "ukraine", "value": 6, "type": "impact"},
                {"source": "nato", "target": "military", "value": 7, "type": "support"},
                {"source": "energy", "target": "europe", "value": 5, "type": "supply"}
            ]
            
            # Добавляем узел Европа, если его нет
            if not any(node["id"] == "europe" for node in nodes):
                nodes.append({"id": "europe", "name": "Европа", "group": 11, "size": 17})
            
            # Динамически изменяем размеры узлов на основе данных
            if data:
                avg_interest = sum(d.interest_level for d in data) / len(data)
                avg_tension = sum(d.social_tension for d in data) / len(data)
                
                # Корректируем размеры узлов на основе средних значений
                for node in nodes:
                    if node["id"] in ["svo_main", "ukraine", "russia"]:
                        node["size"] = max(20, min(40, node["size"] + avg_interest * 0.3))
                    elif node["id"] in ["military", "sanctions"]:
                        node["size"] = max(15, min(35, node["size"] + avg_tension * 0.2))
            
            network_data = {
                "nodes": nodes,
                "links": links,
                "metadata": {
                    "total_nodes": len(nodes),
                    "total_links": len(links),
                    "created_at": datetime.now().isoformat(),
                    "data_period": f"{data[0].date.strftime('%Y-%m-%d')} - {data[-1].date.strftime('%Y-%m-%d')}" if data else "No data"
                }
            }
            
            logger.info(f"Создан сетевой граф с {len(nodes)} узлами и {len(links)} связями")
            return network_data
            
        except Exception as e:
            logger.error(f"Ошибка при создании сетевого графа: {e}")
            # Возвращаем базовую структуру в случае ошибки
            return {
                "nodes": [{"id": "svo_main", "name": "СВО", "group": 1, "size": 30}],
                "links": [],
                "metadata": {"error": str(e)}
            }