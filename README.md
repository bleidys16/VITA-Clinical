# VITA Clinical

**Vital Tracking in Healthcare Analytics** — Plataforma inteligente de analítica clínica para la detección y clasificación de riesgo médico.

VITA Clinical es una aplicación web FullStack que automatiza el procesamiento de datos clínicos mediante un pipeline ETL completo, analítica estadística y modelos de Machine Learning para predecir y clasificar el riesgo médico de pacientes.

---

## Tabla de contenidos

- [Descripción general](#descripción-general)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura](#arquitectura)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación local](#instalación-local)
- [Variables de entorno](#variables-de-entorno)
- [Flujo de uso](#flujo-de-uso)
- [API REST](#api-rest)
- [Roles y permisos](#roles-y-permisos)
- [Módulo ETL](#módulo-etl)
- [Módulo Machine Learning](#módulo-machine-learning)
- [Despliegue en producción](#despliegue-en-producción)

---

## Descripción general

La IPS recibe diariamente miles de registros clínicos con inconsistencias: campos vacíos, duplicados, valores fuera de rango y errores ortográficos en diagnósticos. VITA Clinical resuelve esto con:

- **ETL automatizado** que extrae, limpia y carga el dataset clínico en base de datos con trazabilidad completa.
- **Dashboard clínico** con KPIs en tiempo real: pacientes críticos, hipertensos, diabéticos, distribución de IMC y segmentación por edad y sexo.
- **Modelo RandomForest** entrenado sobre datos reales para predecir el nivel de riesgo (Bajo / Medio / Alto / Crítico) de cada paciente.
- **Exportación de reportes** en PDF, Excel y CSV.
- **Control de acceso por roles** (Administrador, Médico, Analista) con autenticación JWT y sidebar adaptativo.
- **Clasificador de sexo por nombre** con soporte de tildes, aplicado en ETL y en datos existentes.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 · Django 5.x · Django REST Framework |
| Autenticación | djangorestframework-simplejwt |
| ETL | Pandas · NumPy · OpenPyXL |
| Machine Learning | scikit-learn (RandomForestClassifier) · joblib |
| Base de datos | PostgreSQL |
| Frontend | HTML5 · Bootstrap 5 · ApexCharts · Vanilla JS |
| Exportación | ReportLab (PDF) · OpenPyXL (Excel) |
| Servidor producción | Gunicorn · WhiteNoise |

---

## Arquitectura

```
vita-clinical/
│
├── frontend/                    ← Capa de presentación
│   ├── templates/               ← login.html · base.html · dashboard.html
│   │                            ← pacientes.html · ml_modeling.html
│   └── static/
│       ├── css/                 ← custom.css · dashboard.css
│       └── js/                  ← auth.js · dashboard_render.js
│                                ← etl_worker.js · pacientes.js
│
├── backend/                     ← Monolito Django (sirve frontend + API)
│   ├── config/                  ← settings.py · urls.py · wsgi.py
│   └── apps/
│       ├── authentication/      ← LoginView · ProfileUpdateView
│       │                        ← permissions.py (roles: Admin/Medico/Analista)
│       └── etl/
│           ├── models.py        ← Paciente · HistorialETL · ETLTask
│           │                    ← DashboardKPIs · MetricasModeloML · Perfil
│           ├── services.py      ← PipelineETL (Extract · Transform · Load)
│           ├── tasks.py         ← ejecutar_pipeline (threading, no Celery)
│           ├── analytics.py     ← calcular_analitica_dataset · riesgo
│           ├── clasificador_sexo.py ← Mapeo nombre → género
│           ├── views.py         ← ReportesView · RunETLView · PacienteListView
│           │                    ← DashboardKPIView · ML views
│           └── management/commands/
│               ├── ejecutar_etl.py
│               ├── crear_usuarios_base.py
│               └── corregir_sexo.py
│   ├── build.sh                 ← Script de build para Render
│   └── requirements.txt
│
└── datasets/
    └── dataset_clinico_etl_1800_registros.xlsx
```

**Flujo de datos:**

```
Dataset (.xlsx / .csv)
      ↓
  EXTRACT → Lee archivo local o subido por el usuario
      ↓
  TRANSFORM → Limpieza · Estandarización sexo por nombre ·
               Cálculo IMC · Clasificación de riesgo
      ↓
  LOAD → bulk_create atómico en PostgreSQL + registro en HistorialETL
      ↓
  ML → RandomForest entrenado sobre datos limpios → Predicción por paciente
      ↓
  Dashboard → KPIs · Gráficas ApexCharts · Exportación PDF/Excel/CSV
```

---

## Estructura del proyecto

```
backend/
├── config/
│   ├── settings.py              ← Configuración Django (DB, CORS, JWT, etc.)
│   ├── urls.py                  ← Rutas raíz
│   └── wsgi.py                  ← WSGI para Gunicorn
│
├── apps/
│   ├── authentication/
│   │   ├── views.py             ← LoginView · ProfileUpdateView
│   │   ├── permissions.py       ← IsAdministrador · IsMedico · IsAnalista
│   │   │                           EsAdminOMedico · EsAdminOAnalista
│   │   └── serializers.py       ← Auth serializers con rol_display
│   │
│   └── etl/
│       ├── models.py            ← Paciente (20+ campos clínicos)
│       │                           HistorialETL · ETLTask · DashboardKPIs
│       │                           MetricasModeloML · Perfil
│       ├── serializers.py       ← Reportes serializers
│       ├── services.py          ← PipelineETL (extract · transform · load)
│       ├── tasks.py             ← ejecutar_pipeline (threading con ETLTask)
│       ├── analytics.py         ← calcular_analitica_dataset
│       ├── clasificador_sexo.py ← ~600 nombres mapeados a Femenino/Masculino
│       ├── views.py             ← ReportesView · PacienteListView
│       │                           RunETLView · ETLEstadoView
│       │                           DashboardKPIView · PacienteCreateView
│       │                           DashboardDataView · MLEntrenarView
│       │                           MLMetricasView · MLPrediccionView
│       ├── urls.py              ← Rutas de la app etl
│       ├── permissions.py       ← Permisos de la app etl
│       ├── admin.py
│       └── management/commands/
│           ├── ejecutar_etl.py
│           ├── crear_usuarios_base.py
│           └── corregir_sexo.py
│
├── build.sh                     ← Script de build
├── requirements.txt
└── runtime.txt
```

---

## Instalación local

### Requisitos previos

- Python 3.12+
- Git
- PostgreSQL (o SQLite modificando settings)

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/vita-clinical.git
cd vita-clinical/backend
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus credenciales de base de datos
```

### 5. Aplicar migraciones y crear usuarios

```bash
python manage.py migrate
python manage.py crear_usuarios_base
```

### 6. Verificar la instalación

```bash
python manage.py check
```

Debe terminar con `System check identified no issues.`

### 7. Iniciar el servidor

```bash
python manage.py runserver
```

Abrir en el navegador: **http://127.0.0.1:8000**

---

## Variables de entorno

Crea un archivo `.env` en `backend/` con las siguientes variables:

```env
# Seguridad
SECRET_KEY=django-insecure-cambia-esto-en-produccion
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

# Base de datos (PostgreSQL)
DB_NAME=vita_clinical
DB_USER=postgres
DB_PASSWORD=tu_contraseña
DB_HOST=localhost
DB_PORT=5432
```

---

## Flujo de uso

Una vez iniciado el servidor, el flujo recomendado es:

### Paso 1 — Ejecutar el ETL

Desde el dashboard (botón **Ejecutar ETL**) o desde la terminal:

```bash
python manage.py ejecutar_etl
```

El dataset debe estar en `backend/datasets/dataset_clinico_etl_1800_registros.xlsx`. El ETL procesará 1800 registros, eliminará duplicados, corregirá inconsistencias, estandarizará el sexo por nombre y los cargará en la base de datos.

### Paso 2 — Entrenar el modelo ML

Desde el dashboard → sección **ML Modeling** → botón **Entrenar modelo**.

O vía API:

```bash
curl -X POST http://127.0.0.1:8000/api/etl/ml/entrenar/ \
  -H "Authorization: Bearer <token>"
```

### Paso 3 — Explorar el dashboard

El dashboard se actualiza automáticamente con los datos cargados. Incluye:

- KPIs clínicos en tiempo real (tarjetas cliqueables con enlace según rol)
- Gráficas ApexCharts: distribución de riesgo, diagnósticos, sexo y grupos etarios
- Tabla de pacientes con búsqueda (sin tildes), filtros por riesgo e IMC
- Sidebar adaptativo según rol (enlaces permitidos/denegados/ocultos)
- Perfil de usuario con avatar por inicial y color por rol
- Predicción individual de riesgo

---

## API REST

Todos los endpoints requieren autenticación JWT excepto `/api/auth/login/`.

### Autenticación

```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**Respuesta:**

```json
{
  "access": "<jwt_token>",
  "refresh": "<refresh_token>",
  "rol": "ADMIN",
  "rol_display": "Administrador",
  "nombres": "Admin",
  "email": "admin@vita.com"
}
```

Usar el access token en el header de todas las peticiones:

```http
Authorization: Bearer <jwt_token>
```

### Endpoints disponibles

| Método | Endpoint | Descripción | Roles |
|--------|----------|-------------|-------|
| POST | `/api/auth/login/` | Login → devuelve JWT | Todos |
| POST | `/api/auth/token/refresh/` | Renovar token | Todos |
| GET | `/api/auth/me/` | Perfil del usuario autenticado | Todos |
| PUT/PATCH | `/api/auth/profile/update/` | Actualizar perfil (solo ADMIN) | Admin |
| GET | `/api/etl/dashboard/kpis/` | KPIs clínicos completos | Todos |
| GET | `/api/etl/pacientes/` | Lista paginada de pacientes | Todos |
| GET | `/api/etl/reportes/?formato=pdf` | Exportar PDF/Excel/CSV | Todos |
| POST | `/api/etl/run/` | Ejecutar pipeline ETL | Admin · Analista |
| GET | `/api/etl/status/` | Estado de ejecución ETL | Admin · Analista |
| GET | `/api/etl/historial/` | Historial de ejecuciones | Admin · Analista |
| POST | `/api/etl/ml/entrenar/` | Entrenar RandomForest | Admin · Analista |
| GET | `/api/etl/ml/metricas/` | Métricas del modelo | Admin · Analista |
| POST | `/api/etl/ml/predecir/` | Predecir riesgo de un paciente | Admin · Analista |
| GET | `/api/analytics/descriptive/` | Estadística descriptiva | Todos |
| GET | `/api/analytics/pacientes-por-criterio/` | Segmentación cruzada | Todos |
| POST | `/api/etl/pacientes/create/` | Crear paciente manualmente | Admin |

### Ejemplo — Predicción de riesgo

```http
POST /api/etl/ml/predecir/
Authorization: Bearer <token>
Content-Type: application/json

{
  "edad": 55,
  "glucosa": 145.0,
  "presion_sistolica": 150,
  "imc": 29.5,
  "colesterol": 220.0,
  "saturacion_oxigeno": 96.0,
  "frecuencia_cardiaca": 88,
  "temperatura": 37.0,
  "sexo": "Masculino",
  "actividad_fisica": "Baja",
  "fumador": true,
  "antecedentes_familiares": true,
  "presion_diastolica": 95,
  "consumo_alcohol": false
}
```

**Respuesta:**

```json
{
  "riesgo_predicho": "Alto",
  "probabilidades": {
    "Alto": 0.6133,
    "Bajo": 0.0867,
    "Medio": 0.3000
  },
  "modelo_usado": "RandomForestClassifier"
}
```

---

## Roles y permisos

El sistema tiene tres roles con sidebar adaptativo. El rol se incluye como claim en el JWT y la UI se ajusta dinámicamente.

| Sección | Administrador | Médico | Analista |
|---------|:---:|:---:|:---:|
| Dashboard / KPIs | ✅ | ✅ | ✅ |
| Lista de pacientes | ✅ | ✅ | ✅ |
| Editar perfil propio | ✅ | ❌ (solo lectura) | ❌ (solo lectura) |
| Pipeline ETL | ✅ | ❌ | ✅ |
| ML Modeling | ✅ | ❌ | ✅ |
| Exportar reportes | ✅ | ✅ (solo PDF) | ✅ |
| CRUD de pacientes | ✅ | ❌ | ❌ |
| Estadística descriptiva | ✅ | ✅ | ✅ |
| Ver credenciales en login | ✅ | ✅ | ✅ |

El sidebar muestra los enlaces no permitidos en gris con icono de candado (`nav-denied`) o los oculta completamente (`nav-hidden`) según la configuración por rol.

---

## Módulo ETL

### Dataset

El dataset incluye **1800 registros clínicos simulados** con errores intencionales:

- Valores nulos (glucosa = NULL, peso = NULL)
- Tipos incorrectos (edad = "Treinta", presión = "Alta")
- Duplicados de pacientes
- Errores ortográficos en diagnósticos ("hipertencion", "hipertensíon")
- Sexo con formato inconsistente (M, F, Masculino, Femenino)

### Reglas de limpieza aplicadas

| Problema | Tratamiento |
|----------|-------------|
| Duplicados | `drop_duplicates` por `id_paciente` |
| Texto en campos numéricos | `pd.to_numeric(errors='coerce')` → imputación por mediana |
| Errores ortográficos | Normalización mediante diccionario de equivalencias |
| Sexo inconsistente | M → Masculino, F → Femenino + verificación por nombre |
| Nulos en categóricos | Imputación por moda |
| IMC | Calculado automáticamente: peso / altura² |
| Riesgo clínico | Clasificado por reglas: Crítico / Alto / Medio / Bajo |

### Criterios de clasificación de riesgo

| Nivel | Criterios |
|-------|-----------|
| **Crítico** | Presión sistólica > 180 ó Glucosa > 300 ó Saturación < 85% |
| **Alto** | 2 o más de: PS > 140, glucosa > 140, IMC > 35, fumador > 60 años, antecedentes |
| **Medio** | 2 o más de: PS > 120, glucosa > 100, IMC > 30, fumador, edad > 65 |
| **Bajo** | No cumple criterios anteriores |

Cada ejecución queda registrada en `HistorialETL` con: fecha, usuario, registros procesados, errores, tiempo de ejecución y estado.

### Clasificador de sexo por nombre

El sistema incluye un mapeo de ~600 nombres a su género correspondiente. Durante el ETL y mediante el comando `corregir_sexo`, se verifica y corrige automáticamente el sexo de cada paciente basado en su nombre de pila, con soporte para tildes y mayúsculas/minúsculas.

---

## Módulo Machine Learning

### Modelo

`RandomForestClassifier` (scikit-learn) con las siguientes características:

- `n_estimators=150`, `max_depth=12`, `class_weight='balanced'`
- Preprocesamiento: `StandardScaler` para numéricas, `OneHotEncoder` para categóricas
- Todo encapsulado en un `Pipeline` de scikit-learn y serializado con `joblib`

### Variables predictoras

`edad`, `imc`, `glucosa`, `colesterol`, `presion_sistolica`, `presion_diastolica`, `frecuencia_cardiaca`, `saturacion_oxigeno`, `temperatura`, `sexo`, `actividad_fisica`, `fumador`, `consumo_alcohol`, `antecedentes_familiares`

### Métricas reportadas

Accuracy, Precision, Recall, F1-Score, Matriz de confusión

> **Nota:** el modelo serializado (`ml_models/`) no se incluye en el repositorio. Debe entrenarse tras ejecutar el ETL usando el botón **Entrenar modelo** en el dashboard o el endpoint `/api/etl/ml/entrenar/`.

---

## Despliegue en producción

La aplicación está desplegada usando **Render** + **PostgreSQL**.

### Variables de entorno en producción

```env
SECRET_KEY=<clave-secreta-larga-y-aleatoria>
DEBUG=False
ALLOWED_HOSTS=tu-dominio.onrender.com
DB_NAME=vita_clinical
DB_USER=usuario
DB_PASSWORD=contraseña
DB_HOST=host.render.com
DB_PORT=5432
```

### Start command (Render)

```bash
gunicorn config.wsgi:application --workers 1 --threads 2 --timeout 300 --worker-class gthread
```

### Build command (Render)

```bash
./build.sh
```

El script `build.sh` ejecuta automáticamente:

```bash
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py crear_usuarios_base
python manage.py corregir_sexo
```

---

Proyecto FullStack + Data Analytics + ETL + Machine Learning — Junio 2026
