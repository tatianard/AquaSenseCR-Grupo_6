# AquaSenseCR

## Instalación y ejecución de ScyllaDB con Docker

AquaSenseCR utiliza **ScyllaDB**, una base de datos NoSQL de columnas anchas (*wide-column*). Mediante **Docker Compose**, cada usuario puede ejecutar su propia instancia local en Windows, macOS o Linux.

### 1. Requisitos previos

- Docker y Docker Compose instalados y funcionando.
- Al menos 8 GB de RAM recomendados.
- Puerto local `9042` disponible.

**Nota:** Si el puerto `9042` está ocupado, se debe liberar o modificar el puerto local en `docker-compose.yml`

### 2. Verificar Docker

```bash
docker --version
docker compose version
docker info
```

### 3. Iniciar ScyllaDB

Desde la carpeta que contiene `docker-compose.yml`

```bash
docker compose config
docker compose up -d
```

### 4. Verificar el funcionamiento

```bash
docker compose ps
docker compose exec scylla nodetool status
```

El nodo debe mostrar el estado `UN` (**Up / Normal**).

### 5. Acceder a ScyllaDB

```bash
docker compose exec scylla cqlsh
```

Para salir:

```sql
EXIT;
```

### 6. Detener y reiniciar

Detener el contenedor:

```bash
docker compose stop
```

Reiniciarlo:

```bash
docker compose start
```

Eliminar el contenedor conservando los datos:

```bash
docker compose down
```

Volver a crearlo:

```bash
docker compose up -d
```
## Creación y verificación del esquema CQL

Se utiliza el archivo `esquema.cql` para crear el *keyspace* `aquasense` y las cuatro tablas de ScyllaDB.

### 1. Ejecutar el esquema

Con Docker Compose iniciado, desde la carpeta en la cual se esté trabajando el proyecto, ejecutar:

```bash
docker compose cp esquema.cql scylla:/tmp/esquema.cql
docker compose exec -T scylla cqlsh -f /tmp/esquema.cql
```

### 2. Verificar las tablas

```bash
docker compose exec -T scylla cqlsh -e "SELECT table_name FROM system_schema.tables WHERE keyspace_name = 'aquasense';"
```
Deben aparecer **cuatro** tablas:

- mediciones_por_sensor
- mediciones_por_zona
- anomalias_por_zona
- resumen_diario_zona

## Ejecución de los scripts de Python

1. Instalar las dependencias

Desde la carpeta raíz del proyecto, ejecutar:

python -m pip install pandas numpy cassandra-driver

2. Verificar la conexión

Con ScyllaDB iniciado y las tablas creadas:

python scripts/probar_conexion.py

3. Generar los datos sintéticos
python scripts/generar_datos.py


Este script genera los archivos CSV dentro de la carpeta data/.

4. Cargar las mediciones
python scripts/cargar_datos.py


Este proceso carga las mediciones en las tablas por sensor y por zona.

5. Generar el resumen diario
python scripts/generar_resumen.py

6. Cargar las anomalías
python scripts/cargar_anomalias.py

7. Ejecutar las pruebas de rendimiento
python scripts/medir_consultas.py


Los resultados de las pruebas se guardan en la carpeta resultados.

Evidencias del proyecto

La carpeta resultados/ contiene archivos relacionados con las evidencias iniciales, la verificación del resumen, las pruebas de recuperación y las métricas de rendimiento de las consultas.

Limitaciones del entorno

La configuración actual utiliza un nodo de ScyllaDB para las pruebas locales. Por tanto, los resultados obtenidos no demuestran por sí solos alta disponibilidad ni tolerancia a la caída de un nodo.
