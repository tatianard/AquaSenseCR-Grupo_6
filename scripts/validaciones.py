import csv
import math
import platform
import statistics
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from cassandra.cluster import Cluster
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.io.asyncioreactor import AsyncioConnection

REPETICIONES = 30
CALENTAMIENTO = 5
ESCRITURAS_PRUEBA = 1000
CONCURRENCIA = 10
CARPETA_EVIDENCIAS = Path("evidencias")

# Usar la conexion local de Docker
class TraductorDireccion:
    def translate(self, address):
        return "127.0.0.1"

# Guardar las evidencias en archivos
def guardar_texto(nombre, contenido):
    ruta = CARPETA_EVIDENCIAS / nombre
    ruta.write_text(contenido, encoding="utf-8")
    print(f"Guardado: {ruta}")

def guardar_csv(nombre, filas):
    ruta = CARPETA_EVIDENCIAS / nombre
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"Guardado: {ruta}")

# Medir el tiempo de una consulta
def medir_consulta(session, nombre, consulta, parametros, esperado):
    tiempos_ms = []
    preparada = session.prepare(consulta)

    # Calentamiento antes de comenzar las mediciones
    for _ in range(CALENTAMIENTO):
        list(session.execute(preparada, parametros))

    # Medir la consulta 30 veces
    for _ in range(REPETICIONES):
        inicio = time.perf_counter()
        filas = list(session.execute(preparada, parametros))
        tiempos_ms.append((time.perf_counter() - inicio) * 1000)

    if len(filas) != esperado:
        raise RuntimeError(
            f"{nombre}: se esperaban {esperado} filas, pero llegaron {len(filas)}."
        )

    # Calcular las estadisticas de los tiempos
    ordenados = sorted(tiempos_ms)
    indice_p95 = math.ceil(0.95 * len(ordenados)) - 1

    resultado = {
        "consulta": nombre,
        "repeticiones": REPETICIONES,
        "filas_de_ultima_consulta": len(filas),
        "mediana_ms": round(statistics.median(tiempos_ms), 3),
        "promedio_ms": round(statistics.mean(tiempos_ms), 3),
        "desviacion_ms": round(statistics.stdev(tiempos_ms), 3),
        "p95_ms": round(ordenados[indice_p95], 3),
        "minimo_ms": round(min(tiempos_ms), 3),
        "maximo_ms": round(max(tiempos_ms), 3),
    }
    print(
        f"{nombre}: {len(filas)} filas | "
        f"mediana {resultado['mediana_ms']} ms | P95 {resultado['p95_ms']} ms"
    )
    return resultado

