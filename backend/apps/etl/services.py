import os
import time
import pandas as pd
import numpy as np
from datetime import datetime
from django.db import models, transaction
from django.contrib.auth.models import User
from .models import Paciente, HistorialETL, DashboardKPIs

class PipelineETL:
    def __init__(self, file_path, usuario_id=None):
        self.file_path = file_path
        self.usuario = User.objects.filter(id=usuario_id).first() if usuario_id else None
        self.start_time = None
        self.df = None
        self.total_extraidos = 0

    def extract(self):
        """Capa de Extracción (Extract): Lee el archivo CSV o Excel usando Pandas"""
        self.start_time = time.time()

        # Detectar extensión para elegir el lector de Pandas adecuado
        nombre = self.file_path if isinstance(self.file_path, str) else self.file_path.name
        es_excel = nombre.lower().endswith(('.xlsx', '.xls'))

        if isinstance(self.file_path, str):
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"El archivo en la ruta {self.file_path} no existe.")
            self.df = pd.read_excel(self.file_path) if es_excel else pd.read_csv(self.file_path)
        else:
            self.df = pd.read_excel(self.file_path) if es_excel else pd.read_csv(self.file_path)

        self.total_extraidos = len(self.df)
        return self.total_extraidos

    def transform(self):
        """Capa de Transformación (Transform): Limpieza, estandarización y cálculos clínicos"""
        if self.df is None:
            raise ValueError("Primero debes ejecutar el método extract().")

        # 1. Depuración de duplicados basados en el ID único del paciente
        self.df.drop_duplicates(subset=['id_paciente'], keep='first', inplace=True)

        # 2. Forzar conversión a numérico y Manejo de Datos Faltantes (Evita el error 'Alta')
        columnas_numericas = ['peso', 'altura', 'presión_sistólica', 'presión_diastólica', 
                              'frecuencia_cardiaca', 'glucosa', 'colesterol', 
                              'saturación_oxígeno', 'temperatura']
        
        for col in columnas_numericas:
            if col in self.df.columns:
                # errors='coerce' convierte textos como 'Alta' o 'Baja' en NaN de forma segura
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
                
                # Ahora que es puramente numérico, calculamos la mediana y llenamos vacíos
                mediana = self.df[col].median()
                self.df[col] = self.df[col].fillna(mediana)

        # 3. Estandarización de Variables Categóricas (Sexo)
        if 'sexo' in self.df.columns:
            self.df['sexo'] = self.df['sexo'].astype(str).str.strip().str.upper()
            mapeo_sexo = {'M': 'Masculino', 'F': 'Femenino', 'MASCULINO': 'Masculino', 'FEMENINO': 'Femenino'}
            self.df['sexo'] = self.df['sexo'].map(mapeo_sexo).fillna('No Definido')

        # 4. Corrección de Inconsistencias de Tipo (Edad)
        if 'edad' in self.df.columns:
            mapeo_edades_texto = {'treinta': '30', 'cuarenta': '40', 'cincuenta': '50', 'Treinta': '30'}
            self.df['edad'] = self.df['edad'].astype(str).replace(mapeo_edades_texto)
            self.df['edad'] = pd.to_numeric(self.df['edad'], errors='coerce')
            edad_media = int(self.df['edad'].mean()) if not self.df['edad'].isna().all() else 40
            self.df['edad'] = self.df['edad'].fillna(edad_media).astype(int)

        # 5. Normalización Ortográfica de Diagnósticos Preliminares
        if 'diagnóstico_preliminar' in self.df.columns:
            self.df['diagnóstico_preliminar'] = self.df['diagnóstico_preliminar'].astype(str).str.strip()
            mapeo_diagnosticos = {
                'hipertencion': 'Hipertensión',
                'hipertensíon': 'Hipertensión',
                'Diabetes tipo 2': 'Diabetes Tipo 2',
                'diabetes': 'Diabetes Tipo 2',
                'obesidad': 'Obesidad',
                'Cardiopatía': 'Cardiopatía',
                'Paciente sano': 'Sano'
            }
            self.df['diagnóstico_preliminar'] = self.df['diagnóstico_preliminar'].replace(mapeo_diagnosticos)

        # 6. Cálculos Clínicos Automatizados (Fórmula del IMC)
        self.df['IMC'] = self.df['peso'] / (self.df['altura'] ** 2)
        self.df['IMC'] = self.df['IMC'].round(2)

        # Categorización del IMC mediante condiciones lógicas
        self.df['clasificacion_imc'] = 'No evaluado'
        self.df.loc[self.df['IMC'] < 18.5, 'clasificacion_imc'] = 'Bajo peso'
        self.df.loc[(self.df['IMC'] >= 18.5) & (self.df['IMC'] < 25), 'clasificacion_imc'] = 'Normal'
        self.df.loc[(self.df['IMC'] >= 25) & (self.df['IMC'] < 30), 'clasificacion_imc'] = 'Sobrepeso'
        self.df.loc[self.df['IMC'] >= 30, 'clasificacion_imc'] = 'Obesidad'

        # 7. Conversión de Columnas Booleanas
        columnas_bool = ['antecedentes_familiares', 'fumador', 'consumo_alcohol']
        for col in columnas_bool:
            if col in self.df.columns:
                # Aseguramos mapeo estricto a booleano real
                self.df[col] = self.df[col].replace({'True': True, 'False': False, 1: True, 0: False})
                self.df[col] = self.df[col].astype(bool)

        # 8. Conversión de Fechas
        if 'fecha_consulta' in self.df.columns:
            self.df['fecha_consulta'] = pd.to_datetime(self.df['fecha_consulta'], errors='coerce')
            self.df['fecha_consulta'] = self.df['fecha_consulta'].fillna(pd.Timestamp(datetime.now()))

        return len(self.df)

    def load(self):
        """Capa de Carga (Load): Inserción masiva y atómica en PostgreSQL con logs"""
        if self.df is None:
            raise ValueError("No hay datos transformados listos para cargar.")

        # Solución al error de resta con None: Aseguramos un fallback numérico para el linter
        inicio = self.start_time if self.start_time is not None else time.time()

        registros_a_insertar = []
        
        # Recorremos el DataFrame transformado fila por fila
        for _, row in self.df.iterrows():
            paciente = Paciente(
                id_paciente=int(row['id_paciente']),
                nombres=row['nombres'],
                apellidos=row['apellidos'],
                edad=int(row['edad']),
                sexo=row['sexo'],
                peso=float(row['peso']),
                altura=float(row['altura']),
                imc=float(row['IMC']),
                clasificacion_imc=row['clasificacion_imc'],
                presion_sistolica=int(row['presión_sistólica']),
                presion_diastolica=int(row['presión_diastólica']),
                frecuencia_cardiaca=int(row['frecuencia_cardiaca']),
                glucosa=float(row['glucosa']),
                colesterol=float(row['colesterol']),
                saturacion_oxigeno=float(row['saturación_oxígeno']),
                temperatura=float(row['temperatura']),
                antecedentes_familiares=bool(row['antecedentes_familiares']),
                fumador=bool(row['fumador']),
                consumo_alcohol=bool(row['consumo_alcohol']),
                actividad_fisica=row.get('actividad_física', 'Sedentario'),
                diagnostico_preliminar=row['diagnóstico_preliminar'],
                riesgo_enfermedad=row.get('riesgo_enfermedad', 'Bajo'),
                fecha_consulta=row['fecha_consulta'].date()
            )
            registros_a_insertar.append(paciente)

        # Ejecución atómica masiva corrigiendo el contexto y los llamados de objetos de Django
        try:
            with transaction.atomic(): # Paréntesis explícitos para evitar el 'bad-context-manager'
                # cast dinámico implícito para evitar advertencias de tipado estricto en el ORM
                manager_paciente: models.Manager = Paciente.objects
                manager_paciente.bulk_create(registros_a_insertar, ignore_conflicts=True)
                
            tiempo_final = time.time() - inicio
            
            manager_historial: models.Manager = HistorialETL.objects
            manager_historial.create(
                usuario=self.usuario,
                registros_procesados=len(registros_a_insertar),
                errores_encontrados=self.total_extraidos - len(registros_a_insertar),
                tiempo_ejecucion=round(tiempo_final, 3),
                estado='Exitoso'
            )
            return True, len(registros_a_insertar)
            
        except Exception as e:
            tiempo_final = time.time() - inicio
            manager_historial = HistorialETL.objects
            manager_historial.create(
                usuario=self.usuario,
                registros_procesados=0,
                errores_encontrados=self.total_extraidos,
                tiempo_ejecucion=round(tiempo_final, 3),
                estado=f'Fallido: {str(e)}'
            )
            raise e
   
