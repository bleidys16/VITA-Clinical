import os
import uuid
from django.core.cache import cache
from .services import PipelineETL
from .analytics import calcular_analitica_dataset, recalcular_kpis_desde_db
from apps.machine_learning.services import MotorPredictivoVITA

TASK_ID_KEY = 'etl_task_id'

def ejecutar_pipeline(ruta_archivo, usuario_id=None):
    task_id = uuid.uuid4().hex
    cache.set(TASK_ID_KEY, task_id, timeout=3600)

    def actualizar_log(fase, mensaje, detalle=''):
        data = {'fase': fase, 'mensaje': mensaje, 'detalle': detalle}
        cache.set(f'etl_status_{task_id}', data, timeout=3600)
        log_history = cache.get(f'etl_logs_{task_id}', [])
        log_history.append({'fase': fase, 'mensaje': mensaje, 'detalle': detalle})
        cache.set(f'etl_logs_{task_id}', log_history, timeout=3600)

    actualizar_log('EXTRACT', 'Extrayendo datos del archivo...', 'Leyendo CSV/Excel con Pandas')
    pipeline = PipelineETL(file_path=ruta_archivo, usuario_id=usuario_id)
    filas_extraidas = pipeline.extract()
    actualizar_log('EXTRACT', f'Extracción completada', f'{filas_extraidas} registros leídos')

    actualizar_log('TRANSFORM', 'Transformando datos...', 'Limpieza, normalización y cálculo de IMC')
    pipeline.transform()
    actualizar_log('TRANSFORM', 'Transformación completada', 'Datos limpios y estructurados')

    actualizar_log('LOAD', 'Cargando datos a PostgreSQL...', 'Inserción masiva con transacción atómica')
    exito, filas_cargadas = pipeline.load()
    actualizar_log('LOAD', 'Carga completada', f'{filas_cargadas} registros insertados')

    actualizar_log('ANALYTICS', 'Calculando KPIs del dashboard...', 'Estadísticas descriptivas y pacientes críticos')
    try:
        kpi = calcular_analitica_dataset(pipeline.df, reemplazar=True)
        if not kpi:
            raise ValueError('El dataset no produjo KPIs')
        actualizar_log('ANALYTICS', 'KPIs calculados correctamente', f'{kpi.total_registros} registros')
    except Exception as e:
        actualizar_log('ANALYTICS', 'Reintentando KPIs desde la base de datos...', str(e))
        try:
            kpi = recalcular_kpis_desde_db()
            if kpi:
                actualizar_log('ANALYTICS', 'KPIs recalculados desde BD', f'{kpi.total_registros} registros')
            else:
                actualizar_log('ANALYTICS', 'No se pudieron calcular KPIs', 'Sin pacientes en la base de datos')
        except Exception as e2:
            actualizar_log('ANALYTICS', 'Error definitivo calculando KPIs', str(e2))

    try:
        os.remove(ruta_archivo)
    except Exception:
        pass

    actualizar_log('ML', 'Preparando datos para Machine Learning...', 'Normalizando columnas y generando variable objetivo')

    df_ml = pipeline.df.copy()
    rename_map = {
        'IMC': 'imc',
        'presión_sistólica': 'presion_sistolica',
        'presión_diastólica': 'presion_diastolica',
        'saturación_oxígeno': 'saturacion_oxigeno',
        'diagnóstico_preliminar': 'diagnostico_preliminar',
    }
    df_ml.rename(columns=rename_map, inplace=True)

    df_ml['enfermedad'] = (
        (df_ml['glucosa'] > 100).astype(int) +
        (df_ml['presion_sistolica'] > 130).astype(int) +
        (df_ml['colesterol'] > 200).astype(int) +
        (df_ml['imc'] >= 25).astype(int) +
        (df_ml['frecuencia_cardiaca'] > 90).astype(int) +
        (df_ml['edad'] > 50).astype(int)
    ).apply(lambda x: 1 if x >= 4 else 0)

    actualizar_log('ML', 'Ejecutando entrenamiento con Random Forest...', 'Scikit-Learn pipeline en progreso')
    try:
        MotorPredictivoVITA.entrenar_pipeline_ml(df_ml)
        actualizar_log('ML', 'Modelo entrenado exitosamente', 'Métricas guardadas en la base de datos')
    except Exception as e:
        actualizar_log('ML', 'Error en entrenamiento ML', str(e))

    actualizar_log('DONE', 'Pipeline ETL+ML finalizado', 'Proceso completo')

    return {
        "status": "success",
        "registros_leidos": filas_extraidas,
        "registros_procesados": filas_cargadas,
    }
