document.addEventListener("DOMContentLoaded", function () {
    const token = localStorage.getItem('token_acceso');
    if (!token) return;

    cargarDatosDashboard(token);
    cargarMetricasMachineLearning(token);

    document.getElementById('btn-refresh-dashboard')?.addEventListener('click', function() {
        cargarDatosDashboard(token);
        cargarMetricasMachineLearning(token);
    });
});

async function cargarDatosDashboard(token) {
    try {
        const response = await fetch('/api/etl/analytics/dashboard/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        const data = await response.json();

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

            inicializarGraficaBarras(data.graficas);
            inicializarGraficaTorta(data.graficas);
            inicializarGraficaLineas(data.graficas);
        }
    } catch (error) {
        console.error("Error al renderizar las analíticas de ApexCharts:", error);
    }
}

function inicializarGraficaBarras(graficas) {
    const segmentos = graficas.barras_segmentacion || [];
    const patologiasFijas = ['Hipertensión', 'Diabetes Tipo 2', 'Obesidad'];

    const series = patologiasFijas.map(nombre => ({
        name: nombre,
        data: segmentos.map(seg => {
            const encontrado = (seg.diagnosticos || []).find(d => d.nombre === nombre);
            return encontrado ? encontrado.cantidad : 0;
        })
    }));

    const otrasData = segmentos.map(seg => {
        const fijas = patologiasFijas.map(n => {
            const encontrado = (seg.diagnosticos || []).find(d => d.nombre === n);
            return encontrado ? encontrado.cantidad : 0;
        });
        const sumaFijas = fijas.reduce((a, b) => a + b, 0);
        const totalSeg = seg.total || 0;
        return Math.max(0, totalSeg - sumaFijas);
    });
    series.push({ name: 'Otras condiciones', data: otrasData });

    const options = {
        chart: { type: 'bar', height: 320, stacked: true, toolbar: { show: false } },
        plotOptions: { bar: { borderRadius: 4, horizontal: false } },
        colors: ['#000229', '#6A4DD4', '#A4A7E3', '#CEB5D4'],
        series: series,
        xaxis: {
            categories: graficas.labels_barras || ['<30', '30-49', '50-69', '70+'],
            title: { text: 'Rangos de Edad' }
        },
        yaxis: { title: { text: 'Número de Pacientes' } },
        grid: { show: false },
        legend: { position: 'right', fontSize: '12px', offsetY: 40 },
        dataLabels: { enabled: false }
    };
    if (document.querySelector("#chart-barras")) {
        const chart = new ApexCharts(document.querySelector("#chart-barras"), options);
        chart.render();
    }
}

function inicializarGraficaTorta(graficas) {
    const torta = graficas.riesgo_torta || { labels: [], series: [] };
    const options = {
        chart: { type: 'donut', height: 300, toolbar: { show: false } },
        labels: torta.labels.length ? torta.labels : ['Sin datos'],
        series: torta.series.length ? torta.series : [1],
        colors: ['#48BB78', '#ECC94B', '#CEB5D4', '#E53E3E'],
        legend: { position: 'bottom', fontSize: '12px', horizontalAlign: 'center' },
        dataLabels: { enabled: true, style: { fontSize: '14px', fontWeight: 'bold' } },
        plotOptions: { pie: { donut: { size: '60%' }, expandOnClick: true } },
        tooltip: { y: { formatter: (val) => `${val} pacientes` } },
        responsive: [{ breakpoint: 480, options: { legend: { position: 'bottom' } } }]
    };
    if (document.querySelector("#chart-radar")) {
        const chart = new ApexCharts(document.querySelector("#chart-radar"), options);
        chart.render();
    }
}

function inicializarGraficaLineas(graficas) {
    const tendencias = graficas.tendencias || [];

    const bloques = [
        { label: '15-25', min: 15, max: 25 },
        { label: '26-35', min: 26, max: 35 },
        { label: '36-45', min: 36, max: 45 },
        { label: '46-55', min: 46, max: 55 },
        { label: '56-65', min: 56, max: 65 },
        { label: '66+', min: 66, max: 200 },
    ];

    const promediosPorBloque = bloques.map(bloque => {
        const filtradas = tendencias.filter(t => t.edad >= bloque.min && t.edad <= bloque.max);
        const sistolicas = filtradas.filter(t => t.presion_sistolica).map(t => t.presion_sistolica);
        const glucosas = filtradas.filter(t => t.glucosa).map(t => t.glucosa);
        return {
            label: bloque.label,
            sistolica: sistolicas.length ? Math.round(sistolicas.reduce((a, b) => a + b, 0) / sistolicas.length) : 0,
            glucosa: glucosas.length ? Math.round((glucosas.reduce((a, b) => a + b, 0) / glucosas.length) * 10) / 10 : 0,
        };
    });

    const labels = promediosPorBloque.map(b => b.label);
    const dataSistolica = promediosPorBloque.map(b => b.sistolica);
    const dataGlucosa = promediosPorBloque.map(b => b.glucosa);

    const options = {
        chart: { type: 'line', height: 320, zoom: { enabled: false }, toolbar: { show: false } },
        stroke: { curve: 'smooth', width: 3 },
        markers: { size: 0 },
        series: [
            { name: 'TA Sistólica Promedio (mmHg)', data: dataSistolica },
            { name: 'Glucosa Promedio (mg/dL)', data: dataGlucosa }
        ],
        xaxis: {
            categories: labels,
            title: { text: 'Grupo Etario' }
        },
        yaxis: [
            { title: { text: 'TA Sistólica (mmHg)' }, min: 80, max: 200 },
            { opposite: true, title: { text: 'Glucosa (mg/dL)' }, min: 50, max: 300 }
        ],
        colors: ['#E53E3E', '#000229'],
        grid: { show: false },
        legend: { position: 'top', fontSize: '12px' }
    };
    if (document.querySelector("#chart-lineas")) {
        const chart = new ApexCharts(document.querySelector("#chart-lineas"), options);
        chart.render();
    }
}

async function cargarMetricasMachineLearning(token) {
    try {
        const response = await fetch('/api/ml/model/metrics/', {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();

        if (response.ok && data.modelo_entrenado) {
            document.getElementById('ml-accuracy').innerText = `${data.accuracy}%`;
            document.getElementById('ml-precision').innerText = `${data.precision}%`;
            document.getElementById('ml-recall').innerText = `${data.recall}%`;
            document.getElementById('ml-f1').innerText = `${data.f1_score}%`;

            inicializarHeatmap(data.heatmap);
        } else {
            document.querySelectorAll('#ml-accuracy, #ml-precision, #ml-recall, #ml-f1').forEach(el => el.innerText = '—');
            const hm = document.getElementById('chart-heatmap');
            if (hm) hm.innerHTML = `
                <div class="text-center py-4 text-muted">
                    <i class="fa-solid fa-chart-simple fa-2x mb-2" style="color: var(--clia-wisteria);"></i>
                    <p class="mb-0 small">Sin modelo entrenado</p>
                </div>
            `;
        }
    } catch (error) {
        console.error("Error al cargar métricas de ML:", error);
    }
}

function inicializarHeatmap(heatmapData) {
    const options = {
        chart: { type: 'heatmap', height: 280, toolbar: { show: false } },
        dataLabels: { enabled: true, style: { colors: ['#fff'] } },
        colors: ['#000229'],
        series: heatmapData,
        xaxis: { type: 'category' }
    };
    const chart = new ApexCharts(document.querySelector("#chart-heatmap"), options);
    chart.render();
}