def calcular_analitica_dataset(df: pd.DataFrame):
    """
    Recibe un DataFrame de Pandas limpio y calcula todas las métricas
    obligatorias de la guía, guardándolas en la base de datos.
    """
    # Asegurar que los nombres de las columnas coincidan con tu dataset (ajusta si es necesario)
    # Columnas esperadas: 'edad', 'glucosa', 'presion_sistolica', 'saturacion_oxigeno', 'fumador', 'diabetes', 'hipertension'

    # 1. Total de registros
    total = len(df)
    if total == 0:
        return None

    # 2. Detección de Pacientes Críticos (Criterios estrictos de la guía)
    # Presión sistólica > 180 Ó Glucosa > 300 Ó Saturación < 85
    condicion_critica = (
        (df['presion_sistolica'] > 180) | 
        (df['glucosa'] > 300) | 
        (df['saturacion_oxigeno'] < 85)
    )
    criticos = int(df[condicion_critica].shape[0])

    # 3. KPIs de Control Epidemiológico (Conteos analíticos)
    # Nota: Asumiendo que las columnas son booleanas (True/False) o binarias (1/0)
    hipertensos = int(df[df['hipertension'] == 1].shape[0]) if 'hipertension' in df.columns else 0
    diabeticos = int(df[df['diabetes'] == 1].shape[0]) if 'diabetes' in df.columns else 0
    fumadores = int(df[df['fumador'] == 1].shape[0]) if 'fumador' in df.columns else 0
    
    # Riesgo promedio de la población (si tu dataset ya trae un score o columna de riesgo preliminar)
    riesgo_prom = float(df['riesgo_clinico'].mean()) if 'riesgo_clinico' in df.columns else 0.0

    # 4. Estadística Descriptiva utilizando las funciones nativas de Pandas/NumPy
    e_media = float(df['edad'].mean())
    e_mediana = float(df['edad'].median())
    
    # La moda en Pandas devuelve una Serie (porque puede haber bimodalidad), tomamos el primer valor
    e_moda = float(df['edad'].mode()[0]) if not df['edad'].mode().empty else 0.0
    e_desviacion = float(df['edad'].std()) if len(df) > 1 else 0.0

    g_media = float(df['glucosa'].mean())
    g_desviacion = float(df['glucosa'].std()) if len(df) > 1 else 0.0

    # 5. Guardar el reporte analítico en la base de datos para el consumo del Dashboard
    kpi_reporte = DashboardKPIs.objects.create(
        total_registros=total,
        pacientes_criticos=criticos,
        pacientes_hipertensos=hipertensos,
        pacientes_diabeticos=diabeticos,
        pacientes_fumadores=fumadores,
        riesgo_promedio=riesgo_prom,
        edad_media=e_media,
        edad_mediana=e_mediana,
        edad_moda=e_moda,
        edad_desviacion=e_desviacion,
        glucosa_media=g_media,
        glucosa_desviacion=g_desviacion
    )

    return kpi_reporte