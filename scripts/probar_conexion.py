from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection

# Permite conectarse al nodo local sin depender de la IP interna de Docker.
class TraductorDireccion:
    def translate(self, address):
        return "127.0.0.1"

cluster = None

try:
    # Configuración de la conexión con ScyllaDB.
    cluster = Cluster(
        ["127.0.0.1"],
        port=9042,
        connection_class=AsyncioConnection,
        address_translator=TraductorDireccion(),
        connect_timeout=5,
        control_connection_timeout=5,
    )

    print("Conectando con ScyllaDB...")
    session = cluster.connect("aquasense")

    # Consulta sencilla para comprobar que la conexión funciona.
    filas = session.execute(
        "SELECT keyspace_name FROM system_schema.keyspaces"
    )

    print("CONEXION CORRECTA")
    print("Keyspaces encontrados:")

    for fila in filas:
        print("-", fila.keyspace_name)

except Exception as error:
    print("ERROR DE CONEXION:", repr(error))

finally:
    # Cierra la conexión al finalizar la prueba.
    if cluster is not None:
        cluster.shutdown()
