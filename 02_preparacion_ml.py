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
   en users y hofstede para garantizar compatibilidad con el estándar ISO-2.
4. Consolidación de Happiness (WHR): Se promedia el indicador 'Life Ladder'
   por país (GROUP BY country) y se traducen sus nombres en inglés a códigos
   ISO-2 mediante pycountry y un diccionario de excepciones nominales.
5. Filtro de Representatividad: Se conservan únicamente los países con un
   mínimo de 10 usuarios únicos representativos.

ESTRATEGIA DE MEMORIA Y ARQUITECTURA TÉCNICA:
-------------------------------------------------------------------------------
Para evitar errores de Out-Of-Memory (OOM Killer) al procesar los 351M de
eventos:
- Se agrupa en 3 etapas SQL livianas con DuckDB (acumulando primero por usuario).
- Se habilita el volcado temporal en disco (`temp_directory` en .tmp/) con límite
  de memoria física (RAM) fijado en 3 GB.
===============================================================================
"""

import duckdb
from pathlib import Path
import pandas as pd
import pycountry

# Configuración de rutas
BASE_DIR = Path.cwd()
PARQUET_DIR = BASE_DIR / "data" / "parquet"
CLEAN_DIR = BASE_DIR / "data" / "clean"
TMP_DIR = BASE_DIR / ".tmp"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Diccionario de excepciones para nombres de países en happiness
EXCEPCIONES_ISO2 = {
    "Russia": "RU",
    "South Korea": "KR",
    "Taiwan Province of China": "TW",
    "Hong Kong S.A.R. of China": "HK",
    "Iran": "IR",
    "Vietnam": "VN",
    "Venezuela": "VE",
    "Bolivia": "BO",
    "Moldova": "MD",
    "Tanzania": "TZ",
    "Macedonia": "MK",
    "Syria": "SY",
    "Laos": "LA",
    "Palestinian Territories": "PS",
    "Congo (Kinshasa)": "CD",
    "Congo (Brazzaville)": "CG",
    "Ivory Coast": "CI",
    "Swaziland": "SZ"
}

def nombre_a_iso2(nombre: str):
    if not isinstance(nombre, str):
        return None
    nombre = nombre.strip()
    if nombre in EXCEPCIONES_ISO2:
        return EXCEPCIONES_ISO2[nombre]
    try:
        return pycountry.countries.lookup(nombre).alpha_2
    except LookupError:
        return None

print("--> Conectando a DuckDB con optimización de memoria en disco...")
con = duckdb.connect()

con.execute(f"SET temp_directory='{TMP_DIR.as_posix()}';")
con.execute("SET preserve_insertion_order=false;")
con.execute("SET memory_limit='3GB';")

print("--> Paso 1/3: Filtrando bots (>720 escuchas/día)...")
con.execute(f"""
CREATE OR REPLACE TEMP TABLE bots AS
SELECT user_id, strftime(to_timestamp(timestamp), '%Y-%m-%d') AS fecha
FROM '{PARQUET_DIR}/events.parquet'
GROUP BY user_id, fecha
HAVING COUNT(*) > 720;
""")

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

print("--> Paso 3/3: Consolidando métricas por país y uniendo Hofstede + Happiness (ISO-2)...")

# 1. Métricas sonoras agregadas por país (normalizando UK -> GB)
df_metricas_pais = con.execute(f"""
WITH usuarios_pais AS (
    SELECT 
        u.user_id,
        CASE WHEN u.country = 'UK' THEN 'GB' ELSE u.country END AS country,
        ua.usr_valence, ua.usr_energy, ua.usr_danceability, 
        ua.usr_acousticness, ua.usr_tempo, ua.total_escuchas
    FROM '{PARQUET_DIR}/users.parquet' u
    JOIN usuario_audio ua ON u.user_id = ua.user_id
    WHERE u.country IS NOT NULL AND u.country != ''
)
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
ORDER BY total_escuchas DESC;
""").df()

# 2. Hofstede normalizado a ISO-2 (UK -> GB)
df_hof = con.execute(f"""
SELECT 
    CASE WHEN ctr = 'UK' THEN 'GB' ELSE ctr END AS country,
    TRY_CAST(indulgence AS DOUBLE) AS indulgence,
    TRY_CAST(individualism AS DOUBLE) AS individualism
FROM '{PARQUET_DIR}/hofstede.parquet'
""").df()

# 3. Happiness promediado por país y mapeado a ISO-2
df_hap = con.execute(f"""
SELECT 
    country AS country_name,
    AVG("Life Ladder") AS happiness_score
FROM '{PARQUET_DIR}/happiness.parquet'
GROUP BY country
""").df()

df_hap["country"] = df_hap["country_name"].apply(nombre_a_iso2)
df_hap = df_hap.dropna(subset=["country"])[["country", "happiness_score"]]

# 4. Unión final por código ISO-2 ('country')
df_paises = (
    df_metricas_pais
    .merge(df_hof, on="country", how="left")
    .merge(df_hap, on="country", how="left")
)

output_path = CLEAN_DIR / "df_paises_clean.parquet"
df_paises.to_parquet(output_path, index=False)

print(f"\n¡ÉXITO TOTAL!")
print(f"✓ Dataset generado y guardado en: {output_path}")
print(f"✓ Dimensiones: {df_paises.shape[0]} países x {df_paises.shape[1]} columnas")
print("\nConteo de valores nulos por columna:")
print(df_paises.isna().sum())