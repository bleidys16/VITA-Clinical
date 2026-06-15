let chartDonut = null;
let chartBarras = null;

document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem('token_acceso');
    if (!token) return;

    cargarDatosDashboard(token);

    document.getElementById('btn-refresh-dashboard')?.addEventListener('click', function() {
        cargarDatosDashboard(token);
    });
});

async function cargarDatosDashboard(token) {
    try {
        const response = await fetch('/api/etl/analytics/dashboard/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const data = await response.json();

        if (response.ok && data.sistema_vacio) {
            mostrarDashboardVacio();
            return;
        }

        if (response.ok && !data.sistema_vacio) {
            document.getElementById('kpi-total').innerText = data.kpis.total_registros;
            document.getElementById('kpi-criticos').innerText = data.kpis.pacientes_criticos;
            document.getElementById('kpi-edad-promedio').innerText = data.kpis.edad_promedio;
            document.getElementById('kpi-riesgo').innerText = `${data.kpis.riesgo_promedio}%`;

            const ic = data.indicadores_clinicos || {};
            document.getElementById('ind-glucosa').innerText = ic.glucosa_promedio ? `${ic.glucosa_promedio} mg/dL` : '—';
            document.getElementById('ind-imc').innerText = ic.imc_promedio ? `${ic.imc_promedio}` : '—';
            document.getElementById('ind-criticos').innerText = ic.porcentaje_criticos ? `${ic.porcentaje_criticos}%` : '—';
            document.getElementById('ind-alto').innerText = ic.porcentaje_riesgo_alto ? `${ic.porcentaje_riesgo_alto}%` : '—';

            inicializarGraficaDonut(data.graficas);
            inicializarGraficaBarras(data.graficas);
            renderizarUltimasConsultas(data.ultimas_consultas);
        }
    } catch (error) {
        console.error("Error al renderizar el dashboard:", error);
    }
}

function mostrarDashboardVacio() {
    document.getElementById('kpi-total').innerText = '0';
    document.getElementById('kpi-criticos').innerText = '0';
    document.getElementById('kpi-edad-promedio').innerText = '0';
    document.getElementById('kpi-riesgo').innerText = '0%';
    document.getElementById('ultimas-consultas').innerHTML = `
        <div class="text-center text-muted py-4">
            <i class="fa-solid fa-cloud-arrow-up fa-2x mb-2 d-block" style="color:var(--vita-wisteria);"></i>
            <small>No hay datos en el dashboard.<br>Cargá un dataset desde <a href="/cargar-dataset/">Cargar Dataset</a>.</small>
        </div>`;
    if (chartDonut) { chartDonut.destroy(); chartDonut = null; }
    if (chartBarras) { chartBarras.destroy(); chartBarras = null; }
}

function inicializarGraficaDonut(graficas) {
    const torta = graficas.riesgo_torta || { labels: [], series: [] };
    const total = torta.series.reduce((a, b) => a + b, 0);

    const options = {
        chart: { type: 'donut', height: 280, toolbar: { show: false } },
        labels: torta.labels.length ? torta.labels : ['Sin datos'],
        series: torta.series.length ? torta.series : [1],
        colors: ['#6A4DD4', '#CEB5D4', '#000229', '#6E3377'],
        legend: { position: 'bottom', fontSize: '12px', horizontalAlign: 'center' },
        dataLabels: {
            enabled: true,
            style: { fontSize: '13px', fontWeight: 'bold' },
            formatter: function (val) { return val.toFixed(1) + '%'; }
        },
        plotOptions: {
            pie: {
                donut: {
                    size: '60%',
                    labels: {
                        show: true,
                        total: {
                            show: true,
                            label: 'Total',
                            formatter: function () { return total; }
                        }
                    }
                },
                expandOnClick: true
            }
        },
        tooltip: { y: { formatter: (val) => `${val} pacientes` } },
        responsive: [{ breakpoint: 480, options: { legend: { position: 'bottom' } } }]
    };
    if (document.querySelector("#chart-donut")) {
        if (chartDonut) chartDonut.destroy();
        chartDonut = new ApexCharts(document.querySelector("#chart-donut"), options);
        chartDonut.render();
    }
}

function inicializarGraficaBarras(graficas) {
    const segmentos = graficas.barras_segmentacion || [];
    const categorias = graficas.labels_barras || ['<30', '30-49', '50-69', '70+'];
    const datos = segmentos.map(s => s.total || 0);

    const options = {
        chart: { type: 'bar', height: 300, toolbar: { show: false } },
        plotOptions: { bar: { borderRadius: 4, horizontal: false, distributed: true } },
        colors: ['#6A4DD4', '#CEB5D4', '#000229', '#6E3377'],
        series: [{ name: 'Pacientes', data: datos }],
        xaxis: {
            categories: categorias,
            title: { text: 'Rango de Edad' }
        },
        yaxis: { title: { text: 'Número de Pacientes' } },
        grid: { show: false },
        dataLabels: { enabled: true, style: { colors: ['#fff'], fontSize: '14px', fontWeight: 'bold' } }
    };
    if (document.querySelector("#chart-barras")) {
        if (chartBarras) chartBarras.destroy();
        chartBarras = new ApexCharts(document.querySelector("#chart-barras"), options);
        chartBarras.render();
    }
}

function renderizarUltimasConsultas(pacientes) {
    const container = document.getElementById('ultimas-consultas');
    if (!pacientes || !pacientes.length) {
        container.innerHTML = '<div class="text-center text-muted py-4"><small>Sin consultas recientes</small></div>';
        return;
    }

    const riesgoColors = {
        'Bajo': { bg: '#48BB78', text: '#fff' },
        'Medio': { bg: '#ECC94B', text: '#333' },
        'Alto': { bg: '#f97316', text: '#fff' },
        'Crítico': { bg: '#dc2626', text: '#fff' },
    };

    const items = pacientes.map(p => {
        const rc = riesgoColors[p.riesgo] || { bg: '#6B7280', text: '#fff' };
        const fecha = p.fecha_consulta ? new Date(p.fecha_consulta).toLocaleDateString('es-CO') : '';
        return `
            <div class="d-flex align-items-center py-2 border-bottom border-light">
                <div class="d-flex align-items-center justify-content-center rounded-circle me-3"
                     style="width:38px;height:38px;background:#eef2ff;color:#4F46E5;flex-shrink:0;">
                    <i class="fa-solid ${p.sexo_icon}"></i>
                </div>
                <div class="flex-grow-1 min-width-0">
                    <div class="fw-semibold small text-truncate">${p.nombres} ${p.apellidos}</div>
                    <div class="text-muted" style="font-size:0.75rem;">
                        ${p.edad} años · ${p.diagnostico.length > 35 ? p.diagnostico.substring(0,35)+'…' : p.diagnostico}
                    </div>
                </div>
                <div class="text-end ms-2 flex-shrink-0">
                    <span class="badge rounded-pill" style="background:${rc.bg};color:${rc.text};font-size:0.7rem;">
                        ${p.riesgo}
                    </span>
                    ${fecha ? `<div class="text-muted" style="font-size:0.65rem;">${fecha}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');

    container.innerHTML = items;
}