def comprobar_datos(session):
    # Contar por partición, sin recorrer tablas completas
    contar_sensor = session.prepare("""
        SELECT COUNT(*) FROM mediciones_por_sensor
        WHERE sensor_id = ? AND mes_anio = ?
    """)
    contar_zona = session.prepare("""
        SELECT COUNT(*) FROM mediciones_por_zona
        WHERE zona_id = ? AND mes_anio = ?
    """)
    contar_anomalias = session.prepare("""
        SELECT COUNT(*) FROM anomalias_por_zona
        WHERE zona_id = ? AND mes_anio = ?
    """)
    resumen_zona = session.prepare("""
        SELECT fecha, total_mediciones, total_anomalias
        FROM resumen_diario_zona WHERE zona_id = ?
    """)

    # Verificar los sensores de enero y febrero
    print("\nVerificando mediciones por sensor...")
    total_sensor = 0
    for numero in range(1, 1001):
        sensor = f"S{numero:04d}"
        for mes, esperado in (("2026-01", 744), ("2026-02", 256)):
            cantidad = session.execute(contar_sensor, (sensor, mes)).one()[0]
            if cantidad != esperado:
                raise RuntimeError(f"Cantidad incorrecta para {sensor}, {mes}.")
            total_sensor += cantidad

    # Verificar las 20 zonas y contar las anomalias
    print("Verificando mediciones por zona y anomalías...")
    total_zona = 0
    total_anomalias = 0
    for numero in range(1, 21):
        zona = f"Z{numero:02d}"
        for mes, esperado in (("2026-01", 37200), ("2026-02", 12800)):
            cantidad = session.execute(contar_zona, (zona, mes)).one()[0]
            if cantidad != esperado:
                raise RuntimeError(f"Cantidad incorrecta para {zona}, {mes}.")
            total_zona += cantidad
            total_anomalias += session.execute(contar_anomalias, (zona, mes)).one()[0]

    # Comprobar los 42 dias de cada zona
    print("Verificando resúmenes diarios...")
    total_resumen = 0
    mediciones_resumidas = 0
    anomalias_resumidas = 0
    for numero in range(1, 21):
        zona = f"Z{numero:02d}"
        filas = list(session.execute(resumen_zona, (zona,)))
        if len(filas) != 42:
            raise RuntimeError(f"La zona {zona} no tiene 42 resúmenes.")
        total_resumen += len(filas)
        mediciones_resumidas += sum(f.total_mediciones for f in filas)
        anomalias_resumidas += sum(f.total_anomalias for f in filas)

    # Revisar los totales antes de guardar la evidencia
    if (total_sensor, total_zona, total_anomalias, total_resumen) != (
        1_000_000, 1_000_000, 10_000, 840
    ):
        raise RuntimeError("Los totales de las tablas no coinciden con lo esperado.")
    if (mediciones_resumidas, anomalias_resumidas) != (1_000_000, 10_000):
        raise RuntimeError("Los totales de los resúmenes no coinciden.")

    datos = {
        "mediciones_por_sensor": total_sensor,
        "mediciones_por_zona": total_zona,
        "anomalias_por_zona": total_anomalias,
        "resumen_diario_zona": total_resumen,
    }

    contenido = (
        "VERIFICACION DE DATOS - AquaSenseCR\n"
        "Conteos realizados por claves de particion conocidas.\n\n"
        f"mediciones_por_sensor: {total_sensor:,} filas\n"
        f"mediciones_por_zona: {total_zona:,} filas\n"
        f"anomalias_por_zona: {total_anomalias:,} filas\n"
        f"resumen_diario_zona: {total_resumen:,} filas\n"
        f"Mediciones representadas en resumen: {mediciones_resumidas:,}\n"
        f"Anomalias representadas en resumen: {anomalias_resumidas:,}\n"
    )
    guardar_texto("prueba_recuperacion.txt", contenido)

    print("Totales verificados correctamente.")
    return datos

# Guardar una muestra de los resumenes diarios
def verificar_resumen(session):
    # Consultar las últimas cinco fechas de Z01.
    filas = list(session.execute("""
        SELECT zona_id, fecha, total_mediciones, total_anomalias,
               presion_maxima, presion_promedio, caudal_promedio,
               calidad_promedio
        FROM resumen_diario_zona
        WHERE zona_id = 'Z01'
        LIMIT 5
    """))
    if len(filas) != 5:
        raise RuntimeError("No se encontraron los cinco resúmenes de Z01.")
    for fila in filas:
        if (fila.presion_promedio is None or fila.caudal_promedio is None
                or fila.calidad_promedio is None):
            raise RuntimeError("Faltan promedios en el resumen diario.")

    lineas = [
        "VERIFICACION DE RESUMENES - AquaSenseCR",
        "Total de filas: 840 (verificado en prueba_recuperacion.txt)",
        "",
        "Ultimos cinco resumenes de Z01:",
        "fecha | mediciones | anomalias | presion_maxima | "
        "presion_promedio | caudal_promedio | calidad_promedio",
    ]
    for fila in filas:
        lineas.append(
            f"{fila.fecha} | {fila.total_mediciones} | "
            f"{fila.total_anomalias} | {fila.presion_maxima:.2f} | "
            f"{fila.presion_promedio:.2f} | {fila.caudal_promedio:.2f} | "
            f"{fila.calidad_promedio:.2f}"
        )
    guardar_texto("verificacion_resumen.txt", "\n".join(lineas) + "\n")

