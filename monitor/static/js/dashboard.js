let cpuChart = null;
let memoryChart = null;

/* ---------------------------------------------
   Carrega lista de hosts
------------------------------------------------ */
async function loadHosts() {
    try {
        const res = await fetch("/api/hosts/");
        const data = await res.json();

        const sel = document.getElementById("hostSelect");
        sel.innerHTML = "";

        data.forEach(h => {
            sel.insertAdjacentHTML(
                "beforeend",
                `<option value="${h.id}">${h.hostname}</option>`
            );
        });

    } catch (error) {
        console.error("Erro ao carregar hosts:", error);
    }
}

/* ---------------------------------------------
   EMA – Exponential Moving Average
------------------------------------------------ */
function calculateEMA(values, smoothing = 0.3) {
    if (!values || values.length === 0) return [];

    let ema = [values[0]];

    for (let i = 1; i < values.length; i++) {
        ema.push(values[i] * smoothing + ema[i - 1] * (1 - smoothing));
    }

    return ema;
}

/* ---------------------------------------------
   Carrega métricas
------------------------------------------------ */
async function loadMetrics(hostId, range, metricType) {
    try {
        let url = `/api/metrics/report/?host=${hostId}&metric_type=${metricType}&range=${range}`;
        console.log("Buscando:", url);

        const res = await fetch(url);
        if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);

        const json = await res.json();

        if (json.items) return json.items;
        if (json.report) return json.report;
        if (json[metricType]) return json[metricType];

        console.warn("Formato inesperado da API:", json);
        return [];

    } catch (error) {
        console.error("Erro ao carregar métricas:", error);
        return [];
    }
}

/* ---------------------------------------------
   Cria gráfico com EMA, Zoom com limites e Pan com inércia
------------------------------------------------ */
function renderChartWithEMA(canvasId, label, labels, values, colorLine, colorEMA) {

    const MIN_RANGE = 30;
    const MAX_RANGE = labels.length;

    const canvas = document.getElementById(canvasId);

    if (canvas.chartInstance) {
        canvas.chartInstance.destroy();
    }

    const emaValues = calculateEMA(values);

    const chart = canvas.chartInstance = new Chart(canvas, {
        type: "line",
        data: {
            labels,
            datasets: [
                {
                    label: `${label} (Real)`,
                    data: values,
                    borderColor: colorLine,
                    borderWidth: 1,
                    pointRadius: 2,
                    tension: 0.2
                },
                {
                    label: `${label} (EMA)`,
                    data: emaValues,
                    borderColor: colorEMA,
                    borderWidth: 2,
                    pointRadius: 0,
                    borderDash: [5, 5],
                    tension: 0.35
                }
            ]
        },

        options: {
            responsive: true,
            interaction: { mode: "nearest", intersect: false },

            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: v => `${v}%` }
                }
            },

            plugins: {
                zoom: {

                    limits: {
                        x: { minRange: MIN_RANGE }
                    },

                    zoom: {
                        wheel: {
                            enabled: true,
                            modifierKey: "ctrl"
                        },
                        mode: "x",

                        /* --------- CORRIGIDO: sem event --------- */
                        onZoom({ chart, delta, center }) {
    const scale = chart.scales.x;

    // pixel onde o usuário está apontando
    const mousePixel = center.x;
    const mouseValue = scale.getValueForPixel(mousePixel);

    const zoomFactor = delta.y < 0 ? 0.9 : 1.1;

    let newMin = mouseValue - (mouseValue - scale.min) * zoomFactor;
    let newMax = mouseValue + (scale.max - mouseValue) * zoomFactor;

    const newRange = newMax - newMin;

    if (newRange < MIN_RANGE) {
        const mid = mouseValue;
        newMin = mid - MIN_RANGE / 2;
        newMax = mid + MIN_RANGE / 2;
    }

    if (newRange > MAX_RANGE) {
        newMin = 0;
        newMax = MAX_RANGE;
    }

    scale.options.min = newMin;
    scale.options.max = newMax;
    chart.update("none");
}
                    },

                    pan: {
                        enabled: true,
                        mode: "x",

                        onPanStart({ chart }) {
                            chart.$velocity = 0;
                            chart.$lastTime = performance.now();
                            chart.canvas.style.cursor = "grabbing";
                        },

                        onPan({ chart, delta }) {
                            const now = performance.now();
                            const dt = now - chart.$lastTime;

                            chart.$velocity = delta.x / dt;
                            chart.$lastTime = now;

                            const scale = chart.scales.x;

                            const minPixel = scale.getPixelForValue(scale.min) - delta.x;
                            const maxPixel = scale.getPixelForValue(scale.max) - delta.x;

                            scale.options.min = scale.getValueForPixel(minPixel);
                            scale.options.max = scale.getValueForPixel(maxPixel);

                            chart.update("none");
                        },

                        onPanComplete({ chart }) {
                            const friction = 0.95;

                            function animate() {
                                if (Math.abs(chart.$velocity) < 0.01) {
                                    chart.canvas.style.cursor = "grab";
                                    return;
                                }

                                const scale = chart.scales.x;
                                const dx = chart.$velocity * 16;

                                const minPixel = scale.getPixelForValue(scale.min) - dx;
                                const maxPixel = scale.getPixelForValue(scale.max) - dx;

                                scale.options.min = scale.getValueForPixel(minPixel);
                                scale.options.max = scale.getValueForPixel(maxPixel);

                                chart.$velocity *= friction;
                                chart.update("none");

                                requestAnimationFrame(animate);
                            }

                            requestAnimationFrame(animate);
                        }
                    }
                }
            },

            /* Reset ao dar duplo clique */
            onDblClick(event, elements, chart) {
                chart.resetZoom();
            }
        }
    });

    /* ----- cursor grab ------ */
    canvas.style.cursor = "grab";
}


/* ---------------------------------------------
   Atualiza estatísticas
------------------------------------------------ */
function updateStats(elementId, values) {
    if (!values.length) {
        document.getElementById(elementId).textContent = "Sem dados";
        return;
    }

    const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);
    const max = Math.max(...values).toFixed(1);
    const min = Math.min(...values).toFixed(1);

    document.getElementById(elementId).textContent =
        `Média: ${avg}% | Máx: ${max}% | Mín: ${min}%`;
}

/* ---------------------------------------------
   Carrega todo o dashboard
------------------------------------------------ */
async function loadDashboard() {
    const hostId = document.getElementById("hostSelect").value;
    const range = document.getElementById("rangeSelect").value;

    console.log("Dashboard:", hostId, range);

    const cpu = await loadMetrics(hostId, range, "cpu_percent");
    if (cpu.length > 0) {
        const labels = cpu.map(c => new Date(c.timestamp).toLocaleTimeString("pt-BR"));
        const values = cpu.map(c => Number(c.value));

        renderChartWithEMA("cpuChart", "CPU (%)", labels, values, "#F44336", "#FF9800");
        updateStats("cpuStats", values);
    }

    const mem = await loadMetrics(hostId, range, "memory_percent");
    if (mem.length > 0) {
        const labels = mem.map(m => new Date(m.timestamp).toLocaleTimeString("pt-BR"));
        const values = mem.map(m => Number(m.value));

        renderChartWithEMA("memoryChart", "Memória RAM (%)", labels, values, "#2196F3", "#00BCD4");
        updateStats("memoryStats", values);
    }
}

/* ---------------------------------------------
   Exportar CSV / JSON
------------------------------------------------ */
async function generateReport() {
    const hostId = document.getElementById("hostSelect").value;
    const range = document.getElementById("rangeSelect").value;
    const format = document.getElementById("formatSelect")?.value || "json";

    try {
        const url = `/api/metrics/report/?host=${hostId}&range=${range}`;
        const res = await fetch(url);
        const data = await res.json();

        if (format === "csv") downloadCSV(data.report, hostId);
        else downloadJSON(data, hostId);

    } catch (err) {
        console.error(err);
        alert("Erro ao gerar relatório!");
    }
}

function downloadCSV(report, hostId) {
    if (!report?.length) {
        alert("Nenhum dado para exportar!");
        return;
    }

    const header = ["Hostname", "Tipo", "Valor (%)", "Timestamp"];
    const rows = report.map(m => [
        m.hostname, m.metric_type, m.value, m.timestamp
    ]);

    let csv = header.join(",") + "\n";
    rows.forEach(r => csv += r.join(",") + "\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio_${hostId}.csv`;
    a.click();
}

function downloadJSON(data, hostId) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json"
    });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio_${hostId}.json`;
    a.click();
}

function resetZoom(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (canvas.chartInstance) {
        canvas.chartInstance.resetZoom();
    }
}

/* ---------------------------------------------
   Inicialização
------------------------------------------------ */
document.addEventListener("DOMContentLoaded", async () => {
    await loadHosts();
    await loadDashboard();

    document.getElementById("hostSelect").addEventListener("change", loadDashboard);
    document.getElementById("rangeSelect").addEventListener("change", loadDashboard);

    setInterval(loadDashboard, 60000);
});
