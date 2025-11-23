let cpuChart = null;
let memoryChart = null;
let lastLoadedRange = null;

/* ===== DEBUG: Log para verificar carregamento ===== */
function debugLog(msg) {
    console.log(`[MONITOR ${new Date().toLocaleTimeString()}] ${msg}`);
}

/* ===== CONFIGURAÇÃO: Hosts a Ocultar ===== */
const HIDDEN_HOSTS = ['teste-01', 'teste-02', 'teste-03', 'test', 'demo'];

function shouldHideHost(hostname) {
    return HIDDEN_HOSTS.some(pattern => 
        hostname.toLowerCase().includes(pattern.toLowerCase())
    );
}

/* ===== Carrega lista de hosts ===== */
async function loadHosts() {
    try {
        debugLog("Carregando hosts...");
        const res = await fetch("/api/hosts/");
        const data = await res.json();
        const sel = document.getElementById("hostSelect");
        sel.innerHTML = "";

        // Filtra hosts ocultos
        const visibleHosts = data.filter(h => !shouldHideHost(h.hostname));
        
        debugLog(`Total: ${data.length}, Visíveis: ${visibleHosts.length}`);

        visibleHosts.forEach(h => {
            sel.insertAdjacentHTML(
                "beforeend",
                `<option value="${h.id}">${h.hostname}</option>`
            );
        });
        
        if (visibleHosts.length === 0) {
            document.getElementById("cpuStats").textContent = "Nenhum host disponível";
            document.getElementById("memoryStats").textContent = "Nenhum host disponível";
        } else {
            // Seleciona o primeiro host visível por padrão
            loadDashboard();
        }

    } catch (error) {
        console.error("Erro ao carregar hosts:", error);
        document.getElementById("cpuStats").textContent = "Erro ao carregar hosts";
    }
}

/* ===== EMA – Exponential Moving Average ===== */
function calculateEMA(values, smoothing = 0.3) {
    if (!values || values.length === 0) return [];
    let ema = [values[0]];
    for (let i = 1; i < values.length; i++) {
        ema.push(values[i] * smoothing + ema[i - 1] * (1 - smoothing));
    }
    return ema;
}

