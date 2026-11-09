"""
===============================================================================
SCRIPT DE PREPARACIÓN DE DATOS Y FEATURE ENGINEERING (ML)
===============================================================================
Origen de Datos: Archivos .parquet en /data/parquet/ (351M+ de escuchas)
Destino: /data/clean/df_paises_clean.parquet

REGLAS DE LIMPIEZA Y TRANSFORMACIÓN APLICADAS:
-------------------------------------------------------------------------------
1. Filtrado Temporal: Se conservan únicamente escuchas del rango 2005 - 2014,
   eliminando registros corruptos fuera de época (p. ej., timestamp del año 1970).
2. Filtrado de Bots (Scrobbling Anómalo): Se identifican y descartan las 
   jornadas diarias de usuarios con > 720 escuchas/día (>24 hs de audio continuo).
3. Normalización Geográfica (ISO-2): Se remapea el código de país 'UK' -> 'GB' 
   para garantizar la compatibilidad con el estándar ISO-2 de Hofstede.
4. Filtro de Representatividad: Se conservan únicamente los países con un 
   mínimo de 10 usuarios únicos representativos.

ESTRATEGIA DE MEMORIA Y ARQUITECTURA TÉCNICA:
-------------------------------------------------------------------------------
Para evitar errores de Out-Of-Memory (OOM Killer) en Ubuntu al procesar los
351M de eventos sobre hardware limitado:
- Se agrupa en 3 etapas SQL livianas con DuckDB (acumulando primero por usuario).
- Se habilita el volcado temporal en disco (`temp_directory` en .tmp/) con límite
  de memoria física (RAM) fijado en 3 GB.

CONTENIDO DE LA MATRIZ SALIDA (df_paises_clean.parquet):
-------------------------------------------------------------------------------
- Granularidad: 1 fila = 1 País (98 países representativos procesados).
- Dimensiones: 11 columnas (Metadatos de país + Atributos de Audio de Spotify + 
  Dimensiones Culturales de Hofstede + Métricas Socioeconómicas de WHR).
===============================================================================
"""

import duckdb
from pathlib import Path
import pandas as pd
import numpy as np

# Configuración de rutas
BASE_DIR = Path.cwd()
PARQUET_DIR = BASE_DIR / "data" / "parquet"
CLEAN_DIR = BASE_DIR / "data" / "clean"
TMP_DIR = BASE_DIR / ".tmp"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

print("--> Conectando a DuckDB con optimización de memoria en disco...")
con = duckdb.connect()

# Habilitar almacenamiento temporal en disco para evitar saturación de RAM
con.execute(f"SET temp_directory='{TMP_DIR.as_posix()}';")
con.execute("SET preserve_insertion_order=false;")
con.execute("SET memory_limit='3GB';")

print("--> Paso 1/3: Filtrando bots y creando tabla de usuarios válidos...")

# 1. Crear tabla temporal de bots (>720 escuchas/día)
con.execute(f"""
CREATE OR REPLACE TEMP TABLE bots AS
SELECT user_id, strftime(to_timestamp(timestamp), '%Y-%m-%d') AS fecha
FROM '{PARQUET_DIR}/events.parquet'
GROUP BY user_id, fecha
HAVING COUNT(*) > 720;
""")

# 2. Resumir perfil de escuchas por usuario (Reduce 351M de eventos a ~55k usuarios)
print("--> Paso 2/3: Agregando rasgos de audio por usuario...")
con.execute(f"""
CREATE OR REPLACE TEMP TABLE usuario_audio AS
SELECT 
    e.user_id,
    AVG(af.valence) AS usr_valence,
    AVG(af.energy) AS usr_energy,
    AVG(af.danceability) AS usr_danceability,
    AVG(af.acousticness) AS usr_acousticness,
    AVG(af.tempo) AS usr_tempo,
    COUNT(*) AS total_escuchas
FROM '{PARQUET_DIR}/events.parquet' e
JOIN '{PARQUET_DIR}/acoustic_features.parquet' af ON e.track_id = af.track_id
LEFT JOIN bots b 
       ON e.user_id = b.user_id 
      AND strftime(to_timestamp(e.timestamp), '%Y-%m-%d') = b.fecha
WHERE year(to_timestamp(e.timestamp)) BETWEEN 2005 AND 2014
  AND b.user_id IS NULL
GROUP BY e.user_id;
""")

print("--> Paso 3/3: Consolidando dataset final a nivel País...")
query_paises = f"""
WITH usuarios_pais AS (
    SELECT 
        u.user_id,
        CASE WHEN u.country = 'UK' THEN 'GB' ELSE u.country END AS country,
        ua.usr_valence, ua.usr_energy, ua.usr_danceability, 
        ua.usr_acousticness, ua.usr_tempo, ua.total_escuchas
    FROM '{PARQUET_DIR}/users.parquet' u
    JOIN usuario_audio ua ON u.user_id = ua.user_id
    WHERE u.country IS NOT NULL AND u.country != ''
),
metricas_pais AS (
    SELECT 
        country,
        COUNT(DISTINCT user_id) AS total_usuarios,
        SUM(total_escuchas) AS total_escuchas,
        AVG(usr_valence) AS avg_valence,
        AVG(usr_energy) AS avg_energy,
        AVG(usr_danceability) AS avg_danceability,
        AVG(usr_acousticness) AS avg_acousticness,
        AVG(usr_tempo) AS avg_tempo
    FROM usuarios_pais
    GROUP BY country
    HAVING COUNT(DISTINCT user_id) >= 10
)
SELECT 
    m.*,
    TRY_CAST(h.indulgence AS DOUBLE) AS indulgence,
    TRY_CAST(h.individualism AS DOUBLE) AS individualism,
    w."Life Ladder" AS happiness_score
FROM metricas_pais m
LEFT JOIN '{PARQUET_DIR}/hofstede.parquet' h ON m.country = h.ctr
LEFT JOIN '{PARQUET_DIR}/happiness.parquet' w ON m.country = w.country
ORDER BY total_escuchas DESC;
"""

df_paises = con.execute(query_paises).df()
output_path = CLEAN_DIR / "df_paises_clean.parquet"
df_paises.to_parquet(output_path, index=False)

print(f"\n¡ÉXITO TOTAL Y DEFINITIVO!")
print(f"✓ Dataset generado y guardado en: {output_path}")
print(f"✓ Dimensiones de la matriz: {df_paises.shape[0]} países por {df_paises.shape[1]} columnas.")