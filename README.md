# Análisis de escuchas musicales

TP de minería de datos con el Culture-Aware Music Recommendation Dataset (Last.fm, 2005–2014).
Las dos técnicas principales son clustering de usuarios y recomendación de artistas.
El armado de sesiones para reglas de asociación queda como prueba opcional.

## Organización

```text
proyecto_ml/
├── data/
│   ├── parquet/      # Datos originales convertidos a Parquet
│   ├── clean/        # Datos limpios
│   └── vistas/       # Tablas para los modelos
├── notebooks/
│   ├── config.py
│   ├── 01_exploracion_calidad_ml.ipynb
│   ├── 02_limpieza_datos_ml.ipynb
│   ├── 03_vistas_minables_ml.ipynb
│   └── 06_preparacion_asociacion_opcional.ipynb
├── .tmp/             # Archivos temporales de DuckDB
├── requirements.txt
└── .gitignore
```

Las notebooks 04 (clustering) y 05 (recomendación) todavía no están incluidas.

## Dependencias

Desde la carpeta principal del proyecto, ejecutar:

```bash
python -m pip install -r requirements.txt
```

## Datos

Colocar en `data/parquet/` los archivos `events.parquet`, `users.parquet`, `artists.parquet` y `acoustic_features.parquet`.
No están incluidos en el ZIP. Si ya tenés un repositorio con los datos, podés copiar `config.py` y las notebooks juntos a tu carpeta `mineria/` (o `notebooks/`), un nivel por debajo de la raíz. No hace falta mover ni duplicar los Parquet. Conservá tu carpeta `comun/` y el script `00_convertir_a_parquet.py`, que no fueron enviados.

Fuentes de datos (como en el notebook 01):
- https://zenodo.org/records/3477842
- https://zenodo.org/record/3964506

## Ejecución

Abrir las notebooks con el directorio de trabajo en la carpeta que contiene `config.py`. Por ejemplo, desde la raíz:

```bash
cd notebooks
python -m notebook
```

1. `01_exploracion_calidad_ml.ipynb`: analiza los Parquet originales.
2. `02_limpieza_datos_ml.ipynb`: genera los tres Parquet de `data/clean/`.
3. `03_vistas_minables_ml.ipynb`: genera `vista_usuarios.parquet` y `vista_usuario_artista.parquet`.
4. Opcional: `06_preparacion_asociacion_opcional.ipynb` genera `vista_sesiones.parquet` después de la 03.

Si ya tenés las tablas limpias, podés pasar directamente a la 03. Si volvés a ejecutar celdas con `COPY`, tené en cuenta que pueden reemplazar los Parquet de salida.

## Configuración compartida

`config.py` centraliza las rutas, el límite de memoria (4 GB), la zona horaria y la carpeta temporal.
`conectar()` abre una nueva conexión en cada notebook. `ruta_sql(nombre)` busca la ruta del archivo en `ARCHIVOS` y la devuelve entre comillas para SQL.
Por ejemplo:

```python
from config import conectar, ruta_sql

con = conectar()
con.execute(f"CREATE OR REPLACE VIEW events AS SELECT * FROM {ruta_sql('events')}")
```

Para cambiar la ubicación de los datos, modificar `DATA_DIR` en `config.py`.
El límite de memoria no es un límite de RAM para todo Python; dejar espacio disponible en disco para `.tmp/`.

## Resultados y validación

Se conservaron las salidas y observaciones históricas de las notebooks (excepto las celdas de conexión). Las consultas no se volvieron a ejecutar con los datos originales. Los resultados pendientes de la notebook opcional deben verificarse al correrla.
La vista de recomendación resume todo el historial: al evaluar con una división temporal, reconstruir las interacciones y elegir usuarios y artistas a partir del entrenamiento para no usar información futura.
