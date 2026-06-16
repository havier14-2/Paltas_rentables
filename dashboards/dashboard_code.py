import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# 1. Configuración de la interfaz
st.set_page_config(
    page_title="Palta Inteligente: Dashboard SQL",
    page_icon="🥑",
    layout="wide"
)

st.title("🥑 Palta Inteligente: Dashboard Corporativo (SQL)")
st.markdown("Análisis dinámico conectando Streamlit directly a la base de datos de destino limpio SQLite.")

ruta_db = "data/paltas_retail.db"
ruta_master = "data/master_dataset.csv" # Usamos el master temporalmente para el merge si no se cargó en SQL

# Función para extraer los datos combinados directamente con SQL o Pandas
@st.cache_data
def cargar_datos_desde_origen():
    if not os.path.exists(ruta_master):
        return None
    # Cargamos el dataset limpio y unificado que preparó el ETL
    df = pd.read_csv(ruta_master)
    df['fecha'] = pd.to_datetime(df['fecha'])
    return df

df_base = cargar_datos_desde_origen()

if df_base is None:
    st.error(f"Error: No se detectan los datos limpios de destino. Ejecuta el pipeline ETL completo primero.")
else:
    
    # 2. CONTROLES Y FILTROS REQUERIDOS (En la Barra Lateral)
    
    st.sidebar.header("Filtros Dinámicos (Tiempo Real)")
    
    # Perfil de Audiencia
    perfil = st.sidebar.selectbox(
        "Audiencia / Vista:",
        ["Ejecutivo de Retail", "Productor Agrícola"]
    )
    st.sidebar.markdown("---")

    # FILTRO 1: Regiones (Traídas desde la tabla geográfica del SQL)
    conexion = sqlite3.connect(ruta_db)
    regiones_sql = pd.read_sql_query("SELECT nombre_region FROM dim_geografia_agricola", conexion)
    conexion.close()
    
    lista_regiones = list(regiones_sql['nombre_region'].unique())
    # Añadimos la opción de ver todas las regiones juntas
    region_sel = st.sidebar.selectbox("Filtrar por Región de Origen:", ["TODAS"] + lista_regiones)

    # FILTRO 2: Categorías / Mercados Mayoristas
    lista_mercados = list(df_base['mercado'].unique())
    mercado_sel = st.sidebar.selectbox("Filtrar por Categoría / Mercado:", ["TODOS"] + lista_mercados)

    # FILTRO 3: Rango de Fechas
    fecha_min = df_base['fecha'].min().to_pydatetime()
    fecha_max = df_base['fecha'].max().to_pydatetime()
    rango_fechas = st.sidebar.date_input(
        "Filtrar por Rango de Fechas:",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max
    )

    
    # 3. APLICACIÓN EN TIEMPO REAL DE LOS FILTROS (Pandas Query)
    
    df_filtrado = df_base.copy()

    # Aplicar filtro de Región (Si no es TODAS, filtramos)
    if region_sel != "TODAS":
        df_filtrado = df_filtrado[df_filtrado['region'] == region_sel]

    # Aplicar filtro de Mercado
    if mercado_sel != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['mercado'] == mercado_sel]

    # Aplicar filtro de Fechas (Controlando que el usuario haya seleccionado inicio y fin)
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
        inicio, fin = pd.to_datetime(rango_fechas[0]), pd.to_datetime(rango_fechas[1])
        df_filtrado = df_filtrado[(df_filtrado['fecha'] >= inicio) & (df_filtrado['fecha'] <= fin)]

    
    # 4. RENDERIZADO DE VISUALIZACIONES SEGÚN AUDIENCIA
        
    if df_filtrado.empty:
        st.warning("No hay registros que coincidan con la combinación de filtros seleccionada.")
    else:
        # VISTA EJECUTIVO DE RETAIL
        if perfil == "Ejecutivo de Retail":
            st.subheader(f"Análisis Financiero Comercial — Región: {region_sel}")
            
            # KPIs Dinámicos
            col1, col2, col3 = st.columns(3)
            col1.metric("Precio Promedio", f"${int(df_filtrado['precio_promedio'].mean())} /kg")
            col2.metric("Precio Máximo", f"${int(df_filtrado['precio_maximo'].max())} /kg")
            col3.metric("Total Registros Filtrados", f"{df_filtrado.shape[0]} días")

            st.markdown("---")

            # Gráfico interactivo Plotly (Línea de tiempo)
            fig_lineas = px.line(
                df_filtrado.sort_values('fecha'),
                x='fecha',
                y='precio_promedio',
                color='mercado' if mercado_sel == "TODOS" else None,
                title="Tendencia de Precios Mayoristas en el Tiempo Seleccionado",
                labels={'precio_promedio': 'Precio Promedio ($/kg)', 'fecha': 'Fecha', 'mercado': 'Mercado'},
                template="plotly_white"
            )
            st.plotly_chart(fig_lineas, use_container_width=True)

        # VISTA PRODUCTOR AGRÍCOLA
        else:
            st.subheader(f"Análisis de Riesgo Agrometeorológico — Región: {region_sel}")
            
            # KPIs Dinámicos Climáticos
            col1, col2, col3 = st.columns(3)
            col1.metric("Meses con Alerta de Helada", f"{int(df_filtrado['alerta_helada_previa'].sum())} meses")
            col2.metric("Lluvia Acumulada Periodo", f"{round(df_filtrado['lluvia_mm'].sum(), 1)} mm")
            col3.metric("Temp Mínima Extrema", f"{df_filtrado['temp_min'].min()} °C")

            st.markdown("---")

            # Gráfico interactivo Plotly (Dispersión / Correlación)
            fig_scatter = px.scatter(
                df_filtrado,
                x='temp_min',
                y='precio_promedio',
                color='alerta_helada_previa',
                size='lluvia_mm',
                title="Impacto del Clima Rezagado (Hace 8 Meses) sobre el Precio Actual",
                labels={'temp_min': 'Temperatura Mínima Rezagada (°C)', 'precio_promedio': 'Precio de Venta ($/kg)', 'alerta_helada_previa': '¿Hubo Helada?'},
                color_continuous_scale=["#2ECC71", "#E74C3C"],
                template="plotly_white"
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

# streamlit run dashboards/dashboard_code.py