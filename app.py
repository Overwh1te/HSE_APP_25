
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import warnings
warnings.filterwarnings('ignore')

# инициализация состояния сессии
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None
if 'temperature_analyzer' not in st.session_state:
    st.session_state.temperature_analyzer = None

# заголовок приложения
st.set_page_config(
    page_title="Анализ температурных данных",
    layout="wide"
)

st.title("Анализ температурных данных и мониторинг погоды")
st.markdown("---")

# сопоставление месяцев с сезонами (должно быть глобально)
month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

class TemperatureAnalyzer:
    """анализатор для сравнения текущей и исторической температур"""
    
    def __init__(self, historical_data: pd.DataFrame):
        self.historical_data = historical_data
        self.historical_data['timestamp'] = pd.to_datetime(self.historical_data['timestamp'])
        self.historical_data['month'] = self.historical_data['timestamp'].dt.month
        self.historical_data['season'] = self.historical_data['month'].map(month_to_season)
    
    def get_seasonal_norms(self, city: str, current_month: int) -> dict:
        """получение сезонных норм для города в текущем месяце"""
        season = month_to_season.get(current_month, 'winter')
        
        city_data = self.historical_data[self.historical_data['city'] == city]
        seasonal_data = city_data[city_data['season'] == season]
        
        if len(seasonal_data) == 0:
            return None
        
        mean_temp = seasonal_data['temperature'].mean()
        std_temp = seasonal_data['temperature'].std()
        
        return {
            'season': season,
            'mean': mean_temp,
            'std': std_temp,
            'min': seasonal_data['temperature'].min(),
            'max': seasonal_data['temperature'].max(),
            'lower_bound': mean_temp - 2 * std_temp,
            'upper_bound': mean_temp + 2 * std_temp,
            'sample_size': len(seasonal_data)
        }
    
    def check_temperature_anomaly(self, city: str, current_temp: float) -> dict:
        """является ли текущая температура аномальной?"""
        current_month = datetime.now().month
        seasonal_norms = self.get_seasonal_norms(city, current_month)
        
        if seasonal_norms is None:
            return {
                'is_anomaly': None,
                'message': 'Нет исторических данных для этого города',
                'norms': None
            }
        
        lower_bound = seasonal_norms['lower_bound']
        upper_bound = seasonal_norms['upper_bound']
        
        is_anomaly = current_temp < lower_bound or current_temp > upper_bound
        deviation = abs(current_temp - seasonal_norms['mean'])
        
        if is_anomaly:
            if current_temp < lower_bound:
                message = f"Температура аномально низкая! Отклонение: {deviation:.1f}°C от нормы"
            else:
                message = f"Температура аномально высокая! Отклонение: {deviation:.1f}°C от нормы"
        else:
            message = f"Температура в пределах нормы. Отклонение: {deviation:.1f}°C от среднего"
        
        return {
            'is_anomaly': is_anomaly,
            'message': message,
            'norms': seasonal_norms,
            'current_temp': current_temp,
            'deviation': deviation
        }
    
    def get_city_statistics(self, city: str) -> dict:
        """получение статистики по городу"""
        city_data = self.historical_data[self.historical_data['city'] == city]
        
        if len(city_data) == 0:
            return None
        
        return {
            'total_records': len(city_data),
            'mean_temperature': city_data['temperature'].mean(),
            'min_temperature': city_data['temperature'].min(),
            'max_temperature': city_data['temperature'].max(),
            'std_temperature': city_data['temperature'].std(),
            'date_range': {
                'start': city_data['timestamp'].min().strftime('%Y-%m-%d'),
                'end': city_data['timestamp'].max().strftime('%Y-%m-%d')
            }
        }

def analyze_city_data(city_data):
    """анализ данных для одного города"""
    city_data = city_data.sort_values('timestamp')
    
    # скользящее среднее и стандартное отклонение
    city_data['rolling_mean'] = city_data['temperature'].rolling(window=30, center=True).mean()
    city_data['rolling_std'] = city_data['temperature'].rolling(window=30, center=True).std()
    
    # определение аномалий
    city_data['is_anomaly'] = np.abs(city_data['temperature'] - city_data['rolling_mean']) > 2 * city_data['rolling_std']
    
    # средняя температура и стандартное отклонение по сезонам
    seasonal_stats = city_data.groupby('season').agg({
        'temperature': ['mean', 'std', 'min', 'max']
    }).round(2)
    
    # долгосрочный тренд
    city_data['year'] = city_data['timestamp'].dt.year
    yearly_trend = city_data.groupby('year')['temperature'].mean().reset_index()
    
    return {
        'city_name': city_data['city'].iloc[0],
        'data': city_data,
        'seasonal_stats': seasonal_stats,
        'yearly_trend': yearly_trend,
        'anomalies_count': city_data['is_anomaly'].sum(),
        'total_points': len(city_data)
    }

