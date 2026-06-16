import joblib
import os
import numpy as np
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.etl.models import MetricasModeloML
from apps.machine_learning.services import PredictorRiesgoService


class TrainModelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        user = request.user
        if hasattr(user, 'perfil') and user.perfil.rol not in ('ADMIN', 'ANALISTA'):
            return Response({"error": "No tenés permiso para entrenar el modelo."}, status=status.HTTP_403_FORBIDDEN)
        try:
            predictor = PredictorRiesgoService()
            reporte_metricas = predictor.entrenar_modelo()

            return Response({
                "status": "success",
                "modelo": "Random Forest Classifier - VITA Engine",
                "metricas_evaluacion": reporte_metricas
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Fallo al entrenar el modelo predictivo: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MetricasModeloMLView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        metricas = MetricasModeloML.objects.filter(modelo_activo=True).first()

        if not metricas:
            return Response({"modelo_entrenado": False}, status=status.HTTP_200_OK)

        cm = metricas.matriz_confusion

        heatmap_data = [
            {
                "name": "Sano Predicho (0)",
                "data": [
                    {"x": "Sano Real (0)", "y": cm["verdaderos_negativos"]},
                    {"x": "Enfermo Real (1)", "y": cm["falsos_negativos"]}
                ]
            },
            {
                "name": "Enfermo Predicho (1)",
                "data": [
                    {"x": "Sano Real (0)", "y": cm["falsos_positivos"]},
                    {"x": "Enfermo Real (1)", "y": cm["verdaderos_positivos"]}
                ]
            }
        ]

        return Response({
            "modelo_entrenado": True,
            "accuracy": round(metricas.accuracy * 100, 2),
            "precision": round(metricas.precision * 100, 2),
            "recall": round(metricas.recall * 100, 2),
            "f1_score": round(metricas.f1_score * 100, 2),
            "heatmap": heatmap_data
        }, status=status.HTTP_200_OK)


class PrediccionRiesgoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        modelo_path = os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'random_forest_vita.pkl')
        scaler_path = os.path.join(settings.BASE_DIR, 'media', 'modelos_ml', 'scaler_vita.pkl')

        if not os.path.exists(modelo_path):
            return Response({"error": "No hay modelo entrenado. Ejecutá el pipeline ETL primero."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            modelo = joblib.load(modelo_path)
            scaler = joblib.load(scaler_path)
        except Exception:
            return Response({"error": "Error al cargar el modelo guardado."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        columnas_requeridas = ['edad', 'imc', 'glucosa', 'colesterol', 'presion_sistolica', 'frecuencia_cardiaca']
        for col in columnas_requeridas:
            if col not in request.data:
                return Response({"error": f"Campo requerido: {col}"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            edad = float(request.data['edad'])
            imc = float(request.data['imc'])
            glucosa = float(request.data['glucosa'])
            colesterol = float(request.data['colesterol'])
            presion_sistolica = float(request.data['presion_sistolica'])
            frecuencia_cardiaca = float(request.data['frecuencia_cardiaca'])
            fumador = 1 if request.data.get('fumador', '').lower() in ('true', '1', 'si', 'sí') else 0
        except (ValueError, TypeError) as e:
            campo_error = str(e).split("'")[1] if "'" in str(e) else "desconocido"
            return Response({"error": f"Valor inválido en '{campo_error}'. Verificá los datos ingresados."}, status=status.HTTP_400_BAD_REQUEST)

        entrada = np.array([[edad, imc, glucosa, colesterol, presion_sistolica, frecuencia_cardiaca, fumador]])
        entrada_scaled = scaler.transform(entrada)
        prediccion = modelo.predict(entrada_scaled)[0]
        probabilidad = modelo.predict_proba(entrada_scaled)[0]

        riesgo = 'Sano' if prediccion == 0 else 'Enfermo'
        confianza = round(float(max(probabilidad) * 100), 2)

        return Response({
            "prediccion": riesgo,
            "confianza": confianza,
            "probabilidad_sano": round(float(probabilidad[0] * 100), 2),
            "probabilidad_enfermo": round(float(probabilidad[1] * 100), 2),
        }, status=status.HTTP_200_OK)
