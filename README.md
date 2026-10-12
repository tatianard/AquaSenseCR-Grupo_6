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

## Verificación de la conexión con Python

Este proyecto utiliza Python para conectarse a ScyllaDB y ejecutar las operaciones de carga y consulta.

### 1. Requisitos previos

- Python y la librería `scylla-driver` deben estar instalados.

### 2. Probar la conexión

Desde la carpeta principal del proyecto, ejecutar:

```bash
python probar_conexion.py
```

### 3. Verificar el resultado

Si la conexión funciona correctamente, se mostrará una salida que incluye:

```text
Conectando con ScyllaDB...
CONEXION CORRECTA
Keyspaces encontrados:
- aquasense
```
## Generación de datos sintéticos

Mediante `generar_datos.py` se simulan las mediciones sintéticas de los sensores de agua potable.

### 1. Requisitos previos

- Python instalado y funcionando.
- Librerías `scylla-driver`, `pandas` y `numpy` instaladas.

### 2. Generar los datos

Ejecutar desde la carpeta principal del proyecto:

```bash
python generar_datos.py
```

### 2. Verificar los resultados

El programa genera:

- 1 000 sensores distribuidos en 20 zonas.
- 1 000 000 de mediciones.
- Aproximadamente un 1 % de anomalías de presión.
- Valores de caudal, presión, temperatura e índice de calidad.

Los archivos se guardan automáticamente en la carpeta `data`:

- `sensores.csv`
- `mediciones.csv`

## Carga de datos y consultas de prueba

### 1. Cargar las mediciones

Una vez generados los CSV, ejecutar desde la carpeta principal del proyecto:

```bash
python cargar_datos.py
```

El programa carga 1 000 000 de mediciones en las tablas `mediciones_por_sensor` y `mediciones_por_zona`, realizando 2 000 000 de escrituras.

### 2. Verificar los datos almacenados

Para ejecutar las consultas del archivo `consultas_rev.cql`:

**Nota:** Las consultas se realizan directamente sobre las tablas de ScyllaDB, no sobre los CSV. Es importante haber seguido los pasos anteriores.

```bash
docker compose cp consultas_rev.cql scylla:/tmp/consultas_rev.cql
docker compose exec -T scylla cqlsh -f /tmp/consultas_rev.cql
```
## Carga de anomalías y generación de resúmenes

Es necesario contar con el archivo `mediciones.csv` en la carpeta local del proyecto

### 1. Cargar las anomalías

Una vez cargadas las mediciones en ScyllaDB, ejecutar:

```bash
python cargar_anomalias.py
```
El programa selecciona las mediciones anómalas del CSV y las almacena en la tabla `anomalias_por_zona`.

### 2. Generar los resúmenes diarios

Ejecutar:

```bash
python generar_resumen.py
```
El programa calcula las estadísticas diarias por zona y las almacena en `resumen_diario_zona`, incluyendo mediciones, anomalías y valores de presión, caudal y calidad.

### 3. Verificar los datos cargados a las tablas derivadas

Para ejecutar las consultas guardadas en `consultas_anomaresu.cql`:

```bash
docker compose cp consultas_anomaresu.cql scylla:/tmp/consultas_anomaresu.cql
docker compose exec -T scylla cqlsh -f /tmp/consultas_anomaresu.cql
```

**Nota:** Al igual que en el caso anterior, las consultas de verificación se realizan directamente sobre las tablas ScyllaDB y no del CSV. 









### 3. Ejecución de los scripts de Python

## A. Instalar las dependencias

Desde la carpeta raíz del proyecto, ejecutar:

python -m pip install pandas numpy cassandra-driver

## B. Verificar la conexión

Con ScyllaDB iniciado y las tablas creadas:

python scripts/probar_conexion.py

## C. Generar los datos sintéticos
python scripts/generar_datos.py


Este script genera los archivos CSV dentro de la carpeta data/.

## D. Cargar las mediciones
python scripts/cargar_datos.py


Este proceso carga las mediciones en las tablas por sensor y por zona.

## E. Generar el resumen diario
python scripts/generar_resumen.py

## F. Cargar las anomalías
python scripts/cargar_anomalias.py

## G. Ejecutar las pruebas de rendimiento
python scripts/medir_consultas.py

Los resultados de las pruebas se guardan en la carpeta resultados/.

### Evidencias del proyecto

La carpeta resultados contiene archivos relacionados con las evidencias iniciales, la verificación del resumen, las pruebas de recuperación y las métricas de rendimiento de las consultas.

### Limitaciones del entorno

La configuración actual utiliza un nodo de ScyllaDB para las pruebas locales. Por tanto, los resultados obtenidos no demuestran por sí solos alta disponibilidad ni tolerancia a la caída de un nodo.