def get_current_weather(api_key: str, city: str):
    """получение текущей погоды через OpenWeatherMap API"""
    BASE_URL = "http://api.openweathermap.org/data/2.5/weather"
    
    params = {
        'q': city,
        'appid': api_key,
        'units': 'metric',
        'lang': 'ru'
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'data': {
                    'city': city,
                    'temperature': data['main']['temp'],
                    'feels_like': data['main']['feels_like'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'description': data['weather'][0]['description'],
                    'wind_speed': data['wind']['speed'] if 'wind' in data else 0,
                    'timestamp': datetime.now()
                }
            }
        elif response.status_code == 401:
            return {
                'success': False,
                'error': 'Неверный API ключ. Пожалуйста, проверьте ваш ключ.'
            }
        else:
            return {
                'success': False,
                'error': f'Ошибка API: {response.status_code}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Ошибка соединения: {str(e)}'
        }

def create_temperature_plot(city_data, city_name):
    """создание графика температуры"""
    fig = go.Figure()
    
    # нормальные данные
    normal_data = city_data[~city_data['is_anomaly']]
    fig.add_trace(go.Scatter(
        x=normal_data['timestamp'],
        y=normal_data['temperature'],
        mode='lines',
        name='Нормальная температура',
        line=dict(color='blue', width=1)
    ))
    
    # аномалии
    anomaly_data = city_data[city_data['is_anomaly']]
    if len(anomaly_data) > 0:
        fig.add_trace(go.Scatter(
            x=anomaly_data['timestamp'],
            y=anomaly_data['temperature'],
            mode='markers',
            name='Аномалии',
            marker=dict(color='red', size=8, symbol='circle')
        ))
    
    # скользящее среднее
    fig.add_trace(go.Scatter(
        x=city_data['timestamp'],
        y=city_data['rolling_mean'],
        mode='lines',
        name='Скользящее среднее (30 дней)',
        line=dict(color='green', width=2)
    ))
    
    fig.update_layout(
        title=f'Температура в {city_name} с аномалиями',
        xaxis_title='Дата',
        yaxis_title='Температура (°C)',
        hovermode='x unified',
        height=500
    )
    
    return fig

def create_seasonal_profile(seasonal_stats, city_name):
    """создание сезонного профиля"""
    seasons = ['winter', 'spring', 'summer', 'autumn']
    
    # Проверяем, есть ли данные для всех сезонов
    available_seasons = [s for s in seasons if s in seasonal_stats.index]
    
    if not available_seasons:
        return None
    
    means = [seasonal_stats.loc[s, ('temperature', 'mean')] for s in available_seasons]
    stds = [seasonal_stats.loc[s, ('temperature', 'std')] for s in available_seasons]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=available_seasons,
        y=means,
        name='Средняя температура',
        error_y=dict(
            type='data',
            array=stds,
            visible=True
        )
    ))
    
    fig.update_layout(
        title=f'Сезонные профили температуры в {city_name}',
        xaxis_title='Сезон',
        yaxis_title='Температура (°C)',
        height=400
    )
    
    return fig

