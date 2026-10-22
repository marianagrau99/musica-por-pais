"""
Paso 1: revisar que los archivos estén bien y ver el formato real de cada uno.


Estructura esperada:
    giras/
      paso1_revisar.py          <- este script
      data/culture_aware/       <- los 7 archivos descargados

Uso (parada en la carpeta giras):
    python paso1_revisar.py
"""
import tarfile
from collections import Counter
from pathlib import Path

CARPETA = Path("data/culture_aware")

ESPERADOS = {
    "users.tsv": "usuarios",
    "acoustic_features_lfm_id.tsv": "audio features",
    "hofstede.tsv": "Hofstede",
    "world_happiness_report_2018.tsv": "felicidad",
    "LFM1b-MB-artists.txt": "nombres de artistas",
}


def titulo(texto):
    print("\n" + "=" * 70 + f"\n{texto}\n" + "=" * 70)


def primeras_lineas(ruta, n=5):
    with open(ruta, encoding="utf-8", errors="replace") as f:
        for i, linea in enumerate(f):
            if i >= n:
                break
            # repr() muestra los tabs como \t, así vemos el separador real
            print("  " + repr(linea.rstrip("\n")))


# 1) ¿Están todos los archivos?
titulo("1. ARCHIVOS")
if not CARPETA.exists():
    raise SystemExit(f"No encuentro la carpeta {CARPETA.resolve()}")
for ruta in sorted(CARPETA.iterdir()):
    print(f"  {ruta.name:45s} {ruta.stat().st_size / 1e6:>10,.1f} MB")
faltan = [n for n in ESPERADOS if not (CARPETA / n).exists()]
eventos = sorted(CARPETA.glob("events.tar*"))
if not eventos:
    faltan.append("events.tar.gz")
if faltan:
    print("\n  FALTAN (o tienen otro nombre):", faltan)
    print("  Si un archivo se llama 'users (1).tsv' o parecido, renombralo.")

# 2) Archivo de artistas: ¿qué columnas trae?
titulo("2. LFM1b-MB-artists.txt (primeras 10 líneas)")
ruta_art = CARPETA / "LFM1b-MB-artists.txt"
if ruta_art.exists():
    primeras_lineas(ruta_art, n=10)
    with open(ruta_art, encoding="utf-8", errors="replace") as f:
        n_lineas = sum(1 for _ in f)
    print(f"\n  Total de líneas: {n_lineas:,}")

# 3) Usuarios: países y edades
titulo("3. users.tsv")
ruta_us = CARPETA / "users.tsv"
if ruta_us.exists():
    primeras_lineas(ruta_us)
    with open(ruta_us, encoding="utf-8", errors="replace") as f:
        cab = f.readline().rstrip("\n").split("\t")
        filas = [l.rstrip("\n").split("\t") for l in f]
    print(f"\n  {len(filas):,} usuarios")
    if "country" in cab:
        paises = Counter(fila[cab.index("country")] for fila in filas)
        print(f"  {len(paises)} países. Los 15 con más usuarios:")
        for pais, n in paises.most_common(15):
            print(f"    {pais}: {n:,}")
        print("  ¿Está Argentina (AR)?", "sí, " + f"{paises['AR']:,} usuarios" if "AR" in paises else "no")
    if "age" in cab:
        edades = [int(f[cab.index("age")]) for f in filas if f[cab.index("age")].lstrip("-").isdigit()]
        validas = [e for e in edades if 10 <= e <= 90]
        print(f"  Edad: {len(validas):,} usuarios con edad válida (10-90), "
              f"{len(edades) - len(validas):,} con edad vacía o rara")

# 4) Audio features
titulo("4. acoustic_features_lfm_id.tsv")
if (CARPETA / "acoustic_features_lfm_id.tsv").exists():
    primeras_lineas(CARPETA / "acoustic_features_lfm_id.tsv")

# 5) Eventos: se leen desde el comprimido, sin descomprimir al disco
titulo("5. EVENTOS (desde el comprimido)")
for ruta_ev in eventos:
    print(f"  Archivo: {ruta_ev.name} ({ruta_ev.stat().st_size / 1e9:.2f} GB)")
    try:
        # 'r|*' detecta solo si está comprimido (.tar.gz) o no (.tar)
        with tarfile.open(ruta_ev, mode="r|*") as tar:
            for miembro in tar:
                print(f"\n  -- adentro: {miembro.name} ({miembro.size / 1e9:.2f} GB sin comprimir)")
                if miembro.isfile():
                    f = tar.extractfile(miembro)
                    for _ in range(5):
                        linea = f.readline()
                        if not linea:
                            break
                        print("    " + repr(linea.decode("utf-8", "replace").rstrip("\n")))
                    break  # con el primer archivo alcanza; recorrer todo tardaría minutos
    except tarfile.ReadError as e:
        print("  No se pudo abrir: puede que la descarga esté incompleta.", e)

titulo("LISTO: copiá todo lo que salió en pantalla y pasáselo a Claude")