/* ===== Formata timestamp com base no intervalo ===== */
function formatTimestamp(isoString, range) {
    try {
        const date = new Date(isoString);
        
        if (range === '1h' || range === '6h') {
            return date.toLocaleTimeString("pt-BR", { 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            });
        } else if (range === '24h') {
            return date.toLocaleString("pt-BR", { 
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit', 
                minute: '2-digit' 
            });
        } else { // 7d
            return date.toLocaleString("pt-BR", { 
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }
    } catch (e) {
        return isoString;
    }
}

/* ===== Carrega métricas com anti-cache agressivo ===== */
async function loadMetrics(hostId, range, metricType) {
    try {
        // Gera token único para anti-cache
        const randomToken = Math.random().toString(36).substring(2, 15);
        const timestamp = Date.now();
        const url = `/api/metrics/report/?host=${hostId}&metric_type=${metricType}&range=${range}&t=${timestamp}&rand=${randomToken}`;
        
        debugLog(`Buscando ${metricType} para range ${range}...`);

        const res = await fetch(url, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        
        if (!res.ok) {
            console.error(`Erro HTTP ${res.status}`);
            return [];
        }
        
        const json = await res.json();
        debugLog(`Response recebido: ${JSON.stringify(json).substring(0, 100)}...`);

        let items = [];
        
        // Tenta diferentes formatos de resposta
        if (json.report && Array.isArray(json.report)) {
            items = json.report;
            debugLog(`✅ Formato 'report' - ${items.length} items`);
        } else if (Array.isArray(json)) {
            items = json;
            debugLog(`✅ Formato array - ${items.length} items`);
        } else if (json.items && Array.isArray(json.items)) {
            items = json.items;
            debugLog(`✅ Formato 'items' - ${items.length} items`);
        } else {
            console.error("Formato desconhecido:", json);
            return [];
        }

        // Filtra apenas o tipo de métrica solicitado
        const filtered = items.filter(m => m.metric_type === metricType);
        debugLog(`Filtradas ${filtered.length} de ${items.length} para ${metricType}`);
        
        return filtered;

    } catch (error) {
        console.error("Erro ao carregar métricas:", error);
        debugLog(`❌ Erro: ${error.message}`);
        return [];
    }
}

/* ===== Renderiza gráfico com suporte a diferentes intervalos ===== */
function renderChartWithEMA(canvasId, label, labels, values, colorLine, colorEMA, range) {
    const canvas = document.getElementById(canvasId);

    // Destroi gráfico anterior
    if (canvas.chartInstance) {
        canvas.chartInstance.destroy();
        canvas.chartInstance = null;
    }

    debugLog(`Renderizando ${label} com ${values.length} pontos`);

    if (values.length === 0) {
        debugLog(`❌ Sem dados para renderizar ${label}`);
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    const emaValues = calculateEMA(values);

    // Limita ticks de acordo com o intervalo
    let maxTicksLimit = 30;
    if (range === '7d') {
        maxTicksLimit = 42;
    } else if (range === '24h') {
        maxTicksLimit = 50;
    } else if (range === '6h') {
        maxTicksLimit = 40;
    } else if (range === '1h') {
        maxTicksLimit = 25;
    }

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
                    pointRadius: range === '1h' ? 3 : 2,
                    tension: 0.2,
                    order: 2,
                    fill: false
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
                        above: colorEMA + "40"
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
                    ticks: { 
                        callback: v => `${v}%`,
                        stepSize: 10
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: maxTicksLimit,
                        autoSkip: true,
                        autoSkipPadding: 20
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        usePointStyle: false,
                        padding: 20,
                        generateLabels(chart) {
                            const labels = Chart.defaults.plugins.legend.labels.generateLabels(chart);
                            labels.forEach(label => {
                                const ds = chart.data.datasets[label.datasetIndex];
                                if (ds.label.includes("(EMA)")) {
                                    label.lineWidth = 2;
                                    label.strokeStyle = ds.borderColor;
                                    label.fillStyle = "transparent";
                                    label.lineDash = [6, 4];
                                    label.pointStyle = false;
                                } else {
                                    label.lineWidth = 2;
                                    label.strokeStyle = ds.borderColor;
                                    label.fillStyle = ds.borderColor;
                                    label.lineDash = [];
                                    label.pointStyle = false;
                                }
                            });
                            return labels;
                        }
                    }
                },
                zoom: {
                    limits: {
                        x: {min: 0, max: labels.length - 1, minRange: 5},
                        y: {min: 0, max: 100}
                    },
                    pan: {
                        enabled: true,
                        mode: 'x',
                        threshold: 10,
                    },
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

    canvas.style.cursor = "grab";
    canvas.addEventListener('mousedown', () => canvas.style.cursor = "grabbing");
    canvas.addEventListener('mouseup', () => canvas.style.cursor = "grab");
    canvas.addEventListener('mouseout', () => canvas.style.cursor = "grab");
    
    debugLog(`✅ Gráfico ${label} renderizado com sucesso`);
}

/* ===== Atualiza estatísticas ===== */
function updateStats(elementId, values) {
    if (!values || values.length === 0) {
        document.getElementById(elementId).textContent = "Sem dados";
        return;
    }

    const avg = (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1);
    const max = Math.max(...values).toFixed(1);
    const min = Math.min(...values).toFixed(1);

    document.getElementById(elementId).textContent =
        `Média: ${avg}% | Máx: ${max}% | Mín: ${min}%`;
}

/* ===== PRINCIPAL: Carrega dashboard ===== */
async function loadDashboard() {
    const hostSelect = document.getElementById("hostSelect");
    const rangeSelect = document.getElementById("rangeSelect");
    
    const hostId = hostSelect.value;
    const range = rangeSelect.value;

    if (!hostId) {
        debugLog("Nenhum host selecionado");
        return;
    }

    debugLog(`========================================`);
    debugLog(`Carregando: Host=${hostId}, Range=${range}`);
    debugLog(`========================================`);

    // Carrega CPU
    const cpu = await loadMetrics(hostId, range, "cpu_percent");
    
    if (cpu && cpu.length > 0) {
        const labels = cpu.map(c => formatTimestamp(c.timestamp, range));
        const values = cpu.map(c => Number(c.value));

        debugLog(`✅ CPU: ${cpu.length} métricas carregadas`);
        renderChartWithEMA("cpuChart", "CPU (%)", labels, values, "#F44336", "#FF9800", range);
        updateStats("cpuStats", values);
    } else {
        debugLog(`❌ CPU: Sem dados`);
        const ctx = document.getElementById("cpuChart");
        if(ctx.chartInstance) ctx.chartInstance.destroy();
        document.getElementById("cpuStats").textContent = "Sem dados para este intervalo";
    }

    // Carrega Memória
    const mem = await loadMetrics(hostId, range, "memory_percent");
    
    if (mem && mem.length > 0) {
        const labels = mem.map(m => formatTimestamp(m.timestamp, range));
        const values = mem.map(m => Number(m.value));

        debugLog(`✅ Memória: ${mem.length} métricas carregadas`);
        renderChartWithEMA("memoryChart", "Memória RAM (%)", labels, values, "#2196F3", "#00BCD4", range);
        updateStats("memoryStats", values);
    } else {
        debugLog(`❌ Memória: Sem dados`);
        const ctx = document.getElementById("memoryChart");
        if(ctx.chartInstance) ctx.chartInstance.destroy();
        document.getElementById("memoryStats").textContent = "Sem dados para este intervalo";
    }

    debugLog(`Dashboard atualizado!`);
}

/* ===== Exportar PDF / XLSX ===== */
async function generateReport() {
    const hostId = document.getElementById("hostSelect").value;
    const range = document.getElementById("rangeSelect").value;
    const format = document.getElementById("formatSelect")?.value || "xlsx";

    try {
        const url = `/report/generate/?host=${hostId}&range=${range}&format=${format}`;
        window.location.href = url;
    } catch (err) {
        console.error(err);
        alert("Erro ao gerar relatório!");
    }
}

function resetZoom(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (canvas.chartInstance) {
        canvas.chartInstance.resetZoom();
    }
}

/* ===== INICIALIZAÇÃO ===== */
document.addEventListener("DOMContentLoaded", async () => {
    debugLog(`Iniciando dashboard...`);
    
    await loadHosts();
    debugLog(`Hosts carregados`);
    
    // Aguarda um pouco
    setTimeout(() => {
        loadDashboard();
    }, 500);

    document.getElementById("hostSelect").addEventListener("change", () => {
        debugLog(`Host alterado`);
        loadDashboard();
    });
    
    document.getElementById("rangeSelect").addEventListener("change", () => {
        debugLog(`Range alterado`);
        loadDashboard();
    });

    // Atualiza a cada 60 segundos
    setInterval(() => {
        debugLog(`Auto-atualização (60s)`);
        loadDashboard();
    }, 60000);

    debugLog(`Dashboard pronto!`);
});
