from django.db import models
from django.contrib.auth.models import User


class Paciente(models.Model):
    objects = models.Manager()

    # Identificación básica (id_paciente del CSV como llave primaria)
    id_paciente = models.IntegerField(unique=True, primary_key=True)
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150)
    edad = models.IntegerField()
    sexo = models.CharField(max_length=20)

    # Variables de Antropometría (Peso y Talla)
    peso = models.FloatField(null=True, blank=True)
    altura = models.FloatField(null=True, blank=True)
    imc = models.FloatField(null=True, blank=True)  # Calculado en ETL
    clasificacion_imc = models.CharField(max_length=50, null=True, blank=True)  # Calculado en ETL

    # Signos Vitales y Paraclínicos
    presion_sistolica = models.IntegerField(null=True, blank=True)
    presion_diastolica = models.IntegerField(null=True, blank=True)
    frecuencia_cardiaca = models.IntegerField(null=True, blank=True)
    glucosa = models.FloatField(null=True, blank=True)
    colesterol = models.FloatField(null=True, blank=True)
    saturacion_oxigeno = models.FloatField(null=True, blank=True)
    temperatura = models.FloatField(null=True, blank=True)

    # Antecedentes y Estilo de Vida
    antecedentes_familiares = models.BooleanField(default=False)
    fumador = models.BooleanField(default=False)
    consumo_alcohol = models.BooleanField(default=False)
    actividad_fisica = models.CharField(max_length=50, null=True, blank=True)

    # Diagnóstico y Gestión de Riesgo
    diagnostico_preliminar = models.CharField(max_length=250, null=True, blank=True)
    riesgo_enfermedad = models.CharField(max_length=50, null=True, blank=True)  # Calculado/Validado en ETL
    fecha_consulta = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} - ID: {self.id_paciente}"


class HistorialETL(models.Model):
    objects = models.Manager()

    # Control de auditoría para el proceso de carga masiva
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    registros_procesados = models.IntegerField()
    errores_encontrados = models.IntegerField(default=0)
    tiempo_ejecucion = models.FloatField()  # En segundos
    estado = models.CharField(max_length=50)  # 'Exitoso' o 'Fallido'

    def __str__(self):
        return f"Ejecución ETL {self.id} - {self.estado} ({self.fecha})"

class Perfil(models.Model):
    # Opciones de roles obligatorios de la guía
    ROLE_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('MEDICO', 'Médico'),
        ('ANALISTA', 'Analista de Datos'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    rol = models.CharField(max_length=15, choices=ROLE_CHOICES, default='MEDICO')

    def __str__(self):
        return f"{self.user.email} - {self.get_rol_display()}"

class DashboardKPIs(models.Model):
    fecha_calculo = models.DateTimeField(auto_now_add=True)

    # 1. KPIs de Control Obligatorios
    total_registros = models.IntegerField(default=0)
    pacientes_criticos = models.IntegerField(default=0)
    pacientes_hipertensos = models.IntegerField(default=0)
    pacientes_diabeticos = models.IntegerField(default=0)
    pacientes_fumadores = models.IntegerField(default=0)
    pacientes_obesos = models.IntegerField(default=0)
    pacientes_antecedentes = models.IntegerField(default=0)
    pacientes_alcohol = models.IntegerField(default=0)
    pacientes_saturacion_baja = models.IntegerField(default=0)
    riesgo_promedio = models.FloatField(default=0.0)

    # 2. Alertas Clínicas Individuales
    alertas_sistolica = models.IntegerField(default=0)
    alertas_glucosa = models.IntegerField(default=0)
    alertas_saturacion = models.IntegerField(default=0)

    # 3. Estadística Descriptiva
    edad_media = models.FloatField(default=0.0)
    edad_mediana = models.FloatField(default=0.0)
    edad_moda = models.FloatField(default=0.0)
    edad_desviacion = models.FloatField(default=0.0)
    glucosa_media = models.FloatField(default=0.0)
    glucosa_desviacion = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-fecha_calculo']

class MetricasModeloML(models.Model):
    fecha_entrenamiento = models.DateTimeField(auto_now_add=True)
    
    # Métricas Obligatorias de la Guía
    accuracy = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()
    
    # Matriz de Confusión 2x2 serializada como JSON (VP, FP, FN, VN)
    matriz_confusion = models.JSONField() 
    
    # Campo binario o ruta para guardar el archivo del modelo entrenado (.pkl) si es necesario
    modelo_activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_entrenamiento']