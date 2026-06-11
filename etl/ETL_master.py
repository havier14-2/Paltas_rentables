import os
import sqlite3
import logging
import pandas as pd
from datetime import timedelta

# ---------------------------------------------------------
# 1. CONFIGURACIÓN PROFESIONAL
# ---------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("ETL_Master_Transformer")

def unificar_y_transformar():
    logger.info("Iniciando Fase de Transformación y Carga (T & L)...")

    # ---------------------------------------------------------
    # 2. EXTRACCIÓN LOCAL (Lectura de las 3 Fuentes)
    # ---------------------------------------------------------
    ruta_odepa = os.path.join("data", "raw_odepa_paltas.csv")
    ruta_clima = os.path.join("data", "historical_weather.csv")
    ruta_db = os.path.join("data", "paltas_retail.db")

    if not all(os.path.exists(p) for p in [ruta_odepa, ruta_clima, ruta_db]):
        logger.error("Faltan archivos base en la carpeta /data/. Ejecuta los scripts anteriores primero.")
        return

    # Leer CSVs limpios
    df_precios = pd.read_csv(ruta_odepa)
    df_clima = pd.read_csv(ruta_clima) # Lee directo porque ETL_clima.py ya lo limpió en la fase anterior

    # Leer SQL (Reglas de Negocio)
    conexion = sqlite3.connect(ruta_db)
    df_reglas = pd.read_sql_query("SELECT * FROM reglas_fenologicas", conexion)
    conexion.close()

    # ---------------------------------------------------------
    # 3. TRANSFORMACIÓN: LA LÓGICA DE REZAGO (LAG FEATURES)
    # ---------------------------------------------------------
    logger.info("Aplicando lógica de rezago agrícola (8 meses)...")
    
    # Asegurar que las fechas sean objetos de tipo DateTime
    df_precios['fecha'] = pd.to_datetime(df_precios['fecha'])
    df_clima['fecha_clima'] = pd.to_datetime(df_clima['fecha_clima'])

    # Calcular la "fecha de impacto" de ese clima (8 meses en el futuro = aprox 240 días)
    # Si heló hoy, el mercado lo sentirá en 240 días.
    df_clima['fecha_impacto_mercado'] = df_clima['fecha_clima'] + timedelta(days=240)
    
    # Redondeamos al mes para facilitar el cruce (evaluamos el impacto mensual)
    df_clima['mes_anio_impacto'] = df_clima['fecha_impacto_mercado'].dt.to_period('M')
    df_precios['mes_anio'] = df_precios['fecha'].dt.to_period('M')

    # ---------------------------------------------------------
    # 4. EL CRUCE MAESTRO (JOIN)
    # ---------------------------------------------------------
    # Agrupamos el clima de todas las zonas productoras para ese mes rezagado
    clima_agrupado = df_clima.groupby('mes_anio_impacto').agg({
        'temp_min': 'min',  # Buscamos la temperatura más fría registrada
        'temp_max': 'max',  # Buscamos la temperatura más cálida registrada
        'lluvia_mm': 'sum'  # Sumamos toda la lluvia de ese mes
    }).reset_index()

    # Unimos el precio de la palta con el clima que hubo hace 8 meses
    df_master = pd.merge(
        df_precios, 
        clima_agrupado, 
        left_on='mes_anio', 
        right_on='mes_anio_impacto', 
        how='left'
    )

    # ---------------------------------------------------------
    # 5. CREACIÓN DE ALERTAS DE NEGOCIO (Ingeniería de Características)
    # ---------------------------------------------------------
    # Extraemos el límite crítico de la base de datos SQL
    limite_helada = df_reglas.loc[df_reglas['fase_planta'].str.contains('Floración', case=False, na=False), 'temp_minima_critica'].values
    limite = limite_helada[0] if len(limite_helada) > 0 else 2.0

    # Creamos un Flag (1 o 0) si hubo helada hace 8 meses
    df_master['alerta_helada_previa'] = df_master['temp_min'].apply(lambda x: 1 if x <= limite else 0)

    # Limpieza final de columnas auxiliares
    df_master = df_master.drop(columns=['mes_anio', 'mes_anio_impacto'])

    # ---------------------------------------------------------
    # 6. CARGA FINAL
    # ---------------------------------------------------------
    ruta_salida = os.path.join("data", "master_dataset.csv")
    df_master.to_csv(ruta_salida, index=False, encoding="utf-8")
    
    logger.info(f"Pipeline ETL completado. Tabla maestra generada en: {ruta_salida}")
    logger.info(f"Total de registros unificados: {len(df_master)}")

if __name__ == "__main__":
    unificar_y_transformar()