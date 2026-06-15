import pandas as pd
from apps.etl.models import Paciente, DashboardKPIs
from apps.etl.services import calcular_analitica_dataset

# Delete old KPIs
DashboardKPIs.objects.all().delete()
print("Old KPIs deleted")

# Recalculate from existing patients
qs = Paciente.objects.all().values()
df = pd.DataFrame(list(qs))
print(f"Loaded {len(df)} patients from DB")

if not df.empty:
    kpi = calcular_analitica_dataset(df)
    if kpi:
        print(f"KPIs created: pk={kpi.pk}")
        print(f"  total: {kpi.total_registros}")
        print(f"  criticos: {kpi.pacientes_criticos}")
        print(f"  hipertensos: {kpi.pacientes_hipertensos}")
        print(f"  diabeticos: {kpi.pacientes_diabeticos}")
        print(f"  fumadores: {kpi.pacientes_fumadores}")
        print(f"  obesos: {kpi.pacientes_obesos}")
        print(f"  antecedentes: {kpi.pacientes_antecedentes}")
        print(f"  alcohol: {kpi.pacientes_alcohol}")
        print(f"  saturacion_baja: {kpi.pacientes_saturacion_baja}")
        print(f"  alertas_sistolica: {kpi.alertas_sistolica}")
        print(f"  alertas_glucosa: {kpi.alertas_glucosa}")
        print(f"  alertas_saturacion: {kpi.alertas_saturacion}")
    else:
        print("Failed to create KPIs")
else:
    print("No patients found")
