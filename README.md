# AquaSenseCR

XS0131 - Gestión de Bases de Datos y Análisis de Información

AquaSenseCR simula el monitoreo de una red de agua potable mediante 1 000 sensores distribuidos en 20 zonas. Utiliza **ScyllaDB**,  una base de datos NoSQL de columnas anchas (*wide-column*), para almacenar un millón de mediciones, consultar historiales por sensor y zona, identificar anomalías y generar resúmenes diarios

### Integrantes: 

- David Brenes
- Fernando López
- Catalina Monge
- Tatiana Ramos

## Instalación y ejecución de ScyllaDB con Docker

Mediante **Docker Compose**, cada usuario puede ejecutar su propia instancia local en Windows, macOS o Linux.

### 1. Requisitos previos

- Docker y Docker Compose instalados y funcionando.
- Al menos 8 GB de RAM recomendados.
- Puerto local `9042` disponible.

**Nota:** Si el puerto `9042` está ocupado, se debe liberar o modificar el puerto local en `docker-compose.yml`
Modificar el `docker-compose.yml` implica hacer los ajustes en los siguientes archivos.

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

```bash
python -m pip install scylla-driver
```
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

```bash
python -m pip install scylla-driver pandas numpy
```

### 2. Generar los datos

Ejecutar desde la carpeta principal del proyecto:

```bash
python generar_datos.py
```

### 3. Verificar los resultados

El programa genera:

- 1 000 sensores distribuidos en 20 zonas.
- 1 000 000 de mediciones.
- Aproximadamente un 1 % de anomalías de presión.
- Valores de caudal, presión, temperatura e índice de calidad.

Los archivos se guardan automáticamente en la carpeta `data`:

- `sensores.csv`
- `mediciones.csv`

**Nota:** La carpeta `data` no se incluye en GitHub, ya que los archivos CSV pueden generarse nuevamente ejecutando `generar_datos.py`
Asimismo, la dimensión de los archivos sintéticos excede el límite de tamaño permitido por la plataforma.

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

## Validaciones y evidencias

### 1. Ejecutar las validaciones

Una vez cargados los datos en ScyllaDB, ejecutar:

```bash
python validaciones.py
```

### 2. Pruebas realizadas

- **Consultas por sensor:** últimas mediciones e intervalos temporales.
- **Consultas por zona:** recuperación de mediciones por zona y periodo.
- **Anomalías:** consulta de lecturas anómalas y verificación del umbral de presión.
- **Resúmenes diarios:** consulta y verificación de estadísticas por zona.
- **Particiones:** comprobación de los registros almacenados por sensor, zona y mes.
- **Concurrencia:** comparación de 1 000 escrituras distribuidas entre 20 zonas y 1 000 concentradas en una sola.

### 3. Evidencias generadas

**Nota:** Los resultados se guardan automáticamente en la carpeta `evidencias`:

- `evidencias_iniciales.txt`: información del entorno y resultados de las consultas funcionales.
- `prueba_recuperacion.txt`: verificación de los registros de las cuatro tablas.
- `rendimiento_consultas.csv`: tiempos y estadísticas de las consultas.
- `verificacion_resumen.txt`: ejemplos de resúmenes diarios con sus estadísticas.
- `rendimiento_concurrencia.csv`: resultados de las pruebas de escrituras concurrentes.
