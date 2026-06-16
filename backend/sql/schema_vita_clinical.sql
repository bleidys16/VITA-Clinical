-- ============================================================
-- Script SQL - Esquema de Base de Datos VITA Clinical
-- Motor: PostgreSQL 16
-- Generado a partir de modelos Django (ORM)
-- Fecha: Junio 2026
-- ============================================================

-- Extensión para UUID (opcional, para IDs universales)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- TABLA: auth_user (propia de Django, se incluye como referencia)
-- ============================================================
CREATE TABLE auth_user (
    id              SERIAL PRIMARY KEY,
    password        VARCHAR(128) NOT NULL,
    last_login      TIMESTAMPTZ,
    is_superuser    BOOLEAN NOT NULL DEFAULT FALSE,
    username        VARCHAR(150) NOT NULL UNIQUE,
    first_name      VARCHAR(150) NOT NULL DEFAULT '',
    last_name       VARCHAR(150) NOT NULL DEFAULT '',
    email           VARCHAR(254) NOT NULL DEFAULT '',
    is_staff        BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    date_joined     TIMESTAMPTZ NOT NULL
);

-- ============================================================
-- TABLA: etl_paciente
-- Registros clínicos de pacientes con antropometría,
-- signos vitales, antecedentes y clasificación de riesgo.
-- ============================================================
CREATE TABLE etl_paciente (
    id_paciente             INTEGER PRIMARY KEY,
    nombres                 VARCHAR(150) NOT NULL,
    apellidos               VARCHAR(150) NOT NULL,
    edad                    INTEGER NOT NULL,
    sexo                    VARCHAR(20) NOT NULL,

    -- Antropometría
    peso                    DOUBLE PRECISION,
    altura                  DOUBLE PRECISION,
    imc                     DOUBLE PRECISION,
    clasificacion_imc       VARCHAR(50),

    -- Signos vitales y paraclínicos
    presion_sistolica       INTEGER,
    presion_diastolica      INTEGER,
    frecuencia_cardiaca     INTEGER,
    glucosa                 DOUBLE PRECISION,
    colesterol              DOUBLE PRECISION,
    saturacion_oxigeno      DOUBLE PRECISION,
    temperatura             DOUBLE PRECISION,

    -- Antecedentes y estilo de vida
    antecedentes_familiares BOOLEAN NOT NULL DEFAULT FALSE,
    fumador                 BOOLEAN NOT NULL DEFAULT FALSE,
    consumo_alcohol         BOOLEAN NOT NULL DEFAULT FALSE,
    actividad_fisica        VARCHAR(50),

    -- Diagnóstico y riesgo
    diagnostico_preliminar  VARCHAR(250),
    riesgo_enfermedad       VARCHAR(50),
    fecha_consulta          DATE
);

-- Índices para búsquedas frecuentes
CREATE INDEX idx_paciente_edad        ON etl_paciente (edad);
CREATE INDEX idx_paciente_sexo        ON etl_paciente (sexo);
CREATE INDEX idx_paciente_riesgo      ON etl_paciente (riesgo_enfermedad);
CREATE INDEX idx_paciente_imc         ON etl_paciente (imc);
CREATE INDEX idx_paciente_consulta    ON etl_paciente (fecha_consulta);

-- ============================================================
-- TABLA: etl_perfil
-- Perfiles de usuario con roles:
--   ADMIN   → Acceso total
--   MEDICO  → Solo lectura
--   ANALISTA→ ETL + Machine Learning
-- ============================================================
CREATE TABLE etl_perfil (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
    rol         VARCHAR(15) NOT NULL DEFAULT 'MEDICO'
                CHECK (rol IN ('ADMIN', 'MEDICO', 'ANALISTA'))
);

CREATE INDEX idx_perfil_rol ON etl_perfil (rol);

-- ============================================================
-- TABLA: etl_historialetl
-- Auditoría de ejecuciones del pipeline ETL.
-- ============================================================
CREATE TABLE etl_historialetl (
    id                      SERIAL PRIMARY KEY,
    fecha                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usuario_id              INTEGER REFERENCES auth_user(id) ON DELETE SET NULL,
    registros_procesados    INTEGER NOT NULL,
    errores_encontrados     INTEGER NOT NULL DEFAULT 0,
    tiempo_ejecucion        DOUBLE PRECISION NOT NULL,
    estado                  VARCHAR(50) NOT NULL CHECK (estado IN ('Exitoso', 'Fallido'))
);

CREATE INDEX idx_historial_fecha   ON etl_historialetl (fecha DESC);
CREATE INDEX idx_historial_estado  ON etl_historialetl (estado);

-- ============================================================
-- TABLA: etl_etltask
-- Estado de tareas ETL en tiempo real (para el frontend).
-- ============================================================
CREATE TABLE etl_etltask (
    id          SERIAL PRIMARY KEY,
    task_id     VARCHAR(64) NOT NULL UNIQUE,
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    fase        VARCHAR(32) NOT NULL DEFAULT '',
    mensaje     TEXT NOT NULL DEFAULT '',
    detalle     TEXT NOT NULL DEFAULT '',
    logs        JSONB NOT NULL DEFAULT '[]',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_etltask_activo   ON etl_etltask (activo);
CREATE INDEX idx_etltask_created  ON etl_etltask (created_at DESC);

-- ============================================================
-- TABLA: etl_dashboardkpis
-- Snapshots de KPIs calculados después de cada ETL.
-- ============================================================
CREATE TABLE etl_dashboardkpis (
    id                          SERIAL PRIMARY KEY,
    fecha_calculo               TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- KPIs de control
    total_registros             INTEGER NOT NULL DEFAULT 0,
    pacientes_criticos          INTEGER NOT NULL DEFAULT 0,
    pacientes_hipertensos       INTEGER NOT NULL DEFAULT 0,
    pacientes_diabeticos        INTEGER NOT NULL DEFAULT 0,
    pacientes_fumadores         INTEGER NOT NULL DEFAULT 0,
    pacientes_obesos            INTEGER NOT NULL DEFAULT 0,
    pacientes_antecedentes      INTEGER NOT NULL DEFAULT 0,
    pacientes_alcohol           INTEGER NOT NULL DEFAULT 0,
    pacientes_saturacion_baja   INTEGER NOT NULL DEFAULT 0,
    riesgo_promedio             DOUBLE PRECISION NOT NULL DEFAULT 0.0,

    -- Alertas clínicas
    alertas_sistolica           INTEGER NOT NULL DEFAULT 0,
    alertas_glucosa             INTEGER NOT NULL DEFAULT 0,
    alertas_saturacion          INTEGER NOT NULL DEFAULT 0,

    -- Estadística descriptiva
    edad_media                  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    edad_mediana                DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    edad_moda                   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    edad_desviacion             DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    glucosa_media               DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    glucosa_desviacion          DOUBLE PRECISION NOT NULL DEFAULT 0.0
);

CREATE INDEX idx_kpis_fecha ON etl_dashboardkpis (fecha_calculo DESC);

-- ============================================================
-- TABLA: etl_metricasmodeloml
-- Métricas de los modelos de Machine Learning entrenados.
-- ============================================================
CREATE TABLE etl_metricasmodeloml (
    id                      SERIAL PRIMARY KEY,
    fecha_entrenamiento     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Métricas de rendimiento
    accuracy                DOUBLE PRECISION NOT NULL,
    precision               DOUBLE PRECISION NOT NULL,
    recall                  DOUBLE PRECISION NOT NULL,
    f1_score                DOUBLE PRECISION NOT NULL,

    -- Matriz de confusión 2x2 en formato JSON
    -- {"vp": N, "fp": N, "fn": N, "vn": N}
    matriz_confusion        JSONB NOT NULL,

    -- Modelo activo (último entrenado)
    modelo_activo           BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_ml_fecha   ON etl_metricasmodeloml (fecha_entrenamiento DESC);
CREATE INDEX idx_ml_activo  ON etl_metricasmodeloml (modelo_activo);
