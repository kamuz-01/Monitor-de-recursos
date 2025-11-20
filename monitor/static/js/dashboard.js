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
   Cria gráfico com Pan (Maps), Zoom (Ctrl) e 30 Ticks
------------------------------------------------ */
function renderChartWithEMA(canvasId, label, labels, values, colorLine, colorEMA) {
    const canvas = document.getElementById(canvasId);

    if (canvas.chartInstance) {
        canvas.chartInstance.destroy();
    }

    const emaValues = calculateEMA(values);

    // Configuração do gráfico
    const chart = canvas.chartInstance = new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: `${label} (Real)`,
                    data: values,
                    borderColor: colorLine,
                    borderWidth: 1,
                    pointRadius: 2,
                    tension: 0.2,
                    order: 2
                },
                {
    		    label: `${label} (EMA)`,
    		    data: emaValues,
    		    borderColor: colorEMA,
    		    borderWidth: 2,
    		    pointRadius: 0,
    		    borderDash: [5, 5],
    		    tension: 0.35,
    		    order: 1,
    		    fill: {
        		target: 'origin',
        		above: colorEMA + "40"  // 40 = 25% de opacidade em hex
    		   }
		}
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false,
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: v => `${v}%` }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 30 // <--- AQUI MUDOU DE 10 PARA 30
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                },
                zoom: {
                    // Limites
                    limits: {
                        x: {
                            min: 0,
                            max: labels.length - 1,
                            minRange: 5 
                        },
                        y: {
                            min: 0,
                            max: 100
                        }
                    },
                    // Pan (Arrastar estilo Maps)
                    pan: {
                        enabled: true,   
                        mode: 'x',       
                        threshold: 10,   
                    },
                    // Zoom (Apenas com Ctrl pressionado)
                    zoom: {
                        wheel: {
                            enabled: true,
                            modifierKey: 'ctrl', 
                        },
                        pinch: {
                            enabled: true 
                        },
                        mode: 'x',
                    }
                }
            }
        }
    });

    /* Cursores visuais */
    canvas.style.cursor = "grab";
    
    canvas.addEventListener('mousedown', () => canvas.style.cursor = "grabbing");
    canvas.addEventListener('mouseup', () => canvas.style.cursor = "grab");
    canvas.addEventListener('mouseout', () => canvas.style.cursor = "grab");
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
    const hostSelect = document.getElementById("hostSelect");
    const rangeSelect = document.getElementById("rangeSelect");
    
    const hostId = hostSelect.value;
    const range = rangeSelect.value;

    if (!hostId) return;

    console.log("Atualizando dashboard:", hostId, range);

    // CPU
    const cpu = await loadMetrics(hostId, range, "cpu_percent");
    if (cpu && cpu.length > 0) {
        const labels = cpu.map(c => new Date(c.timestamp).toLocaleTimeString("pt-BR"));
        const values = cpu.map(c => Number(c.value));

        renderChartWithEMA("cpuChart", "CPU (%)", labels, values, "#F44336", "#FF9800");
        updateStats("cpuStats", values);
    } else {
        const ctx = document.getElementById("cpuChart");
        if(ctx.chartInstance) ctx.chartInstance.destroy();
        document.getElementById("cpuStats").textContent = "Aguardando dados...";
    }

    // Memória
    const mem = await loadMetrics(hostId, range, "memory_percent");
    if (mem && mem.length > 0) {
        const labels = mem.map(m => new Date(m.timestamp).toLocaleTimeString("pt-BR"));
        const values = mem.map(m => Number(m.value));

        renderChartWithEMA("memoryChart", "Memória RAM (%)", labels, values, "#2196F3", "#00BCD4");
        updateStats("memoryStats", values);
    } else {
        const ctx = document.getElementById("memoryChart");
        if(ctx.chartInstance) ctx.chartInstance.destroy();
        document.getElementById("memoryStats").textContent = "Aguardando dados...";
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
    setTimeout(loadDashboard, 500);

    document.getElementById("hostSelect").addEventListener("change", loadDashboard);
    document.getElementById("rangeSelect").addEventListener("change", loadDashboard);

    setInterval(loadDashboard, 60000);
});
