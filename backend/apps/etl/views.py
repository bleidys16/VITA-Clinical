import uuid
import os
import io
import pandas as pd
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsAdministrador, IsAnalista, EsAdminOMedico, EsAdminOAnalista
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.db.models import Q, Avg
from django.db import models
from django.contrib.auth.models import User
from .services import PipelineETL
from .models import Paciente, HistorialETL, DashboardKPIs, Perfil
from .analytics import calcular_analitica_dataset, recalcular_kpis_desde_db
from .tasks import ejecutar_pipeline_asincrono, TASK_ID_KEY



@method_decorator(csrf_exempt, name='dispatch')
class ETLLogListView(View):
    def get(self, request, format=None):
        historial = HistorialETL.objects.all().order_by('-fecha')
        logs_records = []
        for h in historial:
            logs_records.append({
                'fecha_ejecucion': h.fecha.isoformat() if h.fecha else None,
                'registros_procesados': h.registros_procesados,
                'tiempo_ejecucion': h.tiempo_ejecucion,
                'usuario_responsable': h.usuario.username if h.usuario else 'Sistema',
                'estado': h.estado,
            })
        return JsonResponse(logs_records, safe=False, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class ResetDataView(APIView):
    permission_classes = [IsAuthenticated, (IsAdministrador | IsAnalista)]

    def delete(self, request, format=None):
        try:
            pacientes_borrados = Paciente.objects.count()
            Paciente.objects.all().delete()
            HistorialETL.objects.all().delete()
            DashboardKPIs.objects.all().delete()
            return Response({
                "status": "success",
                "message": f"Datos restablecidos. {pacientes_borrados} registros eliminados."
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Error al restablecer datos: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RunETLView(APIView):
    permission_classes = [IsAuthenticated, (IsAdministrador | IsAnalista)]

    def post(self, request, format=None):
        if 'file' not in request.FILES:
            return Response({
                "status": "error",
                "message": "No se ha seleccionado ningún archivo para procesar."
            }, status=status.HTTP_400_BAD_REQUEST)

        archivo_subido = request.FILES['file']

        try:
            upload_dir = 'temp_uploads/'
            os.makedirs(upload_dir, exist_ok=True)

            ext = os.path.splitext(archivo_subido.name)[1] or '.csv'
            nombre_unico = f"{uuid.uuid4().hex}{ext}"
            ruta_guardado = f"{upload_dir}/{nombre_unico}"

            with open(ruta_guardado, 'wb+') as destino:
                for chunk in archivo_subido.chunks():
                    destino.write(chunk)

            usuario_id = request.user.id if request.user.is_authenticated else None

            ejecutar_pipeline_asincrono.delay(ruta_guardado, usuario_id=usuario_id)

            return Response({
                "status": "accepted",
                "message": "El archivo se ha recibido correctamente y se está procesando en segundo plano."
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            return Response({
                "status": "error",
                "message": f"Ocurrió un error al recibir el archivo: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PacienteListView(APIView):
    permission_classes = [IsAuthenticated, EsAdminOMedico]

    def get(self, request, format=None):
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        if page < 1: page = 1
        if page_size < 1: page_size = 50
        if page_size > 5000: page_size = 5000

        queryset = Paciente.objects.all().order_by('id_paciente')
        total = queryset.count()
        inicio = (page - 1) * page_size
        fin = inicio + page_size
        pacientes = queryset[inicio:fin]

        data = []
        for p in pacientes:
            imc = round(p.imc, 1) if p.imc else 0
            if imc < 18.5:
                clas_imc = 'Bajo peso'
                color_imc = 'warning'
            elif imc < 25:
                clas_imc = 'Normal'
                color_imc = 'success'
            elif imc < 30:
                clas_imc = 'Sobrepeso'
                color_imc = 'warning'
            else:
                clas_imc = 'Obesidad'
                color_imc = 'danger'

            riesgo = p.riesgo_enfermedad or 'Bajo'
            color_riesgo = {
                'Bajo': 'success', 'Medio': 'warning', 'Alto': 'danger', 'Crítico': 'dark'
            }.get(riesgo, 'secondary')

            data.append({
                "id_paciente": p.id_paciente,
                "nombres": p.nombres,
                "apellidos": p.apellidos,
                "edad": p.edad,
                "sexo": p.sexo,
                "imc": imc,
                "clasificacion_imc": clas_imc,
                "color_imc": color_imc,
                "presion_sistolica": p.presion_sistolica,
                "presion_diastolica": p.presion_diastolica,
                "glucosa": p.glucosa,
                "saturacion_oxigeno": p.saturacion_oxigeno,
                "temperatura": p.temperatura,
                "fumador": p.fumador,
                "consumo_alcohol": p.consumo_alcohol,
                "antecedentes_familiares": p.antecedentes_familiares,
                "diagnostico_preliminar": p.diagnostico_preliminar,
                "riesgo_enfermedad": riesgo,
                "color_riesgo": color_riesgo,
            })
        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),
            "results": data,
        }, status=status.HTTP_200_OK)


class DashboardAnalyticsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ultimo_kpi = DashboardKPIs.objects.order_by('-fecha_calculo').first()
        if not ultimo_kpi:
            return Response({"sistema_vacio": True})

        return Response({
            "sistema_vacio": False,
            "kpis": {
                "total_registros": ultimo_kpi.total_registros,
                "pacientes_criticos": ultimo_kpi.pacientes_criticos,
                "pacientes_hipertensos": ultimo_kpi.pacientes_hipertensos,
                "pacientes_diabeticos": ultimo_kpi.pacientes_diabeticos,
                "pacientes_fumadores": ultimo_kpi.pacientes_fumadores,
                "riesgo_promedio": ultimo_kpi.riesgo_promedio,
            },
            "estadistica_descriptiva": {
                "edad": {
                    "media": ultimo_kpi.edad_media,
                    "mediana": ultimo_kpi.edad_mediana,
                    "moda": ultimo_kpi.edad_moda,
                    "desviacion": ultimo_kpi.edad_desviacion,
                },
                "glucosa": {
                    "media": ultimo_kpi.glucosa_media,
                    "desviacion": ultimo_kpi.glucosa_desviacion,
                },
            },
        })


class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        rol = user.perfil.rol if hasattr(user, 'perfil') else None
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "rol": rol,
        })

class ProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        rol = user.perfil.rol if hasattr(user, 'perfil') else None
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "rol": rol,
        })

    def put(self, request):
        user = request.user
        data = request.data

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if username and username != user.username:
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return Response({"error": "El nombre de usuario ya está en uso"}, status=status.HTTP_400_BAD_REQUEST)
            user.username = username

        if email and email != user.email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({"error": "El correo ya está registrado"}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email

        if current_password and new_password:
            if not user.check_password(current_password):
                return Response({"error": "Contraseña actual incorrecta"}, status=status.HTTP_400_BAD_REQUEST)
            if len(new_password) < 6:
                return Response({"error": "La nueva contraseña debe tener al menos 6 caracteres"}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)

        user.save()
        rol = user.perfil.rol if hasattr(user, 'perfil') else None
        return Response({
            "mensaje": "Perfil actualizado correctamente",
            "username": user.username,
            "email": user.email,
            "rol": rol,
        })

class DashboardDataView(APIView):
    permission_classes = [IsAuthenticated, EsAdminOMedico]

    def get(self, request, format=None):
        ultimo_kpi = DashboardKPIs.objects.order_by('-fecha_calculo').first()

        if not ultimo_kpi and Paciente.objects.exists():
            ultimo_kpi = recalcular_kpis_desde_db()

        if not ultimo_kpi:
            return Response({"sistema_vacio": True}, status=status.HTTP_200_OK)

        pacientes = Paciente.objects.all()
        total = pacientes.count()

        edad_promedio = round(ultimo_kpi.edad_media, 1)

        riesgo_promedio = ultimo_kpi.riesgo_promedio
        if not riesgo_promedio:
            riesgo_map = {'Bajo': 0.25, 'Medio': 0.50, 'Alto': 0.75, 'Crítico': 1.0}
            valores = []
            for r in ['Bajo', 'Medio', 'Alto', 'Crítico']:
                cnt = pacientes.filter(riesgo_enfermedad=r).count()
                valores.extend([riesgo_map[r]] * cnt)
            riesgo_promedio = round((sum(valores) / len(valores) * 100) if valores else 0, 2)

        rangos_edad = [
            {'rango': '<30', 'min': 0, 'max': 29},
            {'rango': '30-49', 'min': 30, 'max': 49},
            {'rango': '50-69', 'min': 50, 'max': 69},
            {'rango': '70+', 'min': 70, 'max': 200},
        ]
        segmentacion_edad = []
        labels_barras = []
        for r in rangos_edad:
            qs = pacientes.filter(edad__gte=r['min'], edad__lte=r['max'])
            total_rango = qs.count()
            labels_info = {}
            for diag in pacientes.filter(edad__gte=r['min'], edad__lte=r['max']).values_list('diagnostico_preliminar', flat=True):
                d = diag or 'Sin diagnóstico'
                labels_info[d] = labels_info.get(d, 0) + 1
            segmentacion_edad.append({
                'rango': r['rango'],
                'total': total_rango,
                'diagnosticos': [{'nombre': k, 'cantidad': v} for k, v in labels_info.items()]
            })
            labels_barras.append(r['rango'])

        tendencias = []
        for p in pacientes.order_by('edad').values('edad', 'presion_sistolica', 'glucosa'):
            tendencias.append({
                'edad': p['edad'],
                'presion_sistolica': p['presion_sistolica'],
                'glucosa': p['glucosa'],
            })

        orden_riesgo = ['Bajo', 'Medio', 'Alto', 'Crítico']
        labels_riesgo = ['Riesgo Bajo', 'Riesgo Medio', 'Riesgo Alto', 'Riesgo Crítico']
        riesgo_torta_series = [pacientes.filter(riesgo_enfermedad=riesgo).count() for riesgo in orden_riesgo]

        sexo_riesgo_data = []
        for sexo_val in ['Masculino', 'Femenino']:
            qs_sexo = pacientes.filter(sexo__iexact=sexo_val)
            for riesgo in orden_riesgo:
                count = qs_sexo.filter(riesgo_enfermedad=riesgo).count()
                if count > 0:
                    sexo_riesgo_data.append({
                        'sexo': sexo_val,
                        'riesgo': riesgo,
                        'cantidad': count
                    })

        ultimas_consultas = []
        for p in pacientes.order_by('-fecha_consulta', '-id_paciente')[:6]:
            sexo_icon = 'fa-venus' if p.sexo and 'femenino' in p.sexo.lower() else 'fa-mars'
            ultimas_consultas.append({
                'id': p.id_paciente,
                'nombres': p.nombres,
                'apellidos': p.apellidos,
                'edad': p.edad,
                'sexo': p.sexo,
                'sexo_icon': sexo_icon,
                'diagnostico': p.diagnostico_preliminar or 'Sin diagnóstico',
                'riesgo': p.riesgo_enfermedad or 'Sin riesgo',
                'fecha_consulta': p.fecha_consulta.isoformat() if p.fecha_consulta else None,
            })

        return Response({
            "sistema_vacio": False,
            "kpis": {
                "total_registros": ultimo_kpi.total_registros,
                "pacientes_criticos": ultimo_kpi.pacientes_criticos,
                "edad_promedio": edad_promedio,
                "riesgo_promedio": riesgo_promedio
            },
            "graficas": {
                "barras_segmentacion": segmentacion_edad,
                "labels_barras": labels_barras,
                "tendencias": tendencias,
                "riesgo_torta": {
                    "labels": labels_riesgo,
                    "series": riesgo_torta_series
                },
                "sexo_riesgo_torta": sexo_riesgo_data
            },
            "estadistica_descriptiva": {
                "edad": {
                    "media": round(ultimo_kpi.edad_media, 2),
                    "mediana": round(ultimo_kpi.edad_mediana, 2),
                    "moda": round(ultimo_kpi.edad_moda, 2),
                    "desviacion": round(ultimo_kpi.edad_desviacion, 2)
                },
                "glucosa": {
                    "media": round(ultimo_kpi.glucosa_media, 2),
                    "desviacion": round(ultimo_kpi.glucosa_desviacion, 2)
                }
            },
            "indicadores_clinicos": {
                "glucosa_promedio": round(ultimo_kpi.glucosa_media, 1),
                "imc_promedio": round(pacientes.filter(imc__isnull=False).aggregate(Avg('imc'))['imc__avg'] or 0, 1),
                "porcentaje_criticos": round((ultimo_kpi.pacientes_criticos / total * 100), 1) if total else 0,
                "porcentaje_riesgo_alto": round((pacientes.filter(riesgo_enfermedad='Alto').count() / total * 100), 1) if total else 0,
            },
            "ultimas_consultas": ultimas_consultas,
        }, status=status.HTTP_200_OK)


class ETLEstadoView(APIView):
    permission_classes = [IsAuthenticated, EsAdminOAnalista]

    def get(self, request, format=None):
        task_id = cache.get(TASK_ID_KEY)
        if not task_id:
            return Response({"activo": False, "logs": []}, status=status.HTTP_200_OK)

        data = cache.get(f'etl_status_{task_id}')
        if not data:
            return Response({"activo": False, "logs": []}, status=status.HTTP_200_OK)

        log_history = cache.get(f'etl_logs_{task_id}', [])

        return Response({
            "activo": data['fase'] != 'DONE',
            "fase": data['fase'],
            "mensaje": data['mensaje'],
            "detalle": data['detalle'],
            "logs": log_history,
        }, status=status.HTTP_200_OK)


class ReportesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        formato = request.query_params.get('formato', 'excel')
        user = request.user
        if hasattr(user, 'perfil') and user.perfil.rol == 'MEDICO' and formato != 'pdf':
            return Response({"error": "Los médicos solo pueden exportar en formato PDF."}, status=status.HTTP_403_FORBIDDEN)
        pacientes_qs = Paciente.objects.all().order_by('id_paciente')

        if not pacientes_qs.exists():
            return Response({"error": "No hay pacientes registrados"}, status=status.HTTP_404_NOT_FOUND)

        data = []
        for p in pacientes_qs:
            data.append({
                'ID': p.id_paciente,
                'Nombres': p.nombres,
                'Apellidos': p.apellidos,
                'Edad': p.edad,
                'Sexo': p.sexo,
                'Peso': p.peso,
                'Altura': p.altura,
                'IMC': p.imc,
                'Clasificacion_IMC': p.clasificacion_imc,
                'Presion_Sistolica': p.presion_sistolica,
                'Presion_Diastolica': p.presion_diastolica,
                'Frecuencia_Cardiaca': p.frecuencia_cardiaca,
                'Glucosa': p.glucosa,
                'Colesterol': p.colesterol,
                'Saturacion_Oxigeno': p.saturacion_oxigeno,
                'Temperatura': p.temperatura,
                'Antecedentes_Familiares': p.antecedentes_familiares,
                'Fumador': p.fumador,
                'Consumo_Alcohol': p.consumo_alcohol,
                'Diagnostico': p.diagnostico_preliminar,
                'Riesgo': p.riesgo_enfermedad,
                'Fecha_Consulta': p.fecha_consulta,
            })

        df = pd.DataFrame(data)

        if formato in ('xlsx', 'csv', 'excel'):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Pacientes', index=False)
            output.seek(0)
            ext = 'xlsx'
            response = HttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="reporte_vita_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{ext}"'
            return response
        elif formato == 'pdf':
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.lib.colors import HexColor
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
                from reportlab.lib import colors

                output = io.BytesIO()
                doc = SimpleDocTemplate(
                    output, pagesize=letter,
                    rightMargin=72, leftMargin=72,
                    topMargin=72, bottomMargin=72,
                )

                styles = getSampleStyleSheet()
                title_style = ParagraphStyle(
                    'CustomTitle', parent=styles['Title'],
                    fontName='Helvetica-Bold', fontSize=18,
                    textColor=HexColor('#3F2A52'),
                    spaceAfter=6,
                )
                subtitle_style = ParagraphStyle(
                    'Subtitle', parent=styles['Normal'],
                    fontSize=10, textColor=HexColor('#75619D'),
                    spaceAfter=20,
                )
                normal_style = ParagraphStyle(
                    'CustomNormal', parent=styles['Normal'],
                    fontSize=8,
                )

                elements = []
                elements.append(Paragraph("VITA Clinical", title_style))
                elements.append(Paragraph("Vital Tracking in Healthcare Analytics - Reporte de Pacientes", subtitle_style))
                elements.append(Spacer(1, 0.2 * inch))

                kpi_data = DashboardKPIs.objects.first()
                if kpi_data:
                    kpi_text = (
                        f"Total Registros: {kpi_data.total_registros} | "
                        f"Pacientes Críticos: {kpi_data.pacientes_criticos} | "
                        f"Edad Promedio: {round(kpi_data.edad_media, 1)} | "
                        f"Riesgo Promedio: {round(kpi_data.riesgo_promedio, 1)}%"
                    )
                    elements.append(Paragraph(kpi_text, subtitle_style))
                    elements.append(Spacer(1, 0.2 * inch))

                table_data = [[
                    'ID', 'Paciente', 'Edad', 'Sexo', 'IMC', 'PA Sys',
                    'Glucosa', 'SatO2', 'Riesgo'
                ]]
                for p in pacientes_qs:
                    table_data.append([
                        str(p.id_paciente),
                        f"{p.nombres} {p.apellidos}",
                        str(p.edad),
                        p.sexo or '',
                        f"{round(p.imc, 1) if p.imc else 'N/A'}",
                        str(p.presion_sistolica or ''),
                        str(p.glucosa or ''),
                        f"{p.saturacion_oxigeno or ''}",
                        p.riesgo_enfermedad or '',
                    ])

                col_widths = [40, 120, 40, 50, 45, 45, 45, 45, 60]
                table = Table(table_data, colWidths=col_widths, repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#3F2A52')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 7),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#BEAEDB')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, HexColor('#F5F0FF')]),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(table)
                elements.append(Spacer(1, 0.3 * inch))
                elements.append(Paragraph(
                    f"Reporte generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} - VITA Clinical Engine",
                    ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=HexColor('#999999'))
                ))

                doc.build(elements)
                output.seek(0)
                response = HttpResponse(output.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="reporte_vita_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
                return response

            except ImportError:
                return Response(
                    {"error": "reportlab no está instalado. Instálalo con: pip install reportlab"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        return Response({"error": "Formato no soportado. Usa: excel, csv, pdf"}, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
# PACIENTE CRUD (solo ADMIN)
# ──────────────────────────────────────────────

class PacienteCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador]

    def post(self, request, format=None):
        data = request.data
        try:
            max_id = Paciente.objects.aggregate(models.Max('id_paciente'))['id_paciente__max'] or 0
            paciente = Paciente.objects.create(
                id_paciente=data.get('id_paciente', max_id + 1),
                nombres=data.get('nombres', ''),
                apellidos=data.get('apellidos', ''),
                edad=int(data.get('edad', 0)),
                sexo=data.get('sexo', ''),
                peso=float(data['peso']) if data.get('peso') else None,
                altura=float(data['altura']) if data.get('altura') else None,
                presion_sistolica=int(data['presion_sistolica']) if data.get('presion_sistolica') else None,
                presion_diastolica=int(data['presion_diastolica']) if data.get('presion_diastolica') else None,
                frecuencia_cardiaca=int(data['frecuencia_cardiaca']) if data.get('frecuencia_cardiaca') else None,
                glucosa=float(data['glucosa']) if data.get('glucosa') else None,
                colesterol=float(data['colesterol']) if data.get('colesterol') else None,
                saturacion_oxigeno=float(data['saturacion_oxigeno']) if data.get('saturacion_oxigeno') else None,
                temperatura=float(data['temperatura']) if data.get('temperatura') else None,
                antecedentes_familiares=data.get('antecedentes_familiares', False) in (True, 'true', '1'),
                fumador=data.get('fumador', False) in (True, 'true', '1'),
                consumo_alcohol=data.get('consumo_alcohol', False) in (True, 'true', '1'),
                actividad_fisica=data.get('actividad_fisica', ''),
                diagnostico_preliminar=data.get('diagnostico_preliminar', ''),
                fecha_consulta=data.get('fecha_consulta', None),
            )
            return Response({"status": "success", "paciente_id": paciente.id_paciente}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PacienteDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador]

    def put(self, request, paciente_id, format=None):
        try:
            paciente = Paciente.objects.get(id_paciente=paciente_id)
        except Paciente.DoesNotExist:
            return Response({"error": "Paciente no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        for campo in ('nombres', 'apellidos', 'sexo', 'actividad_fisica', 'diagnostico_preliminar'):
            if campo in data:
                setattr(paciente, campo, data[campo])
        for campo in ('edad',):
            if campo in data:
                setattr(paciente, campo, int(data[campo]))
        for campo in ('peso', 'altura', 'glucosa', 'colesterol', 'saturacion_oxigeno', 'temperatura'):
            if campo in data:
                setattr(paciente, campo, float(data[campo]) if data[campo] else None)
        for campo in ('presion_sistolica', 'presion_diastolica', 'frecuencia_cardiaca'):
            if campo in data:
                setattr(paciente, campo, int(data[campo]) if data[campo] else None)
        for campo in ('antecedentes_familiares', 'fumador', 'consumo_alcohol'):
            if campo in data:
                setattr(paciente, campo, data[campo] in (True, 'true', '1'))
        if 'fecha_consulta' in data:
            paciente.fecha_consulta = data['fecha_consulta'] or None
        paciente.save()
        return Response({"status": "success"})


    def delete(self, request, paciente_id, format=None):
        try:
            paciente = Paciente.objects.get(id_paciente=paciente_id)
            paciente.delete()
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except Paciente.DoesNotExist:
            return Response({"error": "Paciente no encontrado"}, status=status.HTTP_404_NOT_FOUND)


# ──────────────────────────────────────────────
# USUARIOS CRUD (solo ADMIN)
# ──────────────────────────────────────────────

class UsuarioListView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador]

    def get(self, request, format=None):
        usuarios = User.objects.all().order_by('id')
        data = []
        for u in usuarios:
            rol = u.perfil.rol if hasattr(u, 'perfil') else 'MEDICO'
            data.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "rol": rol,
                "is_active": u.is_active,
                "date_joined": u.date_joined.isoformat(),
            })
        return Response(data)


class UsuarioCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador]

    def post(self, request, format=None):
        data = request.data
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        rol = data.get('rol', 'MEDICO')

        if not username or not password:
            return Response({"error": "Usuario y contraseña requeridos"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"error": "El nombre de usuario ya existe"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password)
        Perfil.objects.create(user=user, rol=rol)
        return Response({"status": "success", "user_id": user.id}, status=status.HTTP_201_CREATED)


class UsuarioUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador]

    def put(self, request, user_id, format=None):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        if 'email' in data:
            user.email = data['email']
        if 'username' in data:
            user.username = data['username']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        if 'is_active' in data:
            user.is_active = data['is_active'] in (True, 'true', '1')
        user.save()

        if 'rol' in data and hasattr(user, 'perfil'):
            user.perfil.rol = data['rol']
            user.perfil.save()
        elif 'rol' in data:
            Perfil.objects.create(user=user, rol=data['rol'])

        return Response({"status": "success"})


class UsuarioDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsAdministrador]

    def delete(self, request, user_id, format=None):
        if request.user.id == user_id:
            return Response({"error": "No puedes eliminarte a ti mismo"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)