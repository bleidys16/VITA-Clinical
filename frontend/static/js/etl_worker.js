let pollingInterval = null;

document.addEventListener("DOMContentLoaded", function () {
    cargarHistorialLogs();

    const btnRunEtl = document.getElementById('btn-run-etl');
    if (btnRunEtl) btnRunEtl.addEventListener('click', ejecutarPipelineETL);

    const btnReset = document.getElementById('btn-reset-data');
    if (btnReset) btnReset.addEventListener('click', resetearDataset);
});

async function cargarHistorialLogs() {
    const tableBody = document.getElementById('etl-logs-table-body');
    if (!tableBody) return;

    try {
        const response = await fetch('/api/etl/logs/');
        if (!response.ok) { mostrarTablaVacia(tableBody); return; }

        const logs = await response.json();
        tableBody.innerHTML = '';

        if (!logs || logs.length === 0) { mostrarTablaVacia(tableBody); return; }

        logs.forEach(log => {
            const fechaFormateada = new Date(log.fecha_ejecucion).toLocaleString('es-CO');
            const estadoBadge = log.estado === 'Exitoso' || log.estado === 'Success'
                ? '<span class="badge" style="background-color: var(--clia-wisteria); color: var(--clia-jacarta); font-weight: 600;">Completado</span>'
                : '<span class="badge bg-danger text-white">Fallido</span>';

            tableBody.innerHTML += `
                <tr>
                    <td class="fw-bold" style="color: var(--clia-jacarta);">${fechaFormateada}</td>
                    <td><i class="fa-solid fa-circle-check text-success me-1"></i> ${log.registros_procesados || 0}</td>
                    <td class="text-muted">${log.tiempo_ejecucion ? log.tiempo_ejecucion.toFixed(2) + 's' : '—'}</td>
                    <td><small class="text-uppercase font-monospace text-secondary">${log.usuario_responsable || 'Sistema'}</small></td>
                    <td>${estadoBadge}</td>
                </tr>
            `;
        });

    } catch (error) {
        console.error("Error al renderizar la tabla de auditoría:", error);
        mostrarTablaVacia(tableBody);
    }
}

function mostrarTablaVacia(contenedor) {
    contenedor.innerHTML = `
        <tr>
            <td colspan="5" class="text-center text-muted py-4" style="font-family: 'Satoshi', sans-serif;">
                <i class="fa-solid fa-folder-open me-2" style="color: var(--clia-wisteria);"></i> 
                No se registran ejecuciones previas. El sistema está listo para recibir el primer dataset.
            </td>
        </tr>`;
}

async function ejecutarPipelineETL() {
    const btn = document.getElementById('btn-run-etl');
    const fileInput = document.getElementById('fileInput');
    const loading = document.getElementById('etl-loading');

    if (!btn || !fileInput || fileInput.files.length === 0) {
        alert("Por favor, selecciona un archivo antes de iniciar el proceso.");
        return;
    }

    btn.disabled = true;
    loading.classList.remove('d-none');

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const data = await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/etl/run/', true);

            const token = localStorage.getItem('token_acceso');
            if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

            xhr.onload = function () {
                try {
                    const d = JSON.parse(xhr.responseText);
                    if (xhr.status >= 200 && xhr.status < 300) resolve(d);
                    else reject(new Error(d.message || 'Error en el servidor'));
                } catch (e) {
                    reject(new Error('Respuesta inválida del servidor'));
                }
            };

            xhr.onerror = function () {
                reject(new Error('Error de conexión con el servidor'));
            };

            xhr.send(formData);
        });

        if (data.status === 'accepted') {
            await esperarPipelineCompletado();
        }

        fileInput.value = '';
        document.getElementById('file-info-container').classList.add('d-none');
        await cargarHistorialLogs();

    } catch (error) {
        console.error("Error en el pipeline:", error);
        alert("Error: " + error.message);
    } finally {
        loading.classList.add('d-none');
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-play me-2"></i> Iniciar Pipeline ETL`;
    }
}

function esperarPipelineCompletado() {
    return new Promise((resolve) => {
        if (pollingInterval) clearInterval(pollingInterval);

        const consoleEl = document.getElementById('etl-console');
        if (consoleEl) consoleEl.innerHTML = '';

        pollingInterval = setInterval(async () => {
            try {
                const token = localStorage.getItem('token_acceso');
                const response = await fetch('/api/etl/status/', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await response.json();

                if (consoleEl && data.logs) {
                    consoleEl.innerHTML = data.logs.map(l =>
                        `<div><span style="color:#89b4fa;">[${l.fase}]</span> ${l.mensaje} <span class="text-muted">${l.detalle}</span></div>`
                    ).join('');
                    consoleEl.scrollTop = consoleEl.scrollHeight;
                }

                if (response.ok && !data.activo) {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                    resolve();
                }
            } catch (err) {
                console.error("Error polling ETL status:", err);
            }
        }, 1500);
    });
}

async function resetearDataset() {
    const btnReset = document.getElementById('btn-reset-data');
    if (!btnReset) return;

    const confirmacion = confirm("¿Estás seguro de que deseas restablecer el dataset? Se eliminarán todos los pacientes y el historial de cargas.");
    if (!confirmacion) return;

    btnReset.disabled = true;
    btnReset.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin me-2"></i> Restableciendo...`;

    const token = localStorage.getItem('token_acceso');
    if (!token) { alert('Debe iniciar sesión'); return; }

    try {
        const response = await fetch('/api/etl/reset/', {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const resultado = await response.json();

        if (response.ok && resultado.status === 'success') {
            alert(resultado.message);
            await cargarHistorialLogs();
            window.location.href = '/dashboard/';
        } else {
            throw new Error(resultado.message || "Error al restablecer datos.");
        }
    } catch (error) {
        console.error("Error al restablecer:", error);
        alert("Error: " + error.message);
    } finally {
        btnReset.disabled = false;
        btnReset.innerHTML = `<i class="fa-solid fa-rotate-left me-2"></i> Restablecer Dataset`;
    }
}