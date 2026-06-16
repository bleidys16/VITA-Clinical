from django.core.management.base import BaseCommand
from apps.etl.models import Paciente
from apps.etl.clasificador_sexo import clasificar_sexo_por_nombre


class Command(BaseCommand):
    help = 'Corrige el campo sexo de los pacientes basado en el clasificador por nombre'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\n=== CORRIGIENDO SEXO POR NOMBRE ===\n'))

        corregidos = 0
        total = Paciente.objects.count()

        for paciente in Paciente.objects.iterator():
            sexo_correcto = clasificar_sexo_por_nombre(paciente.nombres)
            if sexo_correcto and paciente.sexo != sexo_correcto:
                paciente.sexo = sexo_correcto
                paciente.save(update_fields=['sexo'])
                corregidos += 1
                self.stdout.write(f"  {paciente.id_paciente}: {paciente.nombres} -> {sexo_correcto}")

        self.stdout.write(self.style.SUCCESS(
            f'\nTotal procesados: {total} | Corregidos: {corregidos}'
        ))
