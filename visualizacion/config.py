"""
config.py: preparación del entorno que comparten los notebooks de las preguntas.

Este archivo tiene que estar en la misma carpeta que los notebooks.
En cada notebook se usa así:
    from config import con, q, guardar, ruta_tablas, FEATURES
"""
import duckdb
from pathlib import Path

# ---------------------------------------------------------------
# Carpetas
# ---------------------------------------------------------------
# Buscamos la carpeta data subiendo desde la carpeta donde está este archivo.
# Así funciona esté en la raíz del repo o en una subcarpeta.
carpeta = Path(__file__).resolve().parent
while not (carpeta / "data" / "parquet").exists():
    if carpeta == carpeta.parent:
        raise FileNotFoundError("No encontramos la carpeta data/parquet. Revisar dónde están los datos.")
    carpeta = carpeta.parent

ruta = (carpeta / "data" / "parquet").as_posix() + "/"         # datos originales
ruta_clean = (carpeta / "data" / "clean").as_posix() + "/"     # datos limpios (los genera 02_limpieza.ipynb)
ruta_tablas = (carpeta / "data" / "tablas").as_posix() + "/"   # tablas que usan los gráficos
tmp = carpeta / ".tmp"                                         # carpeta temporal de DuckDB
Path(ruta_clean).mkdir(parents=True, exist_ok=True)
Path(ruta_tablas).mkdir(parents=True, exist_ok=True)
tmp.mkdir(exist_ok=True)

# ---------------------------------------------------------------
# Valores que se eligieron una vez y tienen que ser iguales en todos los notebooks
# ---------------------------------------------------------------
# Audio features: las 7 primeras ya van de 0 a 1; tempo y loudness no, así que en 03_tablas
# se normalizan (mínimo-máximo) y quedan como tempo_norm y loudness_norm
FEATURES = ["danceability", "energy", "valence", "acousticness",
            "instrumentalness", "speechiness", "liveness",
            "tempo_norm", "loudness_norm"]

MIN_ESCUCHAS = 100        # mínimo de escuchas para que un usuario entre en tabla_usuario
MIN_USUARIOS_PAIS = 50    # mínimo de usuarios para mostrar un país (con 50 quedan 56 países, ver 01_exploracion)

# ---------------------------------------------------------------
# Conexión a DuckDB
# ---------------------------------------------------------------
con = duckdb.connect()
con.execute("SET memory_limit = '4GB'")                  # tope de memoria
con.execute(f"SET temp_directory = '{tmp.as_posix()}'")  # si hace falta más memoria, usa el disco
con.execute("SET preserve_insertion_order = false")      # ahorra memoria
con.execute("SET TimeZone = 'UTC'")                      # misma zona horaria que en la limpieza

# Vistas: un nombre corto para cada archivo.
# Solo se crean las que existen, así este archivo no falla si todavía falta alguno.
archivos = {
    # datos originales (los usan 01_exploracion y 02_limpieza)
    "events": ruta,
    "users": ruta,
    "artists": ruta,
    "acoustic_features": ruta,
    "hofstede": ruta,
    "happiness": ruta,
    # datos limpios (los genera 02_limpieza.ipynb)
    "events_clean": ruta_clean,
    "users_clean": ruta_clean,
    "acoustic_features_clean": ruta_clean,
    "hofstede_clean": ruta_clean,
    "happiness_clean": ruta_clean,
    # tabla por usuario (la genera 03_tabla_usuario.ipynb)
    "tabla_usuario": ruta_tablas,
}
for nombre, carpeta_archivo in archivos.items():
    archivo = f"{carpeta_archivo}{nombre}.parquet"
    if Path(archivo).exists():
        con.execute(f"CREATE OR REPLACE VIEW {nombre} AS SELECT * FROM '{archivo}'")


# ---------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------
def q(consulta):
    """
    Ejecuta una consulta SQL y devuelve el resultado como DataFrame de pandas.
    Parámetro: consulta (str): consulta SQL a ejecutar.
    Retorna: pd.DataFrame: resultado de la consulta.
    """
    return con.sql(consulta).df()


def guardar(consulta, nombre):
    """
    Ejecuta una consulta SQL y guarda el resultado como Parquet en la carpeta data/tablas/.
    Después crea una vista con el mismo nombre, para poder usarla con FROM en las celdas siguientes.
    Parámetros:
        consulta (str): consulta SQL a ejecutar.
        nombre (str): nombre del archivo sin la extensión.
    Retorna: None.
    """
    destino = f"{ruta_tablas}{nombre}.parquet"
    con.execute(f"COPY ({consulta}) TO '{destino}' (FORMAT PARQUET)")
    con.execute(f"CREATE OR REPLACE VIEW {nombre} AS SELECT * FROM '{destino}'")
    filas = con.execute(f"SELECT COUNT(*) FROM '{destino}'").fetchone()[0]
    print(f"{nombre}: {filas:,} filas guardadas en {destino}")
