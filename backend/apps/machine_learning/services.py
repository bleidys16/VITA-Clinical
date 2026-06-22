import joblib
import os

import numpy as np
import pandas as pd
from django.conf import settings
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
from apps.etl.models import Paciente, MetricasModeloML

class PredictorRiesgoService:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()

    def preparar_datos(self):
        """Extrae los datos limpios de PostgreSQL y los prepara para el modelo"""
        # Traemos todos los registros de pacientes
        pacientes = Paciente.objects.all().values()
        if not pacientes:
            raise ValueError("No hay pacientes registrados en la base de datos para entrenar el modelo.")
        
        df = pd.DataFrame(pacientes)
        
        # 1. Definir características (X) y variable objetivo (y)
        # Usamos las métricas clínicas clave recopiladas en VITA Clinical
        features = [
            'edad', 'peso', 'altura', 'imc', 
            'presion_sistolica', 'presion_diastolica', 
            'frecuencia_cardiaca', 'glucosa', 'colesterol', 
            'saturacion_oxigeno', 'temperatura',
            'antecedentes_familiares', 'fumador', 'consumo_alcohol'
        ]
        
        X = df[features].copy()
        
        # Convertir booleanos a enteros (0 o 1)
        for col in ['antecedentes_familiares', 'fumador', 'consumo_alcohol']:
            X[col] = X[col].astype(int)
            
        # 2. Variable Objetivo: Riesgo de enfermedad
        if 'riesgo_enfermedad' not in df.columns or df['riesgo_enfermedad'].isnull().all():
            # Creamos un sistema de puntuación clínica claro para que el modelo aprenda el patrón
            score = (
                (df['glucosa'] > 110).astype(int) + 
                (df['presion_sistolica'] > 130).astype(int) + 
                (df['colesterol'] > 200).astype(int) +
                (df['imc'] >= 30).astype(int)
            )
            
            condiciones = [
                (score >= 3), # Múltiples factores alterados
                (score == 2),
                (score == 1)
            ]
            opciones = ['Crítico', 'Alto', 'Medio']
            df['riesgo_enfermedad'] = np.select(condiciones, opciones, default='Bajo')
            
        y = self.label_encoder.fit_transform(df['riesgo_enfermedad'])
        
        return X, y

    def entrenar_modelo(self):
        """Entrena el clasificador y retorna las métricas de evaluación de la IPS"""
        X, y = self.preparar_datos()

        # División del dataset: 80% Entrenamiento, 20% Prueba (exigido por buenas prácticas)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        # Escalado de características numéricas
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Ajustar modelo
        self.model.fit(X_train_scaled, y_train)

        # Predicciones para evaluación
        y_pred = self.model.predict(X_test_scaled)

        # Generar reporte de métricas en formato de diccionario
        target_names = self.label_encoder.classes_
        reporte_dict = classification_report(y_test, y_pred, target_names=target_names, output_dict=True)

        # Guardar modelo entrenado a disco
        self.guardar_modelo()

        return reporte_dict

    def guardar_modelo(self):
        os.makedirs(os.path.join(settings.BASE_DIR, 'media', 'modelos_ml'), exist_ok=True)
        joblib.dump(self.model, os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'riesgo_model.pkl'))
        joblib.dump(self.scaler, os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'riesgo_scaler.pkl'))
        joblib.dump(self.label_encoder, os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'riesgo_encoder.pkl'))

    def cargar_modelo(self):
        modelo_path = os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'riesgo_model.pkl')
        scaler_path = os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'riesgo_scaler.pkl')
        encoder_path = os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'riesgo_encoder.pkl')

        if not os.path.exists(modelo_path):
            self.entrenar_modelo()
            return

        self.model = joblib.load(modelo_path)
        self.scaler = joblib.load(scaler_path)
        self.label_encoder = joblib.load(encoder_path)

    def predecir_paciente(self, paciente_id):
        try:
            paciente = Paciente.objects.get(id_paciente=paciente_id)
        except Paciente.DoesNotExist:
            raise ValueError(f"Paciente con ID {paciente_id} no encontrado.")

        self.cargar_modelo()

        features = np.array([[
            paciente.edad, paciente.peso or 0, paciente.altura or 0, paciente.imc or 0,
            paciente.presion_sistolica or 0, paciente.presion_diastolica or 0,
            paciente.frecuencia_cardiaca or 0, paciente.glucosa or 0, paciente.colesterol or 0,
            paciente.saturacion_oxigeno or 0, paciente.temperatura or 0,
            int(paciente.antecedentes_familiares), int(paciente.fumador), int(paciente.consumo_alcohol)
        ]])

        features_scaled = self.scaler.transform(features)
        prediccion = self.model.predict(features_scaled)[0]
        probabilidades = self.model.predict_proba(features_scaled)[0]

        clases = self.label_encoder.classes_
        riesgo = clases[prediccion]
        probs = {clases[i]: round(float(probabilidades[i] * 100), 2) for i in range(len(clases))}
        confianza = round(float(max(probabilidades) * 100), 2)

        # Análisis de factores clave
        factores = []

        glu = paciente.glucosa or 0
        if glu > 200:
            nivel_glu = 'critico'
            desc_glu = 'Nivel crítico de glucosa en sangre. Riesgo severo de complicaciones diabéticas.'
        elif glu > 140:
            nivel_glu = 'alto'
            desc_glu = 'Nivel alto de glucosa en sangre. Riesgo de diabetes.'
        elif glu > 110:
            nivel_glu = 'medio'
            desc_glu = 'Glucosa ligeramente elevada. Monitorear evolución.'
        else:
            nivel_glu = 'normal'
            desc_glu = 'Glucosa dentro de parámetros normales.'
        factores.append({'nombre': 'Glucosa', 'valor': f'{glu:.2f} mg/dL', 'nivel': nivel_glu, 'descripcion': desc_glu})

        col = paciente.colesterol or 0
        if col > 240:
            nivel_col = 'alto'
            desc_col = 'Nivel de colesterol elevado. Dislipidemia.'
        elif col > 200:
            nivel_col = 'medio'
            desc_col = 'Colesterol ligeramente elevado. Riesgo moderado.'
        else:
            nivel_col = 'normal'
            desc_col = 'Colesterol dentro de rangos saludables.'
        factores.append({'nombre': 'Colesterol', 'valor': f'{col:.2f} mg/dL', 'nivel': nivel_col, 'descripcion': desc_col})

        spo2 = paciente.saturacion_oxigeno or 0
        if spo2 < 85:
            nivel_spo2 = 'critico'
            desc_spo2 = 'Saturación de oxígeno crítica. Posible insuficiencia respiratoria.'
        elif spo2 < 90:
            nivel_spo2 = 'alto'
            desc_spo2 = 'Saturación de oxígeno baja. Riesgo de hipoxia.'
        elif spo2 < 95:
            nivel_spo2 = 'medio'
            desc_spo2 = 'Saturación de oxígeno ligeramente baja.'
        else:
            nivel_spo2 = 'normal'
            desc_spo2 = 'Saturación de oxígeno normal.'
        factores.append({'nombre': 'Saturación Oxígeno', 'valor': f'{spo2:.2f} %', 'nivel': nivel_spo2, 'descripcion': desc_spo2})

        fc = paciente.frecuencia_cardiaca or 0
        if fc > 120:
            nivel_fc = 'critico'
            desc_fc = 'Frecuencia cardíaca muy elevada. Riesgo de taquicardia severa.'
        elif fc > 100:
            nivel_fc = 'alto'
            desc_fc = 'Frecuencia cardíaca elevada. Posible taquicardia.'
        elif fc > 90:
            nivel_fc = 'medio'
            desc_fc = 'Frecuencia cardíaca ligeramente elevada.'
        else:
            nivel_fc = 'normal'
            desc_fc = 'Frecuencia cardíaca dentro de rangos normales.'
        factores.append({'nombre': 'Frecuencia Cardíaca', 'valor': f'{fc} lpm', 'nivel': nivel_fc, 'descripcion': desc_fc})

        sist = paciente.presion_sistolica or 0
        if sist > 180:
            nivel_sist = 'critico'
            desc_sist = 'Presión arterial sistólica crítica. Crisis hipertensiva.'
        elif sist > 140:
            nivel_sist = 'alto'
            desc_sist = 'Presión arterial sistólica elevada. Hipertensión Etapa 2.'
        elif sist > 130:
            nivel_sist = 'medio'
            desc_sist = 'Presión arterial sistólica ligeramente elevada. Hipertensión Etapa 1.'
        else:
            nivel_sist = 'normal'
            desc_sist = 'Presión arterial sistólica normal.'
        factores.append({'nombre': 'Presión Sistólica', 'valor': f'{sist} mmHg', 'nivel': nivel_sist, 'descripcion': desc_sist})

        if paciente.fumador:
            factores.append({'nombre': 'Tabaquismo', 'valor': 'Sí', 'nivel': 'alto', 'descripcion': 'El consumo de tabaco aumenta significativamente el riesgo cardiovascular y respiratorio.'})
        else:
            factores.append({'nombre': 'Tabaquismo', 'valor': 'No', 'nivel': 'normal', 'descripcion': 'Sin consumo de tabaco.'})

        if paciente.consumo_alcohol:
            factores.append({'nombre': 'Consumo de Alcohol', 'valor': 'Sí', 'nivel': 'medio', 'descripcion': 'El consumo de alcohol puede elevar la presión arterial, triglicéridos y afectar la función hepática.'})
        else:
            factores.append({'nombre': 'Consumo de Alcohol', 'valor': 'No', 'nivel': 'normal', 'descripcion': 'Sin consumo de alcohol.'})

        if paciente.antecedentes_familiares:
            factores.append({'nombre': 'Antecedentes Familiares', 'valor': 'Sí', 'nivel': 'medio', 'descripcion': 'Existen antecedentes familiares de enfermedades cardiovasculares o metabólicas que aumentan el riesgo genético.'})
        else:
            factores.append({'nombre': 'Antecedentes Familiares', 'valor': 'No', 'nivel': 'normal', 'descripcion': 'Sin antecedentes familiares relevantes.'})

        # Recomendaciones basadas en el nivel de riesgo
        recomendaciones = []
        if riesgo in ('Crítico', 'Alto'):
            recomendaciones.append('Se requiere atención médica URGENTE. Algunos indicadores presentan valores críticos.')
            recomendaciones.append('Realizar estudios complementarios de laboratorio y gabinete de forma inmediata.')
            recomendaciones.append('Monitoreo continuo de signos vitales. Considerar hospitalización si es necesario.')
        if glu > 140 or col > 200:
            recomendaciones.append('Reducir el consumo de azúcares refinados y carbohidratos simples. Consultar con endocrinología para manejo de glucemia.')
        if col > 200:
            recomendaciones.append('Reducir consumo de grasas saturadas y trans. Incluir ácidos grasos omega-3 (pescado, nueces, linaza).')
        if spo2 < 90:
            recomendaciones.append('Evaluación respiratoria urgente por neumología. Posible necesidad de oxigenoterapia complementaria.')
        if fc > 100 or sist > 140:
            recomendaciones.append('Evaluación cardiológica con electrocardiograma. Evitar estimulantes como cafeína, tabaco y bebidas energéticas.')
        if paciente.fumador:
            recomendaciones.append('Programa de cesación tabáquica. El tabaco es el principal factor de riesgo modificable.')
        if paciente.consumo_alcohol:
            recomendaciones.append('Reducir o eliminar el consumo de alcohol. Consultar con especialista en adicciones si es necesario.')
        if riesgo == 'Bajo':
            recomendaciones.append('Mantener hábitos saludables. Realizar chequeos preventivos anuales.')
            recomendaciones.append('Actividad física regular (150 min/semana). Dieta equilibrada rica en frutas y verduras.')

        return {
            'paciente': {
                'id': paciente.id_paciente,
                'nombres': paciente.nombres,
                'apellidos': paciente.apellidos,
                'edad': paciente.edad,
                'sexo': paciente.sexo,
            },
            'prediccion': {
                'riesgo': riesgo,
                'confianza': confianza,
                'probabilidades': probs,
            },
            'factores_clave': factores,
            'recomendaciones': recomendaciones,
        }


