let cpuChart = null;
let memoryChart = null;
let lastLoadedRange = null; // Rastreia o último intervalo carregado

/* ===== DEBUG: Log para verificar carregamento ===== */
function debugLog(msg) {
    console.log(`[MONITOR ${new Date().toLocaleTimeString()}] ${msg}`);
}

/* ===== Carrega lista de hosts ===== */
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
                second: '2-digit'  // Adiciona segundos para 1h/6h
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
        // Gera um random token único para cada requisição (anti-cache)
        const randomToken = Math.random().toString(36).substring(2, 15);
        const url = `/api/metrics/report/?host=${hostId}&metric_type=${metricType}&range=${range}&t=${Date.now()}&rand=${randomToken}`;
        
        debugLog(`Buscando ${metricType} para ${range}: ${url}`);

        const res = await fetch(url, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        
        if (!res.ok) throw new Error(`Erro HTTP ${res.status}`);
        const json = await res.json();

        let items = [];
        if (json.items) items = json.items;
        else if (json.report) items = json.report;
        else if (json[metricType]) items = json[metricType];

        debugLog(`${metricType} retornou ${items.length} itens para ${range}`);
        return items;

    } catch (error) {
        console.error("Erro ao carregar métricas:", error);
        return [];
    }
}

/* ===== Renderiza gráfico com suporte a diferentes intervalos ===== */
function renderChartWithEMA(canvasId, label, labels, values, colorLine, colorEMA, range) {
    const canvas = document.getElementById(canvasId);

    // Destroi gráfico anterior completamente
    if (canvas.chartInstance) {
        canvas.chartInstance.destroy();
        canvas.chartInstance = null;
    }

    debugLog(`Renderizando ${label} com ${values.length} pontos para intervalo ${range}`);

    const emaValues = calculateEMA(values);

    // Limita ticks de acordo com o intervalo
    let maxTicksLimit = 30;
    if (range === '7d') {
        maxTicksLimit = 100;
    } else if (range === '24h') {
        maxTicksLimit = 50;
    } else if (range === '6h') {
        maxTicksLimit = 40;  // 6h = ~360 pontos (6 × 60)
    } else if (range === '1h') {
        maxTicksLimit = 25;  // 1h = ~60 pontos
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
                        usePointStyle: true,
                        padding: 20
                    }
                },
                zoom: {
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
}

/* ===== Atualiza estatísticas ===== */
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

/* ===== PRINCIPAL: Carrega dashboard com diferenciação correta de intervalos ===== */
async function loadDashboard() {
    const hostSelect = document.getElementById("hostSelect");
    const rangeSelect = document.getElementById("rangeSelect");
    
    const hostId = hostSelect.value;
    const range = rangeSelect.value;

    if (!hostId) return;

    // Verifica se o intervalo realmente mudou
    if (lastLoadedRange === range && lastLoadedRange !== null) {
        debugLog(`⚠️ AVISO: Intervalo ${range} já estava carregado! Forçando recarga...`);
    }

    lastLoadedRange = range;
    debugLog(`========================================`);
    debugLog(`Atualizando dashboard: Host=${hostId}, Range=${range}`);
    debugLog(`========================================`);

    // ===== CPU =====
    const cpu = await loadMetrics(hostId, range, "cpu_percent");
    
    if (cpu && cpu.length > 0) {
        const labels = cpu.map(c => formatTimestamp(c.timestamp, range));
        const values = cpu.map(c => Number(c.value));

        debugLog(`✅ CPU carregou: ${cpu.length} pontos`);
        debugLog(`   Primeiro: ${labels[0]} = ${values[0]}%`);
        debugLog(`   Último: ${labels[labels.length-1]} = ${values[values.length-1]}%`);

        renderChartWithEMA("cpuChart", "CPU (%)", labels, values, "#F44336", "#FF9800", range);
        updateStats("cpuStats", values);
    } else {
        debugLog(`❌ CPU: Nenhum dado retornado!`);
        const ctx = document.getElementById("cpuChart");
        if(ctx.chartInstance) ctx.chartInstance.destroy();
        document.getElementById("cpuStats").textContent = "Sem dados para este intervalo";
    }

    // ===== MEMÓRIA =====
    const mem = await loadMetrics(hostId, range, "memory_percent");
    
    if (mem && mem.length > 0) {
        const labels = mem.map(m => formatTimestamp(m.timestamp, range));
        const values = mem.map(m => Number(m.value));

        debugLog(`✅ Memória carregou: ${mem.length} pontos`);
        debugLog(`   Primeiro: ${labels[0]} = ${values[0]}%`);
        debugLog(`   Último: ${labels[labels.length-1]} = ${values[values.length-1]}%`);

        renderChartWithEMA("memoryChart", "Memória RAM (%)", labels, values, "#2196F3", "#00BCD4", range);
        updateStats("memoryStats", values);
    } else {
        debugLog(`❌ Memória: Nenhum dado retornado!`);
        const ctx = document.getElementById("memoryChart");
        if(ctx.chartInstance) ctx.chartInstance.destroy();
        document.getElementById("memoryStats").textContent = "Sem dados para este intervalo";
    }

    debugLog(`Dashboard atualizado com sucesso!`);
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
    debugLog(`Iniciando aplicação...`);
    
    await loadHosts();
    debugLog(`Hosts carregados`);
    
    // Aguarda um pouco para garantir que os hosts foram carregados
    setTimeout(() => {
        loadDashboard();
    }, 500);

    document.getElementById("hostSelect").addEventListener("change", () => {
        debugLog(`🔄 Host alterado`);
        lastLoadedRange = null; // Reset para forçar recarga
        loadDashboard();
    });
    
    document.getElementById("rangeSelect").addEventListener("change", () => {
        debugLog(`🔄 Intervalo alterado`);
        lastLoadedRange = null; // Reset para forçar recarga completa
        loadDashboard();
    });

    // Atualiza a cada 60 segundos
    setInterval(() => {
        lastLoadedRange = null; // Reset para forçar recarga
        loadDashboard();
    }, 60000);

    debugLog(`Aplicação inicializada com sucesso`);
});
