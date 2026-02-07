import math
from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title='Alerta de lluvia anómala',
    page_icon=':umbrella:',
)

st.title(':umbrella: Alerta de lluvia anómala')

st.markdown(
    'Conecta con la estación meteorológica más cercana (vía Open-Meteo) y avisa '
    'cuando la lluvia esperada sea mayor que lo normal para tu zona.'
)

with st.sidebar:
    st.header('Configuración')
    city_query = st.text_input('Ciudad o localidad', 'Ciudad de México')
    threshold_multiplier = st.slider(
        'Multiplicador sobre lo normal',
        min_value=1.1,
        max_value=3.0,
        value=1.5,
        step=0.1,
        help='Ejemplo: 1.5 significa 50% más lluvia que el promedio reciente.',
    )
    history_days = st.number_input(
        'Días para calcular lo normal',
        min_value=7,
        max_value=60,
        value=30,
        step=1,
    )
    phone_note = st.text_input('Número móvil (opcional)', '+52 55 1234 5678')


@st.cache_data(show_spinner=False)
def search_location(query: str) -> pd.DataFrame:
    response = requests.get(
        'https://geocoding-api.open-meteo.com/v1/search',
        params={
            'name': query,
            'count': 5,
            'language': 'es',
            'format': 'json',
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get('results', [])
    return pd.DataFrame(results)


@st.cache_data(show_spinner=False)
def get_forecast(lat: float, lon: float) -> pd.DataFrame:
    response = requests.get(
        'https://api.open-meteo.com/v1/forecast',
        params={
            'latitude': lat,
            'longitude': lon,
            'daily': 'precipitation_sum',
            'timezone': 'auto',
            'forecast_days': 3,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    daily = data.get('daily', {})
    return pd.DataFrame({
        'date': pd.to_datetime(daily.get('time', [])),
        'precipitation_sum': daily.get('precipitation_sum', []),
    })


@st.cache_data(show_spinner=False)
def get_historical(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    response = requests.get(
        'https://archive-api.open-meteo.com/v1/archive',
        params={
            'latitude': lat,
            'longitude': lon,
            'daily': 'precipitation_sum',
            'start_date': start.isoformat(),
            'end_date': end.isoformat(),
            'timezone': 'auto',
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    daily = data.get('daily', {})
    return pd.DataFrame({
        'date': pd.to_datetime(daily.get('time', [])),
        'precipitation_sum': daily.get('precipitation_sum', []),
    })


if city_query:
    with st.spinner('Buscando estaciones cercanas...'):
        locations_df = search_location(city_query)

    if locations_df.empty:
        st.warning('No encontramos resultados para esa ciudad. Prueba otra búsqueda.')
        st.stop()

    location_label = (
        locations_df['name']
        + ', '
        + locations_df['country']
        + locations_df['admin1'].fillna('')
    )
    selected_label = st.selectbox('Selecciona la ubicación', location_label)
    selected_row = locations_df[location_label == selected_label].iloc[0]

    latitude = float(selected_row['latitude'])
    longitude = float(selected_row['longitude'])

    st.subheader('Ubicación seleccionada')
    st.write(
        f"**{selected_row['name']}**, {selected_row.get('admin1', '')} "
        f"({selected_row['country']})"
    )
    st.caption('Fuente de datos: Open-Meteo (estación meteorológica más cercana).')

    today = date.today()
    end_date = today - timedelta(days=1)
    start_date = end_date - timedelta(days=int(history_days) - 1)

    with st.spinner('Cargando datos de precipitación...'):
        historical_df = get_historical(latitude, longitude, start_date, end_date)
        forecast_df = get_forecast(latitude, longitude)

    if historical_df.empty or forecast_df.empty:
        st.error('No pudimos obtener datos suficientes de lluvia para esta ubicación.')
        st.stop()

    normal_precip = historical_df['precipitation_sum'].mean()
    forecast_target = forecast_df.iloc[0]
    forecast_value = forecast_target['precipitation_sum']

    threshold_value = normal_precip * threshold_multiplier
    alert_triggered = forecast_value > threshold_value

    st.subheader('Resumen de alerta')
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric('Lluvia normal (promedio)', f"{normal_precip:.1f} mm")
    with col2:
        st.metric('Pronóstico próximo día', f"{forecast_value:.1f} mm")
    with col3:
        st.metric('Umbral de alerta', f"{threshold_value:.1f} mm")

    if alert_triggered:
        st.error(
            '⚠️ Se espera lluvia por encima de lo normal. '
            'Se enviaría una alerta al móvil configurado.'
        )
    else:
        st.success('✅ No se espera lluvia fuera de lo normal en las próximas 24 horas.')

    alert_message = (
        f"Alerta de lluvia para {selected_row['name']}: "
        f"{forecast_value:.1f} mm vs normal {normal_precip:.1f} mm."
    )

    with st.expander('Mensaje sugerido para tu servicio de alertas'):
        st.code(alert_message)
        st.caption(
            'Integra este mensaje con tu proveedor de notificaciones (Twilio, WhatsApp, SMS).'
        )

    st.subheader('Histórico y pronóstico')
    chart_df = pd.concat(
        [
            historical_df.assign(tipo='Histórico'),
            forecast_df.assign(tipo='Pronóstico'),
        ],
        ignore_index=True,
    )
    st.line_chart(chart_df, x='date', y='precipitation_sum', color='tipo')

    if phone_note:
        st.info(
            f"Número registrado: {phone_note}. "
            'Conecta tu proveedor SMS para enviar alertas reales.'
        )
else:
    st.info('Ingresa una ciudad para comenzar.')