# сайдбар для загрузки данных
with st.sidebar:
    st.header("Загрузка данных")
    
    uploaded_file = st.file_uploader(
        "Загрузите файл temperature_data.csv",
        type=['csv'],
        help="Файл должен содержать колонки: city, timestamp, temperature"
    )
    
    if uploaded_file is not None:
        try:
            historical_data = pd.read_csv(uploaded_file)
            historical_data['timestamp'] = pd.to_datetime(historical_data['timestamp'])
            
            # инициализация анализатора
            st.session_state.temperature_analyzer = TemperatureAnalyzer(historical_data)
            
            # выполнение анализа для всех городов
            analysis_results = {}
            for city in historical_data['city'].unique():
                city_data = historical_data[historical_data['city'] == city].copy()
                analysis_results[city] = analyze_city_data(city_data)
            
            st.session_state.analysis_results = analysis_results
            
            st.success(f"Данные загружены! Городов: {len(analysis_results)}")
            
        except Exception as e:
            st.error(f"Ошибка при загрузке файла: {str(e)}")
    else:
        st.info("Пожалуйста, загрузите файл с историческими данными")
    
    st.markdown("---")
    st.header("API Настройки")
    
    api_key = st.text_input(
        "OpenWeatherMap API Key",
        type="password",
        help="Получите бесплатный ключ на openweathermap.org"
    )
    
    st.markdown("---")
    st.header("Информация")
    st.markdown("""
    Это приложение позволяет:
    1. Анализировать исторические температурные данные
    2. Выявлять температурные аномалии
    3. Сравнивать текущую температуру с историческими нормами
    4. Визуализировать результаты анализа
    
    **Города для тестирования:**
    - Берлин, Каир, Дубай - температура в норме
    - Пекин, Москва - аномальная температура
    """)

# основное содержимое
if st.session_state.analysis_results is not None:
    # выбор города
    cities = list(st.session_state.analysis_results.keys())
    selected_city = st.selectbox(
        "Выберите город для анализа",
        cities,
        help="Выберите город для отображения статистики и графиков"
    )
    
    if selected_city:
        city_results = st.session_state.analysis_results[selected_city]
        
        # две колонки для статистики
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader(f"Статистика по городу: {selected_city}")
            
            # базовая статистика
            stats = st.session_state.temperature_analyzer.get_city_statistics(selected_city)
            if stats:
                st.metric("Всего записей", f"{stats['total_records']:,}")
                st.metric("Средняя температура", f"{stats['mean_temperature']:.1f}°C")
                st.metric("Минимальная температура", f"{stats['min_temperature']:.1f}°C")
                st.metric("Максимальная температура", f"{stats['max_temperature']:.1f}°C")
                st.metric("Стандартное отклонение", f"{stats['std_temperature']:.1f}°C")
                
                st.info(f"**Период данных:** {stats['date_range']['start']} - {stats['date_range']['end']}")
        
        with col2:
            st.subheader("Статистика аномалий")
            
            anomalies_count = city_results['anomalies_count']
            total_points = city_results['total_points']
            anomaly_percentage = (anomalies_count / total_points * 100) if total_points > 0 else 0
            
            st.metric("Обнаружено аномалий", f"{anomalies_count}")
            st.metric("Всего точек данных", f"{total_points}")
            st.metric("Процент аномалий", f"{anomaly_percentage:.2f}%")
            
            # визуализация процента аномалий
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=anomaly_percentage,
                title={'text': "Процент аномалий"},
                domain={'x': [0, 1], 'y': [0, 1]},
                gauge={
                    'axis': {'range': [0, 10]},
                    'bar': {'color': "red"},
                    'steps': [
                        {'range': [0, 2], 'color': "green"},
                        {'range': [2, 5], 'color': "yellow"},
                        {'range': [5, 10], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "black", 'width': 4},
                        'thickness': 0.75,
                        'value': anomaly_percentage
                    }
                }
            ))
            
            fig_gauge.update_layout(height=250)
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        st.markdown("---")
        
        # вкладки для разных визуализаций
        tab1, tab2, tab3, tab4 = st.tabs([
            "Временной ряд",
            "Сезонные профили",
            "Долгосрочный тренд",
            "Детальный анализ"
        ])
        
        with tab1:
            st.subheader(f"Температурный ряд: {selected_city}")
            
            # создание графика температуры
            fig_temp = create_temperature_plot(city_results['data'], selected_city)
            st.plotly_chart(fig_temp, use_container_width=True)
            
            # легенда аномалий
            st.markdown("""
            **Обозначения на графике:**
            - **Синяя линия** - дневная температура
            - **Красные точки** - температурные аномалии
            - **Зеленая линия** - скользящее среднее (30 дней)
            """)
        
        with tab2:
            st.subheader(f"Сезонные профили: {selected_city}")
            
            # создание сезонного профиля
            fig_seasonal = create_seasonal_profile(city_results['seasonal_stats'], selected_city)
            
            if fig_seasonal:
                st.plotly_chart(fig_seasonal, use_container_width=True)
                
                # таблица сезонных статистик
                st.subheader("Сезонная статистика")
                seasonal_df = city_results['seasonal_stats'].copy()
                seasonal_df.columns = ['Средняя', 'Стд. отклонение', 'Минимум', 'Максимум']
                st.dataframe(seasonal_df.style.format("{:.1f}"), use_container_width=True)
            else:
                st.warning("Нет данных для создания сезонного профиля")
        
        with tab3:
            st.subheader(f"Долгосрочный тренд: {selected_city}")
            
            # график тренда
            yearly_trend = city_results['yearly_trend']
            
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=yearly_trend['year'],
                y=yearly_trend['temperature'],
                mode='lines+markers',
                name='Среднегодовая температура',
                line=dict(color='orange', width=3)
            ))
            
            # линейный тренд
            if len(yearly_trend) > 1:
                z = np.polyfit(yearly_trend['year'], yearly_trend['temperature'], 1)
                p = np.poly1d(z)
                fig_trend.add_trace(go.Scatter(
                    x=yearly_trend['year'],
                    y=p(yearly_trend['year']),
                    mode='lines',
                    name='Линейный тренд',
                    line=dict(color='red', width=2, dash='dash')
                ))
                
                # расчет изменения температуры за период
                temp_change = yearly_trend['temperature'].iloc[-1] - yearly_trend['temperature'].iloc[0]
                years_span = yearly_trend['year'].iloc[-1] - yearly_trend['year'].iloc[0]
                yearly_change = temp_change / years_span if years_span > 0 else 0
                
                st.metric("Изменение за период", f"{temp_change:.2f}°C")
                st.metric("Среднегодовое изменение", f"{yearly_change:.2f}°C/год")
            
            fig_trend.update_layout(
                title='Долгосрочный тренд температуры',
                xaxis_title='Год',
                yaxis_title='Температура (°C)',
                height=500
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
        
        with tab4:
            st.subheader("Детальный анализ данных")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # распределение температур
                st.subheader("Распределение температур")
                
                fig_hist = go.Figure()
                fig_hist.add_trace(go.Histogram(
                    x=city_results['data']['temperature'],
                    nbinsx=50,
                    name='Температура',
                    marker_color='skyblue'
                ))
                
                fig_hist.update_layout(
                    title='Гистограмма распределения температур',
                    xaxis_title='Температура (°C)',
                    yaxis_title='Частота',
                    height=400
                )
                
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                # box plot по сезонам
                st.subheader("Box plot по сезонам")
                
                fig_box = go.Figure()
                
                seasons = ['winter', 'spring', 'summer', 'autumn']
                for season in seasons:
                    if season in city_results['seasonal_stats'].index:
                        season_data = city_results['data'][city_results['data']['season'] == season]['temperature']
                        fig_box.add_trace(go.Box(
                            y=season_data,
                            name=season.capitalize(),
                            boxpoints='outliers'
                        ))
                
                fig_box.update_layout(
                    title='Распределение температур по сезонам',
                    yaxis_title='Температура (°C)',
                    height=400
                )
                
                st.plotly_chart(fig_box, use_container_width=True)
            
            # показать первые аномалии
            st.subheader("Примеры обнаруженных аномалий")
            
            anomaly_data = city_results['data'][city_results['data']['is_anomaly']]
            if len(anomaly_data) > 0:
                display_anomalies = anomaly_data[['timestamp', 'temperature', 'rolling_mean']].head(10)
                display_anomalies['timestamp'] = display_anomalies['timestamp'].dt.strftime('%Y-%m-%d')
                display_anomalies['Отклонение'] = (display_anomalies['temperature'] - display_anomalies['rolling_mean']).round(2)
                display_anomalies.columns = ['Дата', 'Температура (°C)', 'Скользящее среднее', 'Отклонение (°C)']
                
                st.dataframe(display_anomalies, use_container_width=True)
            else:
                st.info("Аномалии не обнаружены")
        
        st.markdown("---")
        
        # раздел текущей погоды
        st.header("Текущая погода")
        
        if api_key:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                # кнопка для получения текущей погоды
                if st.button("🔄 Получить текущую погоду", use_container_width=True):
                    with st.spinner("Получаем данные о текущей погоде..."):
                        weather_result = get_current_weather(api_key, selected_city)
                        
                        if weather_result['success']:
                            weather_data = weather_result['data']
                            
                            # проверяем аномальность температуры
                            anomaly_check = st.session_state.temperature_analyzer.check_temperature_anomaly(
                                selected_city, 
                                weather_data['temperature']
                            )
                            
                            # отображаем результаты
                            st.success("✅ Данные о погоде получены!")
                            
                            # показываем текущую погоду
                            col_temp, col_feels, col_hum = st.columns(3)
                            
                            with col_temp:
                                st.metric(
                                    "Текущая температура", 
                                    f"{weather_data['temperature']:.1f}°C",
                                    delta=f"{anomaly_check['deviation']:.1f}°C от нормы"
                                )
                            
                            with col_feels:
                                st.metric(
                                    "Ощущается как", 
                                    f"{weather_data['feels_like']:.1f}°C"
                                )
                            
                            with col_hum:
                                st.metric(
                                    "Влажность", 
                                    f"{weather_data['humidity']}%"
                                )
                            
                            # статус аномальности
                            st.subheader("Статус температуры")
                            
                            if anomaly_check['is_anomaly'] is None:
                                st.warning(anomaly_check['message'])
                            elif anomaly_check['is_anomaly']:
                                st.error(f"{anomaly_check['message']}")
                            else:
                                st.success(f"{anomaly_check['message']}")
                            
                            # дополнительная информация
                            st.subheader("Дополнительная информация")
                            
                            col_desc, col_wind, col_press = st.columns(3)
                            
                            with col_desc:
                                st.markdown(f"**Описание:** {weather_data['description']}")
                            
                            with col_wind:
                                st.markdown(f"**Скорость ветра:** {weather_data['wind_speed']} м/с")
                            
                            with col_press:
                                st.markdown(f"**Давление:** {weather_data['pressure']} hPa")
                            
                            # визуализация относительно норм
                            if anomaly_check['norms']:
                                st.subheader("Сравнение с историческими нормами")
                                
                                norms = anomaly_check['norms']
                                current_temp = weather_data['temperature']
                                
                                fig_comparison = go.Figure()
                                
                                # диапазон нормы
                                fig_comparison.add_trace(go.Bar(
                                    x=['Диапазон нормы'],
                                    y=[norms['upper_bound'] - norms['lower_bound']],
                                    base=norms['lower_bound'],
                                    name='Нормальный диапазон (±2σ)',
                                    marker_color='lightgreen',
                                    opacity=0.5
                                ))
                                
                                # средняя температура
                                fig_comparison.add_trace(go.Scatter(
                                    x=['Средняя'],
                                    y=[norms['mean']],
                                    mode='markers',
                                    name=f'Средняя ({norms["mean"]:.1f}°C)',
                                    marker=dict(color='blue', size=15)
                                ))
                                
                                # текущая температура
                                fig_comparison.add_trace(go.Scatter(
                                    x=['Текущая'],
                                    y=[current_temp],
                                    mode='markers',
                                    name=f'Текущая ({current_temp:.1f}°C)',
                                    marker=dict(color='red', size=20, symbol='star')
                                ))
                                
                                # границы
                                fig_comparison.add_trace(go.Scatter(
                                    x=['Верхняя граница'],
                                    y=[norms['upper_bound']],
                                    mode='markers',
                                    name=f'Верхняя граница ({norms["upper_bound"]:.1f}°C)',
                                    marker=dict(color='gray', size=10, symbol='line-ns')
                                ))
                                
                                fig_comparison.add_trace(go.Scatter(
                                    x=['Нижняя граница'],
                                    y=[norms['lower_bound']],
                                    mode='markers',
                                    name=f'Нижняя граница ({norms["lower_bound"]:.1f}°C)',
                                    marker=dict(color='gray', size=10, symbol='line-ns')
                                ))
                                
                                fig_comparison.update_layout(
                                    title=f'Сравнение с сезонными нормами ({norms["season"]})',
                                    yaxis_title='Температура (°C)',
                                    height=400,
                                    showlegend=True
                                )
                                
                                st.plotly_chart(fig_comparison, use_container_width=True)
                                
                                # статистика по нормам
                                st.info(f"""
                                **Сезонные нормы для {selected_city}:**
                                - **Сезон:** {norms['season']}
                                - **Средняя температура:** {norms['mean']:.1f}°C
                                - **Стандартное отклонение:** {norms['std']:.1f}°C
                                - **Нормальный диапазон:** {norms['lower_bound']:.1f}°C - {norms['upper_bound']:.1f}°C
                                - **На основе:** {norms['sample_size']:,} исторических измерений
                                """)
                            
                            st.markdown(f"*Последнее обновление: {weather_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}*")
                            
                        else:
                            st.error(f"Ошибка при получении данных: {weather_result['error']}")
                
                else:
                    st.info("Нажмите кнопку выше, чтобы получить текущую погоду")
            
            with col2:
                st.markdown("### Тестовые города")
                st.markdown("""
                Для тестирования:
                - **Берлин, Каир, Дубай** - нормальная температура
                - **Пекин, Москва** - аномальная температура
                """)
            
            with col3:
                st.markdown("### API Статус")
                st.success("API ключ введен")
        
        else:
            st.warning("Для получения текущей погоды введите API ключ в боковой панели")
    
    else:
        st.info("Выберите город из списка")
    
    st.markdown("---")
    
    # раздел сравнения городов
    st.header("Сравнение городов")
    
    selected_cities = st.multiselect(
        "Выберите города для сравнения",
        cities,
        default=cities[:3],
        help="Выберите до 5 городов для сравнения"
    )
    
    if len(selected_cities) > 0:
        # DataFrame для сравнения
        comparison_data = []
        for city in selected_cities[:5]:  # 5 городов
            if city in st.session_state.analysis_results:
                city_stats = st.session_state.temperature_analyzer.get_city_statistics(city)
                if city_stats:
                    comparison_data.append({
                        'Город': city,
                        'Средняя темп.': city_stats['mean_temperature'],
                        'Мин. темп.': city_stats['min_temperature'],
                        'Макс. темп.': city_stats['max_temperature'],
                        'Стд. отклонение': city_stats['std_temperature'],
                        'Записей': city_stats['total_records']
                    })
        
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            
            # отображение таблицы
            st.subheader("Сравнительная таблица")
            st.dataframe(
                comparison_df.style.format({
                    'Средняя темп.': '{:.1f}°C',
                    'Мин. темп.': '{:.1f}°C',
                    'Макс. темп.': '{:.1f}°C',
                    'Стд. отклонение': '{:.1f}°C'
                }),
                use_container_width=True
            )
            
            # график сравнения средних температур
            st.subheader("Сравнение средних температур")
            
            fig_comparison = go.Figure()
            
            for idx, row in comparison_df.iterrows():
                fig_comparison.add_trace(go.Bar(
                    x=[row['Город']],
                    y=[row['Средняя темп.']],
                    name=row['Город'],
                    text=f"{row['Средняя темп.']:.1f}°C",
                    textposition='auto'
                ))
            
            fig_comparison.update_layout(
                title='Сравнение средних температур по городам',
                yaxis_title='Температура (°C)',
                height=400
            )
            
            st.plotly_chart(fig_comparison, use_container_width=True)

else:
    # если данные не загружены, будут показаны инструкции
    st.info("Загрузите файл с историческими данными в боковой панели")
    
    # пример данных
    st.subheader("Пример ожидаемой структуры данных")
    
    example_data = pd.DataFrame({
        'city': ['Moscow', 'Moscow', 'Berlin', 'Berlin'],
        'timestamp': ['2020-01-01', '2020-01-02', '2020-01-01', '2020-01-02'],
        'temperature': [-5.3, -4.8, 2.1, 1.9],
        'season': ['winter', 'winter', 'winter', 'winter']
    })
    
    st.dataframe(example_data, use_container_width=True)
    
    st.markdown("""
    **Требования к файлу:**
    1. Формат: CSV
    2. Колонки: `city`, `timestamp`, `temperature` (обязательные)
    3. Дополнительно: может содержать колонку `season`
    4. Кодировка: UTF-8
    
    **Пример генерации данных:**
    ```python
    # код для генерации тестовых данных находится в начале ноутбука
    # файл temperature_data.csv будет сгенерирован автоматически
    ```
    """)

# футер приложения
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Анализ температурных данных | Домашнее задание по ИИ</p>
    <p><small>Использует исторические данные и OpenWeatherMap API</small></p>
</div>
""", unsafe_allow_html=True)
