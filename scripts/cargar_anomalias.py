import csv
import time
from datetime import datetime

from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection
from cassandra.concurrent import execute_concurrent

ARCHIVO_CSV = "data/mediciones.csv"
TAMANO_BLOQUE = 500
CONCURRENCIA = 50

# Conexión local con ScyllaDB
class TraductorDireccion:
    def translate(self, address):
        return "127.0.0.1"

def main():
    cluster = None
    total_mediciones = 0
    total_anomalias = 0
    total_escrituras = 0
    inicio = time.perf_counter()

    try:
        cluster = Cluster(
            ["127.0.0.1"],
            port=9042,
            connection_class=AsyncioConnection,
            address_translator=TraductorDireccion(),
            connect_timeout=10,
            control_connection_timeout=10,
        )

        session = cluster.connect("aquasense")
        print("Conexion correcta con ScyllaDB.")

        # Preparar la inserción de anomalías
        insertar = session.prepare("""
            INSERT INTO anomalias_por_zona
            (zona_id, mes_anio, timestamp, sensor_id,
             presion, caudal, temperatura, calidad)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """)

        bloque = []

        # Guardar las anomalías por bloques
        def guardar_bloque():
            nonlocal total_escrituras

            if not bloque:
                return

            resultados = execute_concurrent(
                session,
                bloque,
                concurrency=CONCURRENCIA,
                raise_on_first_error=False,
            )

            errores = [
                resultado
                for correcto, resultado in resultados
                if not correcto
            ]

            if errores:
                raise RuntimeError(
                    f"Fallaron {len(errores)} escrituras. "
                    f"Primer error: {errores[0]}"
                )

            total_escrituras += len(bloque)
            bloque.clear()

        # Leer el CSV y seleccionar las anomalías
        with open(
            ARCHIVO_CSV,
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as archivo:

            lector = csv.DictReader(archivo)

            for fila in lector:
                total_mediciones += 1

                if fila["es_anomalia"].strip().lower() != "true":
                    continue

                fecha = datetime.fromisoformat(fila["timestamp"])

                bloque.append((
                    insertar,
                    (
                        fila["zona_id"],
                        fecha.strftime("%Y-%m"),
                        fecha,
                        fila["sensor_id"],
                        float(fila["presion"]),
                        float(fila["caudal"]),
                        float(fila["temperatura"]),
                        float(fila["calidad"]),
                    ),
                ))

                total_anomalias += 1

                if len(bloque) >= TAMANO_BLOQUE:
                    guardar_bloque()

                if total_anomalias % 1000 == 0:
                    print(
                        f"Anomalias procesadas: "
                        f"{total_anomalias:,}",
                        flush=True,
                    )

        guardar_bloque()

        duracion = time.perf_counter() - inicio

        # Comprobar la proporción y las escrituras
        proporcion = (
            total_anomalias / total_mediciones
            if total_mediciones > 0 else 0
        )

        if not 0.005 <= proporcion <= 0.015:
            raise RuntimeError(
                "La proporcion de anomalias esta fuera "
                "del rango esperado."
            )

        if total_escrituras != total_anomalias:
            raise RuntimeError(
                "El total de escrituras no coincide."
            )

        print("\nCarga de anomalias terminada.")
        print(f"Anomalias procesadas: {total_anomalias:,}")
        print(f"Escrituras confirmadas: {total_escrituras:,}")
        print(f"Porcentaje de anomalias: {proporcion * 100:.2f}%")
        print(f"Tiempo total: {duracion:.2f} segundos")

    finally:
        if cluster is not None:
            cluster.shutdown()

if __name__ == "__main__":
    main()
