import os
import logging
from datetime import datetime
import requests
import pandas as pd
from pydantic import BaseModel, ValidationError, model_validator
from dotenv import load_dotenv

# 1. CONFIGURACIÓN DE LOGGING PROFESIONAL
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
)
logger = logging.getLogger("Pipeline_ETL_ODEPA")

load_dotenv()

# 2. ESQUEMA DE VALIDACIÓN Y TRANSFORMACIÓN EN VUELO
class RegistroOdepaSchema(BaseModel):
    id_registro: int
    fecha: str
    producto: str
    mercado: str
    precio_minimo: float
    precio_maximo: float
    precio_promedio: float

    @model_validator(mode='before')
    @classmethod
    def normalizar_y_limpiar(cls, values: dict):
        """
        Transformación Robusta: Limpia mayúsculas, espacios, caracteres especiales 
        y corrige el formato decimal chileno (coma a punto) de forma dinámica.
        """
        cleaned = {}
        for key, val in values.items():
            # Traducir llaves del gobierno a snake_case limpio
            new_key = key.lower().strip().replace(" ", "_").replace("á", "a").replace("í", "i")
            if new_key == "_id":
                new_key = "id_registro"

            # Transformar strings numéricos con comas a flotantes válidos
            if isinstance(val, str) and "precio" in new_key:
                try:
                    val = val.replace(".", "").replace(",", ".").strip()
                except Exception:
                    pass
            cleaned[new_key] = val
        return cleaned

# 3. PIPELINE DE EXTRACCIÓN Y PROCESAMIENTO
def ejecutar_etl_odepa(limit: int = 1000) -> None:
    resource_id = os.getenv("ODEPA_RESOURCE_ID")
    if not resource_id:
        logger.error("Falta la variable de entorno ODEPA_RESOURCE_ID en el archivo .env")
        return

    url = "https://datos.odepa.gob.cl/api/3/action/datastore_search"
    # Filtrar directamente en el servidor de la API optimiza el uso de red y memoria
    params = {"resource_id": resource_id, "limit": limit, "q": "Palta Hass"}

    logger.info("Iniciando extracción desde la API RESTful de ODEPA...")
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        json_data = response.json()
        
        if not json_data.get("success"):
            logger.error("La API de ODEPA rechazó la consulta interna.")
            return

        records = json_data["result"]["records"]
        logger.info(f"Se extrajeron {len(records)} registros crudos.")

        # Validación de esquemas activa
        registros_validos = []
        for r in records:
            try:
                item_validado = RegistroOdepaSchema(**r)
                registros_validos.append(item_validado.model_dump())
            except ValidationError as e:
                logger.warning(f"Registro omitido por inconsistencia de esquema: {e.json()}")

        if not registros_validos:
            logger.error("El proceso de validación terminó con 0 registros útiles.")
            return

        # Convertir a DataFrame e Ingeniería de datos inicial
        df = pd.DataFrame(registros_validos)
        
        # Guardar en la estructura de carpetas oficial (/data/)
        os.makedirs("data", exist_ok=True)
        ruta_salida = os.path.join("data", "raw_odepa_paltas.csv")
        df.to_csv(ruta_salida, index=False, encoding="utf-8")
        
        logger.info(f"¡Fase ETL completada con éxito! Archivo guardado en: {ruta_salida}")
        print(df.head(3))

    except requests.exceptions.RequestException as error_red:
        logger.critical(f"Falla crítica de comunicación con la API: {error_red}")
    except Exception as e:
        logger.critical(f"Error inesperado en el pipeline: {e}")

if __name__ == "__main__":
    logger.info("--- INICIANDO ENTORNO DE DESARROLLO ---")
    ejecutar_etl_odepa(limit=100)