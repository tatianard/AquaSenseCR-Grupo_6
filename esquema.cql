-- Esquema CQL
-- Generación de las tablas para el funcionamiento de AquaSenseCR

-- A. Generación del KEYSPACE
-- Se refiere al espacio donde se organizan las tablas en ScyllaDB
-- Se utiliza el keyspace aquasense, independiente del nombre del proyecto Docker.

CREATE KEYSPACE IF NOT EXISTS aquasense
WITH replication = {
    'class': 'NetworkTopologyStrategy',
    'replication_factor': 1
};

USE aquasense;

-- B. Tabla MEDICIONES POR SENSOR
-- Se establece un sistema de partición por sensor y mes
-- Se definen las variables de interés, el tipo de cada una 
-- Así como claves primarias y el ordenamiento de los datos

CREATE TABLE IF NOT EXISTS mediciones_por_sensor (
    sensor_id text,
    mes_anio text,
    timestamp timestamp,
    zona_id text,
    caudal double,
    presion double,
    temperatura double,
    calidad text,
    es_anomalia boolean,
    PRIMARY KEY ((sensor_id, mes_anio), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);

-- C. Tabla MEDICIONES POR ZONA
-- Se organiza por zona y por mes
-- También se contempla un id para garantizar la trazabilidad de las lecturas por sensor
-- Se proponen las variables de interés para el caso, al igual que su tipo
-- Se establecen llaves primarias y organización

CREATE TABLE IF NOT EXISTS mediciones_por_zona (
    zona_id text,
    mes_anio text,
    timestamp timestamp,
    sensor_id text,
    caudal double,
    presion double,
    temperatura double,
    calidad text,
    es_anomalia boolean,
    PRIMARY KEY ((zona_id, mes_anio), timestamp, sensor_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, sensor_id ASC);

-- D. Tabla ANOMALIAS POR ZONA
-- Se trata de una tabla derivada
-- Únicamente recopila aquellos registros modelados como anómalos
-- Igualmente se definen las variables, el tipo, las claves primarias y la organización
-- Pretende facilitar la consulta de este tipo de lecturas

CREATE TABLE IF NOT EXISTS anomalias_por_zona (
    zona_id text,
    mes_anio text,
    timestamp timestamp,
    sensor_id text,
    presion double,
    caudal double,
    temperatura double,
    calidad text,
    PRIMARY KEY ((zona_id, mes_anio), timestamp, sensor_id)
) WITH CLUSTERING ORDER BY (timestamp DESC, sensor_id ASC);

-- E. Tabla RESUMEN DIARIO POR ZONA
-- También es una tabla derivada
-- Permite consultar estadísticas básicas sin recurrir a los datos originales
-- Así, se facilita una aproximación inicial a la información de AquaSenseCR

CREATE TABLE IF NOT EXISTS resumen_diario_zona (
    zona_id text,
    fecha date,
    total_mediciones bigint,
    total_anomalias bigint,
    presion_maxima double,
    PRIMARY KEY (zona_id, fecha)
) WITH CLUSTERING ORDER BY (fecha DESC);
