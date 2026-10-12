-- Consultas de anomalías y resúmenes de AquaSenseCR

USE aquasense;

-- A. Anomalías por zona

-- Consultar las primeras 5 anomalías de Z01 en enero
SELECT sensor_id, zona_id, timestamp, presion, calidad
FROM anomalias_por_zona
WHERE zona_id = 'Z01'
  AND mes_anio = '2026-01'
LIMIT 5;

-- Contar las anomalías de Z01 durante enero
SELECT COUNT(*)
FROM anomalias_por_zona
WHERE zona_id = 'Z01'
  AND mes_anio = '2026-01';

-- B. Resúmenes diarios por zona

-- Consultar las estadísticas de Z01 para el 15 de enero
SELECT *
FROM resumen_diario_zona
WHERE zona_id = 'Z01'
  AND fecha = '2026-01-15';

-- Contar los días con resúmenes registrados en Z01
SELECT COUNT(*)
FROM resumen_diario_zona
WHERE zona_id = 'Z01';