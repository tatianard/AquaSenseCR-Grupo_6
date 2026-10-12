-- Consultas de prueba de AquaSenseCR

USE aquasense;

-- A. Consultar mediciones de un sensor
SELECT sensor_id, zona_id, timestamp, presion, calidad, es_anomalia
FROM mediciones_por_sensor
WHERE sensor_id = 'S0001'
  AND mes_anio = '2026-01'
LIMIT 5;

-- B. Consultar mediciones de una zona
SELECT sensor_id, zona_id, timestamp, presion, calidad, es_anomalia
FROM mediciones_por_zona
WHERE zona_id = 'Z01'
  AND mes_anio = '2026-01'
LIMIT 5;

-- C. Contar mediciones de un sensor en enero
SELECT COUNT(*)
FROM mediciones_por_sensor
WHERE sensor_id = 'S0001'
  AND mes_anio = '2026-01';

-- D. Contar mediciones de un sensor en febrero
SELECT COUNT(*)
FROM mediciones_por_sensor
WHERE sensor_id = 'S0001'
  AND mes_anio = '2026-02';

-- E. Contar mediciones de una zona en enero
SELECT COUNT(*)
FROM mediciones_por_zona
WHERE zona_id = 'Z01'
  AND mes_anio = '2026-01';

-- F. Contar mediciones de una zona en febrero
SELECT COUNT(*)
FROM mediciones_por_zona
WHERE zona_id = 'Z01'
  AND mes_anio = '2026-02';