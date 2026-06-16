import pandas as pd
import numpy as np
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q as DjQ
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
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            pacientes = Paciente.objects.all().values()
            if not pacientes:
                return Response({"error": "No hay pacientes registrados"}, status=status.HTTP_404_NOT_FOUND)

            df = pd.DataFrame(pacientes)

            total = len(df)

            # ── Matriz Descriptiva (9 variables) ──
            columnas_numericas = [
                'edad', 'presion_sistolica', 'presion_diastolica',
                'glucosa', 'colesterol', 'frecuencia_cardiaca',
                'imc', 'temperatura', 'saturacion_oxigeno'
            ]
            etiquetas_columnas = {
                'edad': 'Edad', 'presion_sistolica': 'Presión Sistólica',
                'presion_diastolica': 'Presión Diastólica', 'glucosa': 'Glucosa',
                'colesterol': 'Colesterol', 'frecuencia_cardiaca': 'Frecuencia Cardíaca',
                'imc': 'IMC', 'temperatura': 'Temperatura',
                'saturacion_oxigeno': 'Sat. Oxígeno'
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

            # ── Distribución IMC ──
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

            # ── Comorbilidad por sexo ──
            comorbilidad_sexo = {}
            diag_lower = df['diagnostico_preliminar'].astype(str).str.lower().str.strip() if 'diagnostico_preliminar' in df.columns else pd.Series()
            for patologia, kw in [('Hipertensión', 'hipertens'), ('Diabetes', 'diabet')]:
                masc = df[(df['sexo'] == 'Masculino') & diag_lower.str.contains(kw, na=False)].shape[0] if not diag_lower.empty else 0
                fem = df[(df['sexo'] == 'Femenino') & diag_lower.str.contains(kw, na=False)].shape[0] if not diag_lower.empty else 0
                comorbilidad_sexo[patologia] = {"Masculino": masc, "Femenino": fem}

            riesgo_masc = df[(df['sexo'] == 'Masculino') & (df['riesgo_enfermedad'] == 'Alto')].shape[0] if 'riesgo_enfermedad' in df.columns else 0
            riesgo_fem = df[(df['sexo'] == 'Femenino') & (df['riesgo_enfermedad'] == 'Alto')].shape[0] if 'riesgo_enfermedad' in df.columns else 0
            comorbilidad_sexo['Riesgo Alto'] = {"Masculino": riesgo_masc, "Femenino": riesgo_fem}

            # ── Prevalencia (7 KPIs) ──
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

                obesos = 0
                if 'clasificacion_imc' in df.columns:
                    obesos = int((df['clasificacion_imc'].astype(str).str.lower().str.strip() == 'obesidad').sum())
                elif 'imc' in df.columns:
                    obesos = int((df['imc'] >= 30).sum())

                antecedentes = int(df['antecedentes_familiares'].sum()) if 'antecedentes_familiares' in df.columns else 0
                alcohol = int(df['consumo_alcohol'].sum()) if 'consumo_alcohol' in df.columns else 0
                saturacion_baja = int((df['saturacion_oxigeno'] < 85).sum()) if 'saturacion_oxigeno' in df.columns else 0

                prevalencia = {
                    "total_pacientes": total,
                    "hipertensos": {"cantidad": hipertensos, "proporcion": round(hipertensos / total * 100, 2)},
                    "diabeticos": {"cantidad": diabeticos, "proporcion": round(diabeticos / total * 100, 2)},
                    "fumadores": {"cantidad": fumadores, "proporcion": round(fumadores / total * 100, 2)},
                    "obesos": {"cantidad": obesos, "proporcion": round(obesos / total * 100, 2)},
                    "antecedentes": {"cantidad": antecedentes, "proporcion": round(antecedentes / total * 100, 2)},
                    "alcohol": {"cantidad": alcohol, "proporcion": round(alcohol / total * 100, 2)},
                    "saturacion_baja": {"cantidad": saturacion_baja, "proporcion": round(saturacion_baja / total * 100, 2)},
                }

            # ── Alertas Clínicas ──
            alertas = {}
            if total > 0:
                sist_alta = int((df['presion_sistolica'] > 180).sum()) if 'presion_sistolica' in df.columns else 0
                gluc_alta = int((df['glucosa'] > 300).sum()) if 'glucosa' in df.columns else 0
                sat_baja = int((df['saturacion_oxigeno'] < 85).sum()) if 'saturacion_oxigeno' in df.columns else 0
                alertas = {
                    "sistolica_alta": {"cantidad": sist_alta, "descripcion": "Presión sistólica > 180 mmHg"},
                    "glucosa_alta": {"cantidad": gluc_alta, "descripcion": "Glucosa > 300 mg/dL"},
                    "saturacion_baja": {"cantidad": sat_baja, "descripcion": "Sat. Oxígeno < 85%"},
                }

            # ── Segmentación por Riesgo ──
            segmentacion_riesgo = []
            if 'riesgo_enfermedad' in df.columns:
                orden_riesgo = ['Bajo', 'Medio', 'Alto', 'Crítico']
                for nivel in orden_riesgo:
                    cant = int((df['riesgo_enfermedad'] == nivel).sum())
                    segmentacion_riesgo.append({
                        "nivel": nivel,
                        "cantidad": cant,
                        "porcentaje": round(cant / total * 100, 2)
                    })

            # ── Segmentación por Edad ──
            segmentacion_edad = []
            rangos_edad = [
                ("< 30", 0, 29), ("30-49", 30, 49),
                ("50-69", 50, 69), ("70+", 70, 200)
            ]
            for label, min_e, max_e in rangos_edad:
                cant = int(df[(df['edad'] >= min_e) & (df['edad'] <= max_e)].shape[0])
                segmentacion_edad.append({
                    "rango": label,
                    "cantidad": cant,
                    "porcentaje": round(cant / total * 100, 2)
                })

            return Response({
                "status": "success",
                "total_pacientes": total,
                "matriz_descriptiva": matriz_descriptiva,
                "etiquetas_columnas": etiquetas_columnas,
                "prevalencia_patologias": prevalencia,
                "alertas": alertas,
                "distribucion_imc": distribucion_imc,
                "segmentacion_riesgo": segmentacion_riesgo,
                "segmentacion_edad": segmentacion_edad,
                "comorbilidad_sexo": comorbilidad_sexo,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error al generar estadística descriptiva: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PacientesPorCriterioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        criterio = request.query_params.get('criterio', '')
        q = request.query_params.get('q', '').strip()

        pacientes_qs = Paciente.objects.all()

        if criterio == 'hipertensos':
            pacientes_qs = pacientes_qs.filter(diagnostico_preliminar__icontains='hipertens')
        elif criterio == 'diabeticos':
            pacientes_qs = pacientes_qs.filter(diagnostico_preliminar__icontains='diabet')
        elif criterio == 'fumadores':
            pacientes_qs = pacientes_qs.filter(fumador=True)
        elif criterio == 'obesos':
            pacientes_qs = pacientes_qs.filter(clasificacion_imc__iexact='obesidad')
        elif criterio == 'antecedentes':
            pacientes_qs = pacientes_qs.filter(antecedentes_familiares=True)
        elif criterio == 'alcohol':
            pacientes_qs = pacientes_qs.filter(consumo_alcohol=True)
        elif criterio == 'saturacion_baja':
            pacientes_qs = pacientes_qs.filter(saturacion_oxigeno__lt=85)
        elif criterio == 'sistolica_alta':
            pacientes_qs = pacientes_qs.filter(presion_sistolica__gt=180)
        elif criterio == 'glucosa_alta':
            pacientes_qs = pacientes_qs.filter(glucosa__gt=300)
        elif criterio == 'criticos':
            pacientes_qs = pacientes_qs.filter(
                DjQ(presion_sistolica__gt=180) | DjQ(glucosa__gt=300) | DjQ(saturacion_oxigeno__lt=85)
            )
        else:
            return Response({"error": "Criterio no válido"}, status=status.HTTP_400_BAD_REQUEST)

        if q:
            pacientes_qs = pacientes_qs.filter(
                DjQ(nombres__icontains=q) | DjQ(apellidos__icontains=q) |
                DjQ(diagnostico_preliminar__icontains=q)
            )

        pacientes_qs = pacientes_qs.order_by('id_paciente')
        total = pacientes_qs.count()
        pacientes_qs = pacientes_qs[:200]

        results = []
        for p in pacientes_qs:
            results.append({
                "id": p.id_paciente,
                "nombres": p.nombres,
                "apellidos": p.apellidos,
                "edad": p.edad,
                "sexo": p.sexo,
                "diagnostico": p.diagnostico_preliminar,
                "riesgo": p.riesgo_enfermedad,
            })

        return Response({"total": total, "results": results})
