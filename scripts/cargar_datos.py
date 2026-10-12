import csv
import time
from datetime import datetime

from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection
from cassandra.concurrent import execute_concurrent

ARCHIVO_CSV = "data/mediciones.csv"
TAMANO_BLOQUE = 500
CONCURRENCIA = 50
MOSTRAR_CADA = 10000

# Conexión local con ScyllaDB
class TraductorDireccion:
    def translate(self, address):
        return "127.0.0.1"


def main():
    cluster = None
    total_mediciones = 0
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

        # Preparar las inserciones
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

        bloque = []

        # Ejecutar las inserciones por bloques
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
                primer_error = errores[0]
                raise RuntimeError(
                    f"Fallaron {len(errores)} escrituras "
                    f"en el bloque. Primer error: {primer_error}"
                )

            total_escrituras += len(bloque)
            bloque.clear()

        # Leer las mediciones del CSV
        with open(
            ARCHIVO_CSV,
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as archivo:

            lector = csv.DictReader(archivo)

            for fila in lector:
                fecha = datetime.fromisoformat(fila["timestamp"])
                mes_anio = fecha.strftime("%Y-%m")

                sensor_id = fila["sensor_id"]
                zona_id = fila["zona_id"]
                caudal = float(fila["caudal"])
                presion = float(fila["presion"])
                temperatura = float(fila["temperatura"])
                calidad = float(fila["calidad"])
                es_anomalia = (
                    fila["es_anomalia"].strip().lower()
                    == "true"
                )

                bloque.append((
                    insertar_sensor,
                    (
                        sensor_id, mes_anio, fecha, zona_id,
                        caudal, presion, temperatura,
                        calidad, es_anomalia,
                    ),
                ))

                bloque.append((
                    insertar_zona,
                    (
                        zona_id, mes_anio, fecha, sensor_id,
                        caudal, presion, temperatura,
                        calidad, es_anomalia,
                    ),
                ))

                total_mediciones += 1

                if len(bloque) >= TAMANO_BLOQUE * 2:
                    guardar_bloque()

                # Mostrar el avance de la carga
                if total_mediciones % MOSTRAR_CADA == 0:
                    transcurrido = time.perf_counter() - inicio
                    velocidad = (
                        total_mediciones / transcurrido
                        if transcurrido > 0 else 0
                    )

                    print(
                        f"Mediciones procesadas: "
                        f"{total_mediciones:,} | "
                        f"Escrituras confirmadas: "
                        f"{total_escrituras:,} | "
                        f"Velocidad: {velocidad:.0f} "
                        f"mediciones/s",
                        flush=True,
                    )

        guardar_bloque()

        duracion = time.perf_counter() - inicio

        # Comprobar la cantidad de registros
        if total_mediciones != 1_000_000:
            raise RuntimeError(
                "El CSV no contenia exactamente "
                "1.000.000 de mediciones."
            )

        if total_escrituras != 2_000_000:
            raise RuntimeError(
                "La cantidad de escrituras no coincide "
                "con las 2.000.000 esperadas."
            )

        print("\nCarga terminada correctamente.")
        print(f"Mediciones procesadas: {total_mediciones:,}")
        print(f"Escrituras confirmadas: {total_escrituras:,}")
        print(f"Tiempo total: {duracion:.2f} segundos")

        if duracion > 0:
            print(
                "Velocidad media: "
                f"{total_mediciones / duracion:.2f} "
                "mediciones/s"
            )

    finally:
        if cluster is not None:
            cluster.shutdown()


if __name__ == "__main__":
    main()
