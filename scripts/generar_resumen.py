import csv
import time
from collections import defaultdict
from datetime import date

from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection

ARCHIVO_CSV = "data/mediciones.csv"

# Conexión local con ScyllaDB
class TraductorDireccion:
    def translate(self, address):
        return "127.0.0.1"

def main():
    cluster = None
    inicio = time.perf_counter()

    # Guardar los datos por zona y día
    resumen = defaultdict(
        lambda: {
            "total_mediciones": 0,
            "total_anomalias": 0,
            "presion_maxima": float("-inf"),
            "suma_presion": 0,
            "suma_caudal": 0,
            "suma_calidad": 0,
        }
    )

    try:
        print("Leyendo mediciones.csv...")

        with open(
            ARCHIVO_CSV,
            "r",
            newline="",
            encoding="utf-8-sig",
        ) as archivo:
            lector = csv.DictReader(archivo)

            for fila in lector:
                zona = fila["zona_id"]
                fecha = date.fromisoformat(fila["timestamp"][:10])
                clave = (zona, fecha)

                registro = resumen[clave]
                registro["total_mediciones"] += 1

                if fila["es_anomalia"].strip().lower() == "true":
                    registro["total_anomalias"] += 1

                presion = float(fila["presion"])
                caudal = float(fila["caudal"])
                calidad = float(fila["calidad"])

                registro["presion_maxima"] = max(
                    registro["presion_maxima"], presion
                )

                # Acumular valores para calcular promedios
                registro["suma_presion"] += presion
                registro["suma_caudal"] += caudal
                registro["suma_calidad"] += calidad

        print(f"Grupos diarios calculados: {len(resumen)}")

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

        # Preparar la inserción de los resúmenes
        insertar = session.prepare("""
            INSERT INTO resumen_diario_zona
            (zona_id, fecha, total_mediciones,
             total_anomalias, presion_maxima,
             presion_promedio, caudal_promedio, calidad_promedio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """)

        escrituras = 0

        # Guardar los resúmenes diarios
        for (zona, fecha), datos in sorted(resumen.items()):
            total = datos["total_mediciones"]

            presion_promedio = round(datos["suma_presion"] / total, 2)
            caudal_promedio = round(datos["suma_caudal"] / total, 2)
            calidad_promedio = round(datos["suma_calidad"] / total, 2)

            session.execute(
                insertar,
                (
                    zona,
                    fecha,
                    total,
                    datos["total_anomalias"],
                    datos["presion_maxima"],
                    presion_promedio,
                    caudal_promedio,
                    calidad_promedio,
                ),
            )

            escrituras += 1

        total_resumido = sum(
            datos["total_mediciones"]
            for datos in resumen.values()
        )

        total_anomalias = sum(
            datos["total_anomalias"]
            for datos in resumen.values()
        )

        duracion = time.perf_counter() - inicio

        print("\nResumen diario procesado.")
        print(f"Filas escritas: {escrituras:,}")
        print(f"Tiempo total: {duracion:.2f} segundos")
        print(f"Combinaciones zona-dia: {len(resumen):,}")
        print(f"Mediciones resumidas: {total_resumido:,}")
        print(f"Anomalias resumidas: {total_anomalias:,}")

        # Comprobar los resultados
        if total_resumido != 1_000_000:
            raise RuntimeError(
                "El total resumido no coincide con "
                "1,000,000 mediciones."
            )

        proporcion = total_anomalias / total_resumido

        if not 0.005 <= proporcion <= 0.015:
            raise RuntimeError(
                "La proporcion de anomalias esta fuera "
                "del rango esperado."
            )

        if escrituras != len(resumen):
            raise RuntimeError(
                "La cantidad de escrituras no coincide "
                "con los grupos calculados."
            )

        print("Validaciones del resumen: correctas.")

    finally:
        if cluster is not None:
            cluster.shutdown()



if __name__ == "__main__":
    main()
