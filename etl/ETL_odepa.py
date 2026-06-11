import os
import logging
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
        cleaned = {}
        for key, val in values.items():
            new_key = key.lower().strip().replace(" ", "_").replace("á", "a").replace("í", "i")
            if new_key == "_id":
                new_key = "id_registro"

            if isinstance(val, str) and "precio" in new_key:
                try:
                    val = float(val.replace(".", "").replace(",", ".").strip())
                except ValueError:
                    pass
            cleaned[new_key] = val
        return cleaned

# 3. PIPELINE DE EXTRACCIÓN Y PROCESAMIENTO
def ejecutar_etl_odepa(limit: int = 5000) -> None:
    resource_id = os.getenv("ODEPA_RESOURCE_ID")
    if not resource_id:
        logger.error("Falta la variable de entorno ODEPA_RESOURCE_ID en el archivo .env")
        return

    url = "https://datos.odepa.gob.cl/api/3/action/datastore_search"
    
    # ELIMINAMOS LA "q". Traemos 5000 registros de golpe para filtrarlos nosotros.
    params = {"resource_id": resource_id, "limit": limit}

    logger.info("Iniciando extracción masiva desde la API RESTful de ODEPA...")
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        json_data = response.json()
        
        if not json_data.get("success"):
            logger.error("La API de ODEPA rechazó la consulta interna.")
            return

        records = json_data["result"]["records"]
        logger.info(f"Se extrajeron {len(records)} registros crudos de todo tipo de productos.")

        # Validación Pydantic
        registros_validos = []
        for r in records:
            try:
                item_validado = RegistroOdepaSchema(**r)
                registros_validos.append(item_validado.model_dump())
            except ValidationError:
                pass # Ignoramos silenciosamente lo que venga mal formateado

        if not registros_validos:
            logger.error("El proceso de validación terminó con 0 registros útiles.")
            return

        # Convertir a DataFrame
        df = pd.DataFrame(registros_validos)
        
        # ------------------------------------------------------------------
        # EL FILTRO MAESTRO PANDAS (Case Insensitive)
        # ------------------------------------------------------------------
        logger.info("Filtrando localmente solo los registros de Palta...")
        df_palta = df[df['producto'].str.contains('palta', case=False, na=False)]
        
        if df_palta.empty:
            logger.warning("No se encontraron registros de palta en la muestra extraída.")
            return

        # Guardar
        os.makedirs("data", exist_ok=True)
        ruta_salida = os.path.join("data", "raw_odepa_paltas.csv")
        df_palta.to_csv(ruta_salida, index=False, encoding="utf-8")
        
        logger.info(f"¡Éxito! Se guardaron {len(df_palta)} registros de Palta en: {ruta_salida}")

    except Exception as e:
        logger.critical(f"Error inesperado en el pipeline: {e}")

if __name__ == "__main__":
    logger.info("--- INICIANDO EXTRACCIÓN ODEPA ---")
    ejecutar_etl_odepa(limit=10000)