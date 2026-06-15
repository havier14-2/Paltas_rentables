import sqlite3
import os
import logging

from streamlit import cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("Setup_DB")

def inicializar_base_de_datos():
    # Creamos la base de datos dentro de la carpeta /data/ como exige la estructura
    os.makedirs("data", exist_ok=True)
    db_path = os.path.join("data", "paltas_retail.db")
    
    conexion = sqlite3.connect(db_path)
    cursor = conexion.cursor()
    
    logger.info(f"Creando base de datos relacional en: {db_path}")

    # 1. Tabla de Geografía Agrícola (Traductor API a CSV)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_geografia_agricola (
            id_region INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_region TEXT UNIQUE NOT NULL,
            latitud REAL NOT NULL,
            longitud REAL NOT NULL,
            hectareas_productivas INTEGER
        )
    ''')
    
    # Borramos la tabla vieja si existe para limpiar duplicados anteriores
    cursor.execute('DROP TABLE IF EXISTS reglas_fenologicas')

    # 2. Tabla de Reglas Fenológicas (Lógica de Rezagos del Clima)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reglas_fenologicas (
            id_regla INTEGER PRIMARY KEY AUTOINCREMENT,
            fase_planta TEXT NOT NULL,
            mes_clima INTEGER NOT NULL,
            temp_minima_critica REAL NOT NULL,
            mes_impacto_mercado INTEGER NOT NULL
        )
    ''')

    # 3. Tabla de Costos Operacionales de Retail
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS costos_operacionales (
            id_costo INTEGER PRIMARY KEY AUTOINCREMENT,
            anio INTEGER NOT NULL,
            costo_almacenamiento_diario_tonelada REAL NOT NULL,
            costo_flete_promedio REAL NOT NULL
        )
    ''')

    # POBLAR DATOS INICIALES (Data Seed)
    logger.info("Poblando tablas con parámetros de negocio...")
    
    # Regiones productoras clave coincidentes con ODEPA
    regiones = [
        ("VALPARAISO", -32.25, -70.93, 15000),
        ("METROPOLITANA DE SANTIAGO", -33.45, -70.66, 4000),
        ("LIBERTADOR GENERAL BERNARDO O'HIGGINS", -34.39, -71.17, 8000)
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO dim_geografia_agricola (nombre_region, latitud, longitud, hectareas_productivas)
        VALUES (?, ?, ?, ?)
    ''', regiones)

    # Regla: Si en Agosto (Floración = 8) hiela, el impacto se ve en Abril (Cosecha = 4)
    reglas = [
        ("Floración (Invierno)", 8, 2.0, 4),
        ("Desarrollo de Fruto", 11, 5.0, 5)
    ]
    cursor.executemany('''
        INSERT OR IGNORE INTO reglas_fenologicas (fase_planta, mes_clima, temp_minima_critica, mes_impacto_mercado)
        VALUES (?, ?, ?, ?)
    ''', reglas)

    conexion.commit()
    conexion.close()
    logger.info("¡Base de datos SQL inicializada con éxito!")

if __name__ == "__main__":
    inicializar_base_de_datos()