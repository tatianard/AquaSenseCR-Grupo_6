import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Parámetros del proyecto
NUM_SENSORES = 1000
NUM_ZONAS = 20
NUM_MEDICIONES = 1000
SEMILLA = 42
PROPORCION_ANOMALIAS = 0.01
UMBRAL_PRESION = 6.0

# Generar sensores y asignarlos a las zonas
sensores = []

for i in range(NUM_SENSORES):
    sensor = {
        "sensor_id": f"S{i+1:04d}",
        "zona_id": f"Z{(i % NUM_ZONAS) + 1:02d}"
    }
    sensores.append(sensor)

df_sensores = pd.DataFrame(sensores)

# Generar las mediciones de cada sensor
rng = np.random.default_rng(SEMILLA)
fecha_inicio = datetime(2026, 1, 1)

mediciones = []

for sensor in sensores:
    calidad_anterior = 95.0

    for j in range(NUM_MEDICIONES):

        # La calidad cambia ligeramente respecto a la lectura anterior
        calidad_anterior = 0.9 * calidad_anterior + 0.1 * 95 + rng.normal(0, 0.3)
        calidad_anterior = round(max(90, min(100, calidad_anterior)), 2)

        medicion = {
            "sensor_id": sensor["sensor_id"],
            "zona_id": sensor["zona_id"],
            "timestamp": fecha_inicio + timedelta(hours=j),
            "caudal": round(rng.normal(12, 2), 2),
            "presion": round(rng.normal(3.5, 0.4), 2),
            "temperatura": round(rng.normal(24, 2), 2),
            "calidad": calidad_anterior
        }

        mediciones.append(medicion)

df_mediciones = pd.DataFrame(mediciones)

# Introducir presiones elevadas en el 1% de las mediciones
n_anomalias = int(len(df_mediciones) * PROPORCION_ANOMALIAS)

indices_anomalos = rng.choice(
    df_mediciones.index,
    size=n_anomalias,
    replace=False
)

df_mediciones.loc[indices_anomalos, "presion"] = rng.uniform(
    6.5, 8.5, size=n_anomalias
).round(2)

# Identificar las anomalías según el umbral de presión
df_mediciones["es_anomalia"] = df_mediciones["presion"] > UMBRAL_PRESION

# Verificar los datos generados
mediciones_por_sensor = df_mediciones.groupby("sensor_id").size()

duplicados = df_mediciones.duplicated(
    subset=["sensor_id", "timestamp"]
).sum()

# Comprobaciones de los datos generados
assert df_sensores["zona_id"].nunique() == NUM_ZONAS
assert df_mediciones["sensor_id"].nunique() == NUM_SENSORES
assert len(df_mediciones) == NUM_SENSORES * NUM_MEDICIONES
assert mediciones_por_sensor.eq(NUM_MEDICIONES).all()
assert not df_mediciones.isnull().any().any()
assert duplicados == 0
assert 0.005 <= df_mediciones["es_anomalia"].mean() <= 0.015
assert df_mediciones["calidad"].between(90, 100).all()

# Guardar los archivos CSV
carpeta_datos = Path("data")
carpeta_datos.mkdir(exist_ok=True)

df_sensores.to_csv(carpeta_datos / "sensores.csv", index=False)
df_mediciones.to_csv(carpeta_datos / "mediciones.csv", index=False)

# Mostrar resultados
print("\nTotal de sensores:", len(df_sensores))
print("Total de zonas:", df_sensores["zona_id"].nunique())
print("Total de mediciones:", len(df_mediciones))
print("Total de anomalías:", df_mediciones["es_anomalia"].sum())
print("Porcentaje de anomalías:", round(df_mediciones["es_anomalia"].mean() * 100, 2))

print("\nValores de calidad:")
print("Mínimo:", df_mediciones["calidad"].min())
print("Máximo:", df_mediciones["calidad"].max())
print("Promedio:", round(df_mediciones["calidad"].mean(), 2))

print("\nPresión de las mediciones anómalas:")
print("Mínimo:", df_mediciones.loc[df_mediciones["es_anomalia"], "presion"].min())
print("Máximo:", df_mediciones.loc[df_mediciones["es_anomalia"], "presion"].max())

print("\nArchivos CSV generados correctamente.")