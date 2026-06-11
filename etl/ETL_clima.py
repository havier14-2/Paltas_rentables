import os
import requests
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger("ETL_Clima_Historico")

def generar_csv_clima():
    logger.info("Iniciando descarga masiva de clima histórico...")
    
    # Coordenadas exactas que tenemos en la base de datos SQL
    ubicaciones = [
        {"region": "VALPARAISO", "lat": -32.25, "lon": -70.93},
        {"region": "METROPOLITANA DE SANTIAGO", "lat": -33.45, "lon": -70.66},
        {"region": "LIBERTADOR GENERAL BERNARDO O'HIGGINS", "lat": -34.39, "lon": -71.17}
    ]

    # Preparamos las listas separadas por comas para la API
    lats = ",".join([str(u["lat"]) for u in ubicaciones])
    lons = ",".join([str(u["lon"]) for u in ubicaciones])

    url = "https://archive-api.open-meteo.com/v1/archive"
    parametros = {
        "latitude": lats,
        "longitude": lons,
        "start_date": "2023-01-01",
        "end_date": "2026-06-11",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "America/Santiago"
    }

    try:
        respuesta = requests.get(url, params=parametros, timeout=20)
        respuesta.raise_for_status()
        datos_json = respuesta.json()
        
        registros_limpios = []
        
        # Iteramos sobre la respuesta (una por cada región)
        for index, data_ubicacion in enumerate(datos_json):
            nombre_region = ubicaciones[index]["region"]
            historial_diario = data_ubicacion["daily"]
            
            # Desarmamos las listas de fechas, temperaturas y lluvias
            for i in range(len(historial_diario["time"])):
                registros_limpios.append({
                    "fecha_clima": historial_diario["time"][i],
                    "region": nombre_region,
                    "temp_max": historial_diario["temperature_2m_max"][i],
                    "temp_min": historial_diario["temperature_2m_min"][i],
                    "lluvia_mm": historial_diario["precipitation_sum"][i]
                })

        # Convertimos a Pandas DataFrame
        df_clima = pd.DataFrame(registros_limpios)
        
        # Eliminamos días que por error de servidor vengan sin datos
        df_clima = df_clima.dropna()

        # Guardamos el CSV perfecto en la carpeta data
        os.makedirs("data", exist_ok=True)
        ruta_salida = os.path.join("data", "historical_weather.csv")
        df_clima.to_csv(ruta_salida, index=False, encoding="utf-8")
        
        logger.info(f"¡Éxito! CSV de clima generado perfectamente en: {ruta_salida}")
        print(df_clima.head())

    except Exception as e:
        logger.error(f"Error extrayendo datos climáticos: {e}")

if __name__ == "__main__":
    generar_csv_clima()