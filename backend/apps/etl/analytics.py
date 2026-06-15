import pandas as pd
import numpy as np
from .models import DashboardKPIs, Paciente


def pacientes_a_dataframe():
    rows = list(Paciente.objects.all().values(
        'id_paciente', 'nombres', 'apellidos', 'edad', 'sexo', 'peso', 'altura', 'imc',
        'clasificacion_imc', 'presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca',
        'glucosa', 'colesterol', 'saturacion_oxigeno', 'temperatura',
        'antecedentes_familiares', 'fumador', 'consumo_alcohol',
        'diagnostico_preliminar', 'riesgo_enfermedad',
    ))
    return pd.DataFrame(rows) if rows else None


def recalcular_kpis_desde_db():
    df = pacientes_a_dataframe()
    if df is None or df.empty:
        return None
    return calcular_analitica_dataset(df, reemplazar=True)


def calcular_analitica_dataset(df: pd.DataFrame, reemplazar=False):
    total = len(df)
    if total == 0:
        return None

    col_sistolica = 'presión_sistólica' if 'presión_sistólica' in df.columns else 'presion_sistolica'
    col_glucosa = 'glucosa'
    col_saturacion = 'saturación_oxígeno' if 'saturación_oxígeno' in df.columns else 'saturacion_oxigeno'
    col_diag = 'diagnóstico_preliminar' if 'diagnóstico_preliminar' in df.columns else 'diagnostico_preliminar'
    col_imc = 'IMC' if 'IMC' in df.columns else 'imc'
    col_clasif_imc = 'clasificacion_imc'

    condicion_critica = (
        (df[col_sistolica] > 180) |
        (df[col_glucosa] > 300) |
        (df[col_saturacion] < 85)
    )
    criticos = int(df[condicion_critica].shape[0])

    alertas_sistolica = int((df[col_sistolica] > 180).sum())
    alertas_glucosa = int((df[col_glucosa] > 300).sum())
    alertas_saturacion = int((df[col_saturacion] < 85).sum())

    hipertensos = 0
    diabeticos = 0
    if col_diag in df.columns:
        diag_series = df[col_diag].astype(str).str.lower().str.strip()
        hipertensos = int(diag_series.str.contains('hipertens', na=False).sum())
        diabeticos = int(diag_series.str.contains('diabet', na=False).sum())

    fumadores = int(df['fumador'].sum()) if 'fumador' in df.columns else 0

    obesos = 0
    if col_clasif_imc in df.columns:
        obesos = int((df[col_clasif_imc].astype(str).str.lower().str.strip() == 'obesidad').sum())
    elif col_imc in df.columns:
        obesos = int((df[col_imc] >= 30).sum())

    antecedentes = int(df['antecedentes_familiares'].sum()) if 'antecedentes_familiares' in df.columns else 0
    alcohol = int(df['consumo_alcohol'].sum()) if 'consumo_alcohol' in df.columns else 0
    saturacion_baja = int((df[col_saturacion] < 85).sum())

    col_riesgo = 'riesgo_enfermedad' if 'riesgo_enfermedad' in df.columns else 'riesgo_clinico'
    riesgo_prom = 0.0
    if col_riesgo in df.columns:
        mapeo_riesgo = {'Bajo': 0.25, 'Medio': 0.50, 'Alto': 0.75, 'Crítico': 1.0}
        riesgo_prom = float(df[col_riesgo].map(mapeo_riesgo).fillna(0.0).mean())

    col_edad = 'edad'
    e_media = float(df[col_edad].mean())
    e_mediana = float(df[col_edad].median())
    e_moda = float(df[col_edad].mode()[0]) if not df[col_edad].mode().empty else 0.0
    e_desviacion = float(df[col_edad].std()) if len(df) > 1 else 0.0

    g_media = float(df[col_glucosa].mean())
    g_desviacion = float(df[col_glucosa].std()) if len(df) > 1 else 0.0

    if reemplazar:
        DashboardKPIs.objects.all().delete()

    kpi_reporte = DashboardKPIs.objects.create(
        total_registros=total,
        pacientes_criticos=criticos,
        pacientes_hipertensos=hipertensos,
        pacientes_diabeticos=diabeticos,
        pacientes_fumadores=fumadores,
        pacientes_obesos=obesos,
        pacientes_antecedentes=antecedentes,
        pacientes_alcohol=alcohol,
        pacientes_saturacion_baja=saturacion_baja,
        alertas_sistolica=alertas_sistolica,
        alertas_glucosa=alertas_glucosa,
        alertas_saturacion=alertas_saturacion,
        riesgo_promedio=round(riesgo_prom * 100, 2),
        edad_media=round(e_media, 2),
        edad_mediana=round(e_mediana, 2),
        edad_moda=round(e_moda, 2),
        edad_desviacion=round(e_desviacion, 2),
        glucosa_media=round(g_media, 2),
        glucosa_desviacion=round(g_desviacion, 2),
    )

    return kpi_reporte
