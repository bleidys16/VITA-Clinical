import joblib
import os

import numpy as np
import pandas as pd
from django.conf import settings
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from apps.etl.models import Paciente, MetricasModeloML


class PredictorRiesgoService:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()

    def preparar_datos(self):
        pacientes = Paciente.objects.all().values()
        if not pacientes:
            raise ValueError("No hay pacientes registrados en la base de datos.")

        df = pd.DataFrame(pacientes)

        score = (
            (df['glucosa'] > 100).astype(int) +
            (df['presion_sistolica'] > 130).astype(int) +
            (df['colesterol'] > 200).astype(int) +
            (df['imc'] >= 25).astype(int) +
            (df['frecuencia_cardiaca'] > 90).astype(int) +
            (df['saturacion_oxigeno'] < 95).astype(int) +
            (df['edad'] > 50).astype(int) +
            (df['fumador'] == True).astype(int)
        )

        df['riesgo_enfermedad'] = 'Bajo'
        df.loc[score >= 1, 'riesgo_enfermedad'] = 'Medio'
        df.loc[score >= 3, 'riesgo_enfermedad'] = 'Alto'
        df.loc[score >= 5, 'riesgo_enfermedad'] = 'Crítico'

        features = [
            'edad', 'peso', 'altura', 'imc',
            'presion_sistolica', 'presion_diastolica',
            'frecuencia_cardiaca', 'glucosa', 'colesterol',
            'saturacion_oxigeno', 'temperatura',
            'antecedentes_familiares', 'fumador', 'consumo_alcohol'
        ]

        X = df[features].copy()

        for col in ['antecedentes_familiares', 'fumador', 'consumo_alcohol']:
            X[col] = X[col].astype(int)

        y = self.label_encoder.fit_transform(df['riesgo_enfermedad'])

        return X, y

    def entrenar_modelo(self):
        X, y = self.preparar_datos()

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        self.model.fit(X_train_scaled, y_train)

        y_pred = self.model.predict(X_test_scaled)

        target_names = self.label_encoder.classes_
        from sklearn.metrics import classification_report
        reporte_dict = classification_report(y_test, y_pred, target_names=target_names, output_dict=True)

        return reporte_dict


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
