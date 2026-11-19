"""
config.py: preparación del entorno que comparten los notebooks

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
while not (carpeta / "data" / "clean").exists():
    if carpeta == carpeta.parent:
        raise FileNotFoundError("No se encontró la carpeta data/clean. Correr 02_limpieza.ipynb")
    carpeta = carpeta.parent

ruta = (carpeta / "data" / "parquet").as_posix() + "/"         # datos originales
ruta_clean = (carpeta / "data" / "clean").as_posix() + "/"     # datos limpios (los genera 02_limpieza.ipynb)
ruta_tablas = (carpeta / "data" / "tablas").as_posix() + "/"   # tablas que usan los gráficos
tmp = carpeta / ".tmp"                                         # carpeta temporal de DuckDB
Path(ruta_tablas).mkdir(parents=True, exist_ok=True)
tmp.mkdir(exist_ok=True)

# ---------------------------------------------------------------
# Valores que se eligieron una vez y tienen que ser iguales en todos los notebooks
# ---------------------------------------------------------------
FEATURES = ["danceability", "energy", "valence", "acousticness",
            "instrumentalness", "speechiness", "liveness"]

MIN_ESCUCHAS = 100        # mínimo de escuchas para que un usuario entre en tabla_usuario
MIN_USUARIOS_PAIS = 50    # mínimo de usuarios para mostrar un país (con 50 quedan 56 países, ver 01_exploracion)

# ---------------------------------------------------------------
# Conexión a DuckDB
# ---------------------------------------------------------------
con = duckdb.connect()
con.execute("SET memory_limit = '4GB'")                  # tope de memoria
con.execute(f"SET temp_directory = '{tmp.as_posix()}'")  # si hace falta más memoria, usa el disco
con.execute("SET preserve_insertion_order = false")      # ahorra memoria
con.execute("SET TimeZone = 'UTC'")                      # usamos la misma zona horaria en todos los notebooks

# Vistas: un nombre corto para cada archivo.
# Solo se crean las que existen, así este archivo no falla si todavía falta alguno.
archivos = {
    "events_clean": ruta_clean,
    "users_clean": ruta_clean,
    "acoustic_features_clean": ruta_clean,
    "hofstede_clean": ruta_clean,
    "happiness_clean": ruta_clean,
    "tabla_usuario": ruta_tablas,   # la genera 03_tabla_usuario.ipynb
    "artists": ruta,                # nombres de los artistas (datos originales)
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
    Parámetros:
        consulta (str): consulta SQL a ejecutar.
        nombre (str): nombre del archivo sin la extensión.
    Retorna: None.
    """
    destino = f"{ruta_tablas}{nombre}.parquet"
    con.execute(f"COPY ({consulta}) TO '{destino}' (FORMAT PARQUET)")
    filas = con.execute(f"SELECT COUNT(*) FROM '{destino}'").fetchone()[0]
    print(f"{nombre}: {filas:,} filas guardadas en {destino}")
