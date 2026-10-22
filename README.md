# Hábitos de escucha musical por país (Last.fm, 2005–2014)

Proyecto integrador para **Visualización de Grandes Volúmenes de Datos** y **Data Mining** (UNLP, 2026).

## Datos

Los datos **no están en el repositorio** porque son muy pesados (más de 3 GB).

1. **Culture-Aware Music Recommendation Dataset**: https://zenodo.org/records/3477842
   Descargar los 6 archivos: `events.tar.gz`, `users.tsv`, `acoustic_features_lfm_id.tsv`,
   `hofstede.tsv`, `world_happiness_report_2018.tsv` y `README.md`.
2. **Nombres de artistas**: https://zenodo.org/record/3964506
   Descargar solo `LFM1b-MB-artists.txt`.

Guardar los 7 archivos en la carpeta `data/culture_aware/` 
No descomprimir `events.tar.gz`.

Para verificar que `events.tar.gz` se descargó completo (Windows):
```
certutil -hashfile data\culture_aware\events.tar.gz MD5
```
Tiene que dar `0a7a8096933c6d58721791c9aae5752f`.

## Cómo ejecutar

1. Instalar las librerías:
   ```
   pip install -r requirements.txt
   ```
2. Revisar que los archivos estén bien (opcional):
   ```
   python 00_revisar_descarga.py
   ```
3. Convertir los datos a parquet:
   ```
   python 00_convertir_a_parquet.py
   ```
   Genera la carpeta `data/parquet/`.
4. Abrir el notebook del EDA y ejecutar las celdas en orden.

## Estructura

```
├── README.md
├── requirements.txt
├── 00_revisar_descarga.py       # revisa los archivos descargados
├── 00_convertir_a_parquet.py    # convierte los datos a parquet
├── [notebook del EDA].ipynb
└── data/                   # NO se sube a GitHub
    ├── culture_aware/      # archivos descargados de Zenodo
    ├── parquet/            # generado por 00_convertir_a_parquet.py 
    └── clean/              # generado por la limpieza 
```

## Fuentes

- Zangerle, E., Pichl, M., & Schedl, M. (2020). User Models for Culture-Aware Music Recommendation:
  Fusing Acoustic and Cultural Cues. *Transactions of the International Society for Music Information
  Retrieval*, 3(1). https://doi.org/10.5334/tismir.37
- Last.fm artists gender information (LFM-1b). Zenodo: https://zenodo.org/record/3964506