class MotorPredictivoVITA:

    @staticmethod
    def entrenar_pipeline_ml(df: pd.DataFrame):
        columnas_predictoras = ['edad', 'imc', 'glucosa', 'colesterol', 'presion_sistolica', 'frecuencia_cardiaca', 'fumador']
        columna_objetivo = 'enfermedad'

        for col in columnas_predictoras + [columna_objetivo]:
            if col not in df.columns:
                raise ValueError(f"Falta la columna requerida para ML: {col}")

        X = df[columnas_predictoras]
        y = df[columna_objetivo]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        modelo = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10, class_weight='balanced')
        modelo.fit(X_train_scaled, y_train)

        y_pred = modelo.predict(X_test_scaled)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)

        cm = confusion_matrix(y_test, y_pred)
        matriz_estructurada = {
            "verdaderos_negativos": int(cm[0][0]),
            "falsos_positivos": int(cm[0][1]),
            "falsos_negativos": int(cm[1][0]),
            "verdaderos_positivos": int(cm[1][1])
        }

        MetricasModeloML.objects.update(modelo_activo=False)

        registro_metricas = MetricasModeloML.objects.create(
            accuracy=float(acc),
            precision=float(prec),
            recall=float(rec),
            f1_score=float(f1),
            matriz_confusion=matriz_estructurada,
            modelo_activo=True
        )

        os.makedirs(os.path.join(settings.BASE_DIR, 'media', 'modelos_ml'), exist_ok=True)
        joblib.dump(modelo, os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'random_forest_vita.pkl'))
        joblib.dump(scaler, os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'scaler_vita.pkl'))

        return registro_metricas