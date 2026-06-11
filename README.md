# 🥑 Palta Inteligente: Pipeline ETL & Dashboard

Sistema de integración de datos diseñado para analizar el impacto del clima histórico en los precios actuales mayoristas de la Palta Hass en Chile.

## 🏗️ Arquitectura de Datos

El proyecto integra 3 fuentes principales de datos:

1. **API ODEPA (Dinámica):** Precios mayoristas diarios extraídos y transformados con Pandas y Pydantic.  
2. **Open-Meteo (Estática):** Historial climático en CSV aplicando rezagos agrícolas (*Lag Features*) de 8 meses.  
3. **SQLite (Motor de Reglas):** Base de datos relacional que define tolerancias térmicas y coordenadas geográficas.

## 🚀 Cómo inicializar el entorno local

### 1. Clonar el repositorio
```bash
git clone <URL_DEL_REPO>
cd Paltas_rentables
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Crear un archivo `.env` en la raíz del proyecto (**no subir a Git**) y agregar:

```env
ODEPA_RESOURCE_ID=580beca0-e87e-4dd4-9e8a-0bd92773f4a6
```

### 4. Ejecutar el Pipeline (en este orden exacto)
```bash
python etl/setup_db.py
python etl/ETL_clima.py
python etl/ETL_odepa.py
python etl/ETL_master.py
```