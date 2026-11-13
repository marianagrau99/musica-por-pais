"""
Conversión de los archivos originales (TSV) a formato parquet.

Los archivos de texto ocupan mucho (las escuchas pesan 13,86 GB descomprimidas)
y son lentos de leer. El formato parquet guarda los datos por columna y comprimidos,
lo que permite consultarlos mucho más rápido con DuckDB.

Requiere: pip install pyarrow duckdb
Uso (desde la carpeta del proyecto):
    python 00_convertir_a_parquet.py

Tarda entre 5 y 15 minutos. Si se vuelve a ejecutar, saltea los archivos ya convertidos.
Al final verifica la cantidad de escuchas y que los IDs de artistas coincidan con sus nombres.
"""
import io
import tarfile
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

ORIGEN = Path("data/culture_aware")
DESTINO = Path("data/parquet")
DESTINO.mkdir(parents=True, exist_ok=True)

# Todos los archivos son TSV sin comillas (lo dice el README)
PARSEO = pacsv.ParseOptions(delimiter="\t", quote_char=False)


def tsv_a_parquet(nombre_tsv, nombre_parquet, tipos=None):
    destino = DESTINO / nombre_parquet
    if destino.exists():
        print(f"  ya existe {nombre_parquet}, lo salteo")
        return
    tabla = pacsv.read_csv(
        ORIGEN / nombre_tsv,
        parse_options=PARSEO,
        convert_options=pacsv.ConvertOptions(column_types=tipos or {}),
    )
    pq.write_table(tabla, destino, compression="zstd")
    print(f"  {nombre_parquet}: {tabla.num_rows:,} filas")


def artistas_a_parquet():
    """El archivo de artistas no tiene encabezado: id <tab> nombre <tab> conteo de géneros."""
    destino = DESTINO / "artists.parquet"
    if destino.exists():
        print("  ya existe artists.parquet, lo salteo")
        return
    ids, nombres, generos = [], [], []
    descartadas = 0
    with open(ORIGEN / "LFM1b-MB-artists.txt", encoding="utf-8", errors="replace") as f:
        for linea in f:
            partes = linea.rstrip("\r\n").split("\t")
            if len(partes) < 2 or not partes[0].isdigit():
                descartadas += 1
                continue
            ids.append(int(partes[0]))
            if len(partes) >= 3:
                # si un nombre tuviera un tab adentro, lo volvemos a unir
                nombres.append("\t".join(partes[1:-1]))
                generos.append(partes[-1])
            else:
                nombres.append(partes[1])
                generos.append(None)
    tabla = pa.table({
        "artist_id": pa.array(ids, pa.int32()),
        "artist_name": pa.array(nombres, pa.string()),
        "gender_counts": pa.array(generos, pa.string()),  # desconocido/masc/fem/otro/na
    })
    pq.write_table(tabla, destino, compression="zstd")
    print(f"  artists.parquet: {tabla.num_rows:,} artistas ({descartadas} líneas descartadas)")


class SoloLectura(io.RawIOBase):
    """Adaptador para leer el archivo de escuchas directamente desde el .tar.gz.

    pyarrow lee el archivo en bloques y en algún momento pregunta si se puede "rebobinar"
    (volver atrás). El archivo que sale del comprimido no lo permite y esa pregunta da error.
    Esta clase responde que no se puede rebobinar y le entrega los datos de corrido.
    Así evitamos descomprimir los 14 GB al disco."""

    def __init__(self, archivo):
        self.archivo = archivo

    def readable(self):
        return True

    def seekable(self):
        return False

    def readinto(self, buffer):
        datos = self.archivo.read(len(buffer))
        buffer[: len(datos)] = datos
        return len(datos)


def eventos_a_parquet():
    """Lee events.tsv directo desde el .tar.gz y lo escribe en parquet por bloques,
    así nunca tiene los 14 GB en memoria ni en disco."""
    destino = DESTINO / "events.parquet"
    if destino.exists():
        print("  ya existe events.parquet, lo salteo")
        return
    temporal = DESTINO / "events.parquet.part"
    tipos = {
        "user_id": pa.int32(),
        "artist_id": pa.int32(),
        "album_id": pa.int32(),
        "track_id": pa.int32(),
        "timestamp": pa.int64(),
    }
    ruta = next(ORIGEN.glob("events.tar*"))
    filas, inicio, escritor = 0, time.time(), None

    with tarfile.open(ruta, mode="r|*") as tar:
        for miembro in tar:
            if not (miembro.isfile() and miembro.name.endswith(".tsv")):
                continue
            flujo = io.BufferedReader(SoloLectura(tar.extractfile(miembro)), buffer_size=16 << 20)
            lector = pacsv.open_csv(
                pa.PythonFile(flujo, mode="r"),
                read_options=pacsv.ReadOptions(block_size=64 << 20),  # bloques de 64 MB
                parse_options=PARSEO,
                convert_options=pacsv.ConvertOptions(column_types=tipos),
            )
            for lote in lector:
                tabla = pa.Table.from_batches([lote])
                if escritor is None:
                    escritor = pq.ParquetWriter(temporal, tabla.schema, compression="zstd")
                escritor.write_table(tabla)
                filas += lote.num_rows
                print(f"\r  {filas:,} escuchas ({time.time() - inicio:,.0f} s)", end="", flush=True)
            break

    escritor.close()
    temporal.rename(destino)  # solo queda con el nombre final si terminó bien
    print(f"\n  events.parquet: {filas:,} escuchas")


def verificar():
    con = duckdb.connect()
    ev = (DESTINO / "events.parquet").as_posix()
    ar = (DESTINO / "artists.parquet").as_posix()
    us = (DESTINO / "users.parquet").as_posix()

    # 1. Total de escuchas
    total = con.execute(f"SELECT count(*) FROM '{ev}'").fetchone()[0]
    print(f"\n  Escuchas: {total:,} (el README dice 351,469,333)")

    # 2. Cobertura de nombres de artistas
    cobertura = con.execute(f"""
        SELECT avg(CASE WHEN a.artist_id IS NULL THEN 0 ELSE 1 END)
        FROM '{ev}' e LEFT JOIN '{ar}' a USING (artist_id)
    """).fetchone()[0]
    print(f"  Escuchas con nombre de artista: {cobertura:.2%}")

    print("\n  Control: los 25 artistas más escuchados.")
    print("  Si son nombres conocidos, los IDs de escuchas y artistas coinciden.\n")
    
    # 3. Los 25 artistas más escuchados
    df_top25 = con.execute(f"""
        SELECT e.artist_id, a.artist_name,
               count(*) AS escuchas, count(DISTINCT e.user_id) AS oyentes
        FROM '{ev}' e LEFT JOIN '{ar}' a USING (artist_id)
        GROUP BY ALL ORDER BY escuchas DESC LIMIT 25
    """).df()
    print(df_top25.to_string(index=False))

    print("\n  Control adicional: los 15 artistas con más oyentes en Argentina\n")
    
    # 4. Los artistas con más oyentes en Argentina
    df_ar = con.execute(f"""
        SELECT a.artist_name, count(*) AS escuchas, count(DISTINCT e.user_id) AS oyentes
        FROM '{ev}' e
        JOIN '{us}' u USING (user_id)
        LEFT JOIN '{ar}' a USING (artist_id)
        WHERE u.country = 'AR'
        GROUP BY ALL ORDER BY oyentes DESC LIMIT 15
    """).df()
    print(df_ar.to_string(index=False))


if __name__ == "__main__":
    print("1) Archivos chicos")
    tsv_a_parquet("users.tsv", "users.parquet", {"country": pa.string(), "gender": pa.string()})
    tsv_a_parquet("acoustic_features_lfm_id.tsv", "acoustic_features.parquet")
    tsv_a_parquet("hofstede.tsv", "hofstede.parquet")
    tsv_a_parquet("world_happiness_report_2018.tsv", "happiness.parquet")

    print("\n2) Artistas")
    artistas_a_parquet()

    print("\n3) Escuchas (la parte larga)")
    eventos_a_parquet()

    print("\n4) Verificación")
    verificar()
    print("\nConversión terminada.")
