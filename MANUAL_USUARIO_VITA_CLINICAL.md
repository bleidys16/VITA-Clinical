# Manual de Usuario — VITA Clinical

> **Versión:** 1.0
> **Fecha:** Junio 2026

---

## 1. Credenciales de Acceso

El sistema cuenta con **tres roles** predefinidos. Al iniciar sesión por primera vez, use las siguientes credenciales:

| Rol | Usuario | Contraseña |
|-----|---------|------------|
| Administrador | `admin@vita.com` | `admin123` |
| Médico | `medico@vita.com` | `medico123` |
| Analista | `analista@vita.com` | `analista123` |

*(Captura de pantalla: pantalla de inicio de sesión con los campos de email y contraseña)*

*(Captura de pantalla: vista del sidebar según rol — ADMIN viendo todas las opciones, MEDICO con opciones limitadas)*

---

## 2. Uso del Dashboard

El dashboard es la pantalla principal después de iniciar sesión. Muestra en tiempo real los indicadores clínicos más importantes.

### 2.1 KPIs (Indicadores Clave)

En la parte superior se muestran **4 tarjetas** con los siguientes indicadores:

| Tarjeta | Descripción |
|---------|-------------|
| **Total Registros** | Cantidad total de pacientes cargados en el sistema |
| **Pacientes Críticos** | Pacientes clasificados con riesgo crítico |
| **Edad Promedio** | Edad media de todos los pacientes registrados |
| **% Riesgo Poblacional** | Porcentaje de riesgo promedio de la población |

Debajo del gráfico de distribución de riesgo se muestran **4 indicadores clínicos** adicionales:

| Indicador | Descripción |
|-----------|-------------|
| **Glucosa prom.** | Nivel promedio de glucosa (mg/dL) |
| **IMC prom.** | Índice de Masa Corporal promedio |
| **% Críticos** | Porcentaje de pacientes en estado crítico |
| **% Riesgo Alto** | Porcentaje de pacientes con riesgo alto |

*(Captura de pantalla: dashboard con las tarjetas de KPIs visibles en la parte superior)*

### 2.2 Gráficas

El dashboard incluye gráficos interactivos (ApexCharts):

- **Distribución de riesgo** (Bajo / Medio / Alto / Crítico)
- **Diagnósticos más frecuentes**
- **Distribución por sexo**
- **Grupos etarios**

*(Captura de pantalla: sección de gráficas del dashboard mostrando al menos dos gráficos)*

### 2.3 Barra lateral (Sidebar)

El menú lateral se adapta según el rol del usuario:

| Sección | Admin | Médico | Analista |
|---------|:-----:|:------:|:--------:|
| Dashboard | ✅ | ✅ | ✅ |
| Pacientes | ✅ | ✅ | ✅ |
| ETL | ✅ | ❌ | ✅ |
| ML Modeling | ✅ | ❌ | ✅ |
| Usuarios (Admin) | ✅ | ❌ | ❌ |

*(Captura de pantalla: sidebar expandido mostrando las opciones del menú)*

---

## 3. Proceso ETL

El pipeline ETL (Extract, Transform, Load) permite cargar datasets clínicos en la base de datos.

### 3.1 Carga de archivo

1. Navegue a la sección **ETL** desde el sidebar.
2. Arrastre un archivo `.xlsx` o `.csv` al área de carga o haga clic para seleccionarlo.
3. Haga clic en **Iniciar ETL**.

*(Captura de pantalla: formulario de carga de archivo con el área de drag & drop y el botón "Iniciar ETL")*

### 3.2 Ejecución del pipeline

El sistema ejecuta automáticamente tres fases:

| Fase | Descripción |
|------|-------------|
| **Extract** | Lectura del archivo con pandas |
| **Transform** | Limpieza: duplicados, nulos, tipos de datos, estandarización de sexo, cálculo de IMC |
| **Load** | Inserción masiva en PostgreSQL con auditoría |

Durante la ejecución, un panel de logs muestra el progreso en tiempo real.

*(Captura de pantalla: pipeline en ejecución con logs mostrando Extract → Transform → Load)*

### 3.3 Historial de ejecuciones

Al finalizar, la tabla de historial muestra:

- Fecha y hora de la ejecución
- Usuario que la ejecutó
- Registros procesados
- Errores encontrados
- Tiempo de ejecución
- Estado (Exitoso / Fallido)

*(Captura de pantalla: tabla de historial ETL con ejecuciones listadas y estado "Exitoso")*

### 3.4 KPIs actualizados

Después del ETL, el dashboard se actualiza automáticamente con los nuevos datos.

*(Captura de pantalla: dashboard posterior a la carga ETL mostrando KPIS actualizados)*

*(Captura de pantalla: comparativa de registros antes y después del proceso ETL)*

---

## 4. Reportes

El sistema permite exportar los datos de pacientes en tres formatos desde la vista de pacientes.

### 4.1 Exportar reporte

1. Vaya a **Pacientes** desde el sidebar.
2. Haga clic en el botón del formato deseado: **PDF**, **Excel** o **CSV**.
3. El archivo se descargará automáticamente.

*(Captura de pantalla: vista de pacientes con los botones de exportación PDF, Excel y CSV visibles)*

### 4.2 Formatos disponibles

| Formato | Botón | Contenido |
|---------|-------|-----------|
| **PDF** | ![PDF] | Reporte clínico con KPIs, tabla de pacientes con ID, nombre, edad, sexo, IMC, presión, glucosa, saturación y riesgo |
| **Excel** | ![Excel] | Dataset completo en `.xlsx` con todos los campos |
| **CSV** | ![CSV] | Datos planos separados por comas para análisis externo |

*(Captura de pantalla: selector de formato de reporte y descarga exitosa)*

*(Captura de pantalla: ejemplo del reporte PDF generado con KPIs y tabla de pacientes)*

---

## Historial de Revisiones

| Versión | Fecha | Autor | Descripción |
|---------|-------|-------|-------------|
| 1.0 | Junio 2026 | Equipo VITA Clinical | Manual de usuario inicial |
