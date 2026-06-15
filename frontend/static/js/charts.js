document.addEventListener("DOMContentLoaded", function() {
    cargarDatosDashboard();
});

async function cargarDatosDashboard() {
    try {
        const response = await fetch('/api/dashboard/kpis/');
        if (!response.ok) throw new Error("Error obteniendo indicadores del servidor.");
        
        const data = await response.json();
        const kpi = data.kpis_consolidados || {};

        document.getElementById('kpi-criticos').innerText = kpi.resumen_general?.pacientes_estado_critico || 0;
        document.getElementById('kpi-hipertensos').innerText = kpi.alertas_epidemiologicas_ips?.total_hipertensos || 0;
        document.getElementById('kpi-diabeticos').innerText = kpi.alertas_epidemiologicas_ips?.total_diabeticos || 0;
        document.getElementById('kpi-fumadores').innerText = kpi.total_fumadores || 0;

        const riesgos = kpi.distribucion_riesgos_porcentaje || {};
        const ordenRiesgo = ['Crítico', 'Alto', 'Medio', 'Bajo'];
        const valoresRiesgo = ordenRiesgo.map(r => riesgos[r]?.cantidad || 0);

        const ctxTorta = document.getElementById('chartRiesgoTorta').getContext('2d');
        new Chart(ctxTorta, {
            type: 'pie',
            data: {
                labels: ordenRiesgo,
                datasets: [{
                    data: valoresRiesgo,
                    backgroundColor: ['#3F2A52', '#75619D', '#BEAEDB', '#CED8F2'],
                    borderWidth: 2,
                    borderColor: '#FFFFFF'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { font: { family: 'Satoshi', size: 13 } } }
                }
            }
        });

        const labelsDiagnosticos = Object.keys(kpi.distribucion_diagnostico || {});
        const valoresDiagnosticos = Object.values(kpi.distribucion_diagnostico || {});

        const ctxBarras = document.getElementById('chartDiagnosticosBarras').getContext('2d');
        new Chart(ctxBarras, {
            type: 'bar',
            data: {
                labels: labelsDiagnosticos.length ? labelsDiagnosticos : ['Sin Registros'],
                datasets: [{
                    label: 'Número de Casos',
                    data: valoresDiagnosticos.length ? valoresDiagnosticos : [0],
                    backgroundColor: '#75619D',
                    borderRadius: 6,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { font: { family: 'Satoshi' } } },
                    y: { grid: { color: 'rgba(168, 138, 237, 0.1)' }, ticks: { font: { family: 'Satoshi' } } }
                }
            }
        });

    } catch (error) {
        console.error("Error crítico inicializando componentes visuales:", error);
    }
}
