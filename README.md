# Hábitos de escucha musical por país (Last.fm, 2005–2014)

Proyecto integrador para **Visualización de Grandes Volúmenes de Datos** y **Data Mining** (UNLP, 2026).

______________________________________
## Datos

Los datos **no están en el repositorio** porque son muy pesados (más de 3 GB).

1. **Culture-Aware Music Recommendation Dataset**: https://zenodo.org/records/3477842
   Descargar los 6 archivos: 
   `events.tar.gz`, 
   `users.tsv`, 
   `acoustic_features_lfm_id.tsv`,
   `hofstede.tsv`, 
   `world_happiness_report_2018.tsv` y 
   `README.md`.
2. **Nombres de artistas**: https://zenodo.org/record/3964506
   Descargar solo `LFM1b-MB-artists.txt`.

Guardar los 7 archivos en la carpeta `data/culture_aware/` 
No descomprimir `events.tar.gz`.

Para verificar que `events.tar.gz` se descargó completo (Windows):
```
certutil -hashfile data\culture_aware\events.tar.gz MD5
```
Tiene que dar `0a7a8096933c6d58721791c9aae5752f`.

______________________________________


## Cómo ejecutar
### 1. Crear y activar el entorno virtual (`venv`)

* **En Linux (Ubuntu / Debian / macOS):** *(Si* no tenés instalado *`python3-venv` en Ubuntu, ejecutá primero: `sudo apt update && sudo apt install python3-venv`)*

  ```
  python3 -m venv venv
  source venv/bin/activate
  
  ```

* **En Windows (Git Bash):**

  ```
  py -m venv venv
  source venv/Scripts/activate
  
  ```

* **En Windows (PowerShell):**

  ```
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  
  ```

### 2. Instalar las dependencias

Con el entorno `(venv)` activado:

```
# Actualizar pip para asegurar compatibilidad con paquetes precompilados
python -m pip install --upgrade pip setuptools

# Instalar las librerías del proyecto
pip install -r requirements.txt

```

### 3. Revisar y convertir los datos

```
# Opcional: verificar que los archivos brutos descargados estén correctos
python 00_revisar_descarga.py

# Convertir los datos a formato Parquet comprimido (ZSTD)
python 00_convertir_a_parquet.py

```

*(Genera la carpeta `data/parquet/` en menos de 5 minutos).*

### 4. Ejecutar el Análisis Exploratorio (EDA)

Abrir el notebook `01_exploracion_calidad.ipynb` en VS Code o Jupyter.

> **Importante:** Asegurarse de seleccionar como Kernel el entorno virtual recién creado (`venv`).


______________________________________
## Estructura

```
├── docs/                                  # Documentación técnica y académica del proyecto
│   └── Documentacion_Dataset_Musica_Cultural.docx
├── README.md                              # Guía de ejecución del repositorio
├── requirements.txt                       # Librerías con versiones congeladas
├── 00_revisar_descarga.py                 # Validador de archivos descargados de Zenodo
├── 00_convertir_a_parquet.py              # Ingesta masiva y conversión a Parquet (PyArrow + DuckDB)
├── 01_exploracion_calidad.ipynb           # EDA de calidad de datos, nulos y patrones anómalos
└── data/                                  # NO se sube a GitHub (ignorado en .gitignore)
    ├── culture_aware/                     # Archivos fuente originales de Zenodo
    ├── parquet/                           # Archivos procesados optimizados por 00_convertir_a_parquet.py
    └── clean/                             # Datasets limpios para modelos de Minería y Visualización

```
______________________________________
## Fuentes

- Zangerle, E., Pichl, M., & Schedl, M. (2020). User Models for Culture-Aware Music Recommendation:
  Fusing Acoustic and Cultural Cues. *Transactions of the International Society for Music Information
  Retrieval*, 3(1). https://doi.org/10.5334/tismir.37
- Last.fm artists gender information (LFM-1b). Zenodo: https://zenodo.org/record/3964506
