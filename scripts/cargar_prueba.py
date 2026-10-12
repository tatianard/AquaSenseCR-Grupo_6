import csv
import time
from datetime import datetime
from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection

# Conexión local con ScyllaDB
class TraductorDireccion:
    def translate(self, address):
        return "127.0.0.1"

cluster = None

try:
    cluster = Cluster(
        ["127.0.0.1"],
        port=9042,
        connection_class=AsyncioConnection,
        address_translator=TraductorDireccion(),
        connect_timeout=5,
        control_connection_timeout=5,
    )

    session = cluster.connect("aquasense")
    print("Conexion correcta con ScyllaDB.")

    # Preparar las inserciones en las dos tablas
    insertar_sensor = session.prepare("""
        INSERT INTO mediciones_por_sensor
        (sensor_id, mes_anio, timestamp, zona_id,
         caudal, presion, temperatura, calidad, es_anomalia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    insertar_zona = session.prepare("""
        INSERT INTO mediciones_por_zona
        (zona_id, mes_anio, timestamp, sensor_id,
         caudal, presion, temperatura, calidad, es_anomalia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    total = 0
    inicio = time.perf_counter()

    # Tomar 100 mediciones distribuidas en el CSV
    with open(
        "data/mediciones.csv",
        "r",
        newline="",
        encoding="utf-8-sig"
    ) as archivo:
        lector = csv.DictReader(archivo)

        for indice, fila in enumerate(lector):
            if indice % 10000 != 0:
                continue

            fecha = datetime.fromisoformat(fila["timestamp"])
            mes_anio = fecha.strftime("%Y-%m")

            sensor_id = fila["sensor_id"]
            zona_id = fila["zona_id"]
            caudal = float(fila["caudal"])
            presion = float(fila["presion"])
            temperatura = float(fila["temperatura"])
            calidad = float(fila["calidad"])
            es_anomalia = fila["es_anomalia"].lower() == "true"

            # Insertar en la tabla por sensor
            session.execute(
                insertar_sensor,
                (
                    sensor_id, mes_anio, fecha, zona_id,
                    caudal, presion, temperatura,
                    calidad, es_anomalia
                )
            )

            # Insertar en la tabla por zona
            session.execute(
                insertar_zona,
                (
                    zona_id, mes_anio, fecha, sensor_id,
                    caudal, presion, temperatura,
                    calidad, es_anomalia
                )
            )

            total += 1
            print(f"Medicion {total}/100 insertada", flush=True)

            if total == 100:
                break

    duracion = time.perf_counter() - inicio

    print("\nCarga de prueba terminada.")
    print(f"Mediciones procesadas: {total}")
    print(f"Escrituras realizadas: {total * 2}")
    print(f"Tiempo de carga: {duracion:.2f} segundos")

finally:
    if cluster is not None:
        cluster.shutdown()