def probar_concurrencia(session):
    # Tabla auxiliar: las tablas principales no se modifican
    tabla = "prueba_validaciones_" + uuid.uuid4().hex[:8]
    creada = False
    resultados = []
    try:
        session.execute(f"""
            CREATE TABLE {tabla} (
                zona_id text, mes_anio text, timestamp timestamp,
                sensor_id text, presion double,
                PRIMARY KEY ((zona_id, mes_anio), timestamp, sensor_id)
            ) WITH CLUSTERING ORDER BY (timestamp DESC, sensor_id ASC)
        """)
        creada = True
        insertar = session.prepare(f"""
            INSERT INTO {tabla}
            (zona_id, mes_anio, timestamp, sensor_id, presion)
            VALUES (?, ?, ?, ?, ?)
        """)
        contar = session.prepare(f"""
            SELECT COUNT(*) FROM {tabla}
            WHERE zona_id = ? AND mes_anio = ?
        """)

        # Comparar escrituras repartidas y concentradas
        for escenario in ("distribuido", "concentrado"):
            mes = "2030-01" if escenario == "distribuido" else "2030-02"
            fecha = datetime(2030, 1 if escenario == "distribuido" else 2, 1)
            parametros = []
            for i in range(ESCRITURAS_PRUEBA):
                zona = f"Z{(i % 20) + 1:02d}" if escenario == "distribuido" else "Z01"
                parametros.append((
                    zona, mes, fecha + timedelta(seconds=i),
                    f"S{(i % 1000) + 1:04d}", 3.5
                ))

            # Enviar hasta 10 escrituras al mismo tiempo
            inicio = time.perf_counter()
            respuestas = execute_concurrent_with_args(
                session, insertar, parametros,
                concurrency=CONCURRENCIA,
                raise_on_first_error=False,
            )
            duracion = time.perf_counter() - inicio
            errores = [r for correcto, r in respuestas if not correcto]
            if errores:
                raise RuntimeError(f"Fallaron {len(errores)} escrituras: {errores[0]}")
            # Revisar que todas las escrituras se guardaron
            zonas = [f"Z{i:02d}" for i in range(1, 21)] if escenario == "distribuido" else ["Z01"]
            for zona in zonas:
                cantidad = session.execute(contar, (zona, mes)).one()[0]
                esperado = ESCRITURAS_PRUEBA // 20 if escenario == "distribuido" else ESCRITURAS_PRUEBA
                if cantidad != esperado:
                    raise RuntimeError(f"Conteo incorrecto en {zona}: {cantidad}.")

            velocidad = ESCRITURAS_PRUEBA / duracion
            resultados.append({
                "escenario": escenario,
                "escrituras": ESCRITURAS_PRUEBA,
                "particiones": len(zonas),
                "concurrencia": CONCURRENCIA,
                "segundos": round(duracion, 3),
                "escrituras_por_segundo": round(velocidad, 2),
            })
            print(
                f"{escenario}: {ESCRITURAS_PRUEBA} escrituras, "
                f"{velocidad:.2f} escrituras/s"
            )
        return resultados
    finally:
        # Eliminar la tabla usada solo para la prueba
        if creada:
            try:
                session.execute(f"DROP TABLE {tabla}")
                print("Tabla auxiliar eliminada.")
            except Exception as error:
                print(f"ADVERTENCIA: eliminar manualmente {tabla}: {error}")

# Guardar un resumen corto de las validaciones
def guardar_evidencia_inicial(session, totales, rendimiento):
    lineas = [
        "AquaSenseCR - EVIDENCIAS INICIALES",
        f"Fecha de validacion: {datetime.now():%Y-%m-%d %H:%M:%S}",
        "Tecnologia: ScyllaDB",
        f"Equipo: {platform.platform()} | Python {platform.python_version()}",
        "",
        "VERIFICACION DE DATOS",
        f"mediciones_por_sensor: {totales['mediciones_por_sensor']:,} filas",
        f"mediciones_por_zona: {totales['mediciones_por_zona']:,} filas",
        f"anomalias_por_zona: {totales['anomalias_por_zona']:,} filas",
        f"resumen_diario_zona: {totales['resumen_diario_zona']:,} filas",
        "",
        "CONSULTAS FUNCIONALES",
    ]
    for fila in rendimiento:
        lineas.append(f"{fila['consulta']}: correcta ({fila['filas_de_ultima_consulta']} filas)")
    guardar_texto("evidencias_iniciales.txt", "\n".join(lineas) + "\n")

# Ejecutar las consultas y guardar los resultados
def main():
    CARPETA_EVIDENCIAS.mkdir(exist_ok=True)
    cluster = None
    try:
        cluster = Cluster(
            ["127.0.0.1"], port=9042,
            connection_class=AsyncioConnection,
            address_translator=TraductorDireccion(),
            connect_timeout=10, control_connection_timeout=10,
        )
        session = cluster.connect("aquasense")
        print("Conexión correcta con ScyllaDB.")
        print(f"Repeticiones: {REPETICIONES} | Calentamiento: {CALENTAMIENTO}")

        # Consultas principales del proyecto
        resultados = []
        resultados.append(medir_consulta(
            session, "ultimas_mediciones_sensor",
            """SELECT sensor_id, timestamp, caudal, presion
               FROM mediciones_por_sensor
               WHERE sensor_id = ? AND mes_anio = ? LIMIT 20""",
            ("S0001", "2026-02"), 20,
        ))
        resultados.append(medir_consulta(
            session, "intervalo_temporal_sensor",
            """SELECT sensor_id, timestamp, caudal, presion
               FROM mediciones_por_sensor
               WHERE sensor_id = ? AND mes_anio = ?
                 AND timestamp >= ? AND timestamp < ?""",
            ("S0001", "2026-01", datetime(2026, 1, 1), datetime(2026, 1, 3)), 48,
        ))
        resultados.append(medir_consulta(
            session, "intervalo_temporal_zona",
            """SELECT zona_id, timestamp, sensor_id, caudal, presion
               FROM mediciones_por_zona
               WHERE zona_id = ? AND mes_anio = ?
                 AND timestamp >= ? AND timestamp < ?""",
            ("Z01", "2026-01", datetime(2026, 1, 1), datetime(2026, 1, 2)), 1200,
        ))
        resultados.append(medir_consulta(
            session, "anomalias_zona",
            """SELECT sensor_id, timestamp, presion, calidad
               FROM anomalias_por_zona
               WHERE zona_id = ? AND mes_anio = ? LIMIT 20""",
            ("Z01", "2026-01"), 20,
        ))
        # Revisar que las anomalías de esta muestra tengan presión alta
        filas = session.execute("""
            SELECT presion FROM anomalias_por_zona
            WHERE zona_id = 'Z01' AND mes_anio = '2026-01' LIMIT 20
        """)
        if any(fila.presion <= 6.0 for fila in filas):
            raise RuntimeError("Hay anomalías con presión de 6.0 o menos.")

        resultados.append(medir_consulta(
            session, "resumen_diario_zona",
            """SELECT zona_id, fecha, total_mediciones, total_anomalias,
                      presion_maxima, presion_promedio, caudal_promedio,
                      calidad_promedio
               FROM resumen_diario_zona
               WHERE zona_id = ? AND fecha >= ? AND fecha <= ?""",
            ("Z01", date(2026, 1, 1), date(2026, 2, 11)), 42,
        ))
        guardar_csv("rendimiento_consultas.csv", resultados)

        totales = comprobar_datos(session)
        verificar_resumen(session)
        guardar_evidencia_inicial(session, totales, resultados)

        print("\nPrueba corta de concurrencia:")
        concurrencia = probar_concurrencia(session)
        guardar_csv("rendimiento_concurrencia.csv", concurrencia)
        print("\nTodas las validaciones terminaron correctamente.")
        print("Resultados guardados en la carpeta evidencias/.")
    finally:
        if cluster is not None:
            cluster.shutdown()

if __name__ == "__main__":
    main()