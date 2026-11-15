from pathlib import Path
import duckdb

# Rutas a partir de la ubicación de este archivo
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PARQUET_DIR = DATA_DIR / "parquet"
CLEAN_DIR = DATA_DIR / "clean"
VISTAS_DIR = DATA_DIR / "vistas"
TEMP_DIR = BASE_DIR / ".tmp"

ARCHIVOS = {
    "events": PARQUET_DIR / "events.parquet",
    "users": PARQUET_DIR / "users.parquet",
    "artists": PARQUET_DIR / "artists.parquet",
    "acoustic_features": PARQUET_DIR / "acoustic_features.parquet",
    "events_clean": CLEAN_DIR / "events_clean.parquet",
    "users_clean": CLEAN_DIR / "users_clean.parquet",
    "acoustic_clean": CLEAN_DIR / "acoustic_clean.parquet",
    "vista_usuarios": VISTAS_DIR / "vista_usuarios.parquet",
    "vista_usuario_artista": VISTAS_DIR / "vista_usuario_artista.parquet",
    "vista_sesiones": VISTAS_DIR / "vista_sesiones.parquet",
}


def ruta_sql(nombre):
    # Devuelve la ruta entre comillas para usarla en SQL.
    return "'" + ARCHIVOS[nombre].as_posix().replace("'", "''") + "'"


def conectar():
    for carpeta in [CLEAN_DIR, VISTAS_DIR, TEMP_DIR]:
        carpeta.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("SET memory_limit = '4GB'")
    con.execute("SET TimeZone = 'UTC'")
    ruta_temp = TEMP_DIR.as_posix().replace("'", "''")
    con.execute(f"SET temp_directory = '{ruta_temp}'")
    return con
