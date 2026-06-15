import pandas as pd
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from apps.etl.permissions import EsAdminOMedico
from apps.analytics.services import IndicadoresClinicosService
from apps.etl.models import Paciente

class DashboardKPIsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        try:
            service = IndicadoresClinicosService()
            estadisticas = service.obtener_estadisticas_descriptivas()
            kpis = service.obtener_kpis_dashboard()
            return Response({
                "status": "success",
                "plataforma": "VITA (Vital Tracking in Healthcare Analytics)",
                "kpis_consolidados": kpis,
                "estadistica_descriptiva": estadisticas
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error al consolidar los indicadores analíticos: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DescriptiveAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, EsAdminOMedico]

    def get(self, request, format=None):
        try:
            pacientes = Paciente.objects.all().values()
            if not pacientes:
                return Response({"error": "No hay pacientes registrados"}, status=status.HTTP_404_NOT_FOUND)

            df = pd.DataFrame(pacientes)

            columnas_numericas = [
                'edad', 'presion_sistolica', 'presion_diastolica',
                'glucosa', 'colesterol', 'frecuencia_cardiaca',
                'imc', 'temperatura'
            ]
            etiquetas_columnas = {
                'edad': 'Edad', 'presion_sistolica': 'Presión Sistólica',
                'presion_diastolica': 'Presión Diastólica', 'glucosa': 'Glucosa',
                'colesterol': 'Colesterol', 'frecuencia_cardiaca': 'Frecuencia Cardíaca',
                'imc': 'IMC', 'temperatura': 'Temperatura'
            }

            cols_existentes = [c for c in columnas_numericas if c in df.columns]

            matriz_descriptiva = {}
            for col in cols_existentes:
                serie = df[col].dropna()
                if len(serie) == 0:
                    continue
                matriz_descriptiva[col] = {
                    "count": int(len(serie)),
                    "mean": round(float(serie.mean()), 2),
                    "median": round(float(serie.median()), 2),
                    "mode": round(float(serie.mode().iloc[0]), 2) if not serie.mode().empty else 0,
                    "std": round(float(serie.std()), 2),
                    "min": round(float(serie.min()), 2),
                    "max": round(float(serie.max()), 2),
                    "p25": round(float(serie.quantile(0.25)), 2),
                    "p75": round(float(serie.quantile(0.75)), 2),
                }

            total = len(df)

            distribucion_imc = []
            if 'clasificacion_imc' in df.columns:
                imc_counts = df['clasificacion_imc'].value_counts()
                orden_imc = ['Bajo peso', 'Normal', 'Sobrepeso', 'Obesidad']
                for cls in orden_imc:
                    cant = int(imc_counts.get(cls, 0))
                    distribucion_imc.append({
                        "clasificacion": cls,
                        "cantidad": cant,
                        "porcentaje": round(cant / total * 100, 2)
                    })

            comorbilidad_sexo = {}
            diag_lower = df['diagnostico_preliminar'].astype(str).str.lower().str.strip() if 'diagnostico_preliminar' in df.columns else pd.Series()
            for patologia, kw in [('Hipertensión', 'hipertens'), ('Diabetes', 'diabet')]:
                masc = df[(df['sexo'] == 'Masculino') & diag_lower.str.contains(kw, na=False)].shape[0] if not diag_lower.empty else 0
                fem = df[(df['sexo'] == 'Femenino') & diag_lower.str.contains(kw, na=False)].shape[0] if not diag_lower.empty else 0
                comorbilidad_sexo[patologia] = {"Masculino": masc, "Femenino": fem}

            riesgo_masc = df[(df['sexo'] == 'Masculino') & (df['riesgo_enfermedad'] == 'Alto')].shape[0] if 'riesgo_enfermedad' in df.columns else 0
            riesgo_fem = df[(df['sexo'] == 'Femenino') & (df['riesgo_enfermedad'] == 'Alto')].shape[0] if 'riesgo_enfermedad' in df.columns else 0
            comorbilidad_sexo['Riesgo Alto'] = {"Masculino": riesgo_masc, "Femenino": riesgo_fem}

            prevalencia = {}
            if total > 0:
                col_diag = 'diagnostico_preliminar'
                if col_diag in df.columns:
                    diag_lower = df[col_diag].astype(str).str.lower().str.strip()
                    hipertensos = int(diag_lower.str.contains('hipertens', na=False).sum())
                    diabeticos = int(diag_lower.str.contains('diabet', na=False).sum())
                else:
                    hipertensos = 0
                    diabeticos = 0

                fumadores = int(df['fumador'].sum()) if 'fumador' in df.columns else 0

                prevalencia = {
                    "total_pacientes": total,
                    "hipertensos": {"cantidad": hipertensos, "proporcion": round(hipertensos / total * 100, 2)},
                    "diabeticos": {"cantidad": diabeticos, "proporcion": round(diabeticos / total * 100, 2)},
                    "fumadores": {"cantidad": fumadores, "proporcion": round(fumadores / total * 100, 2)},
                }

            return Response({
                "status": "success",
                "total_pacientes": total,
                "matriz_descriptiva": matriz_descriptiva,
                "etiquetas_columnas": etiquetas_columnas,
                "prevalencia_patologias": prevalencia,
                "distribucion_imc": distribucion_imc,
                "comorbilidad_sexo": comorbilidad_sexo,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error al generar estadística descriptiva: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)