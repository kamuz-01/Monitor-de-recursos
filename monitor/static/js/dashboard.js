let memoryChart = null;
let diskChart = null;
let cpuChart = null;

// --------------------------------
// Carrega lista de hosts
// --------------------------------
async function loadHosts() {
    try {
        const res = await fetch("/api/hosts/");
        const data = await res.json();
        const sel = document.getElementById("hostSelect");

        sel.innerHTML = "";
        data.forEach(h => {
            sel.innerHTML += `<option value="${h.id}">${h.hostname}</option>`;
        });
    } catch (error) {
        console.error("Erro ao carregar hosts:", error);
    }
}

// --------------------------------
// Carrega métricas com intervalo
// --------------------------------
async function loadMetrics(hostId, range, metricType) {
    try {
        let url = `/api/metrics/?host=${hostId}&metric_type=${metricType}&range=${range}`;
        console.log("Fetchando:", url);
        
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        
        const json = await res.json();
        console.log(`Dados recebidos para ${metricType}:`, json);
        
        return json.results || json;
    } catch (error) {
        console.error("Erro ao carregar métricas:", error);
        return [];
    }
}

// --------------------------------
// Renderiza gráfico
// --------------------------------
function renderChart(canvasId, label, labels, values) {
    const canvas = document.getElementById(canvasId);

    // Destruir gráfico anterior
    if (canvas.chartInstance) {
        canvas.chartInstance.destroy();
    }

    canvas.chartInstance = new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: values,
                borderColor: '#4CAF50',
                backgroundColor: 'rgba(76, 175, 80, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'Percentual (%)'
                    }
                }
            }
        }
    });
}

// --------------------------------
// Carrega dashboard completo
// --------------------------------
async function loadDashboard() {
    const hostId = document.getElementById("hostSelect").value;
    const range = document.getElementById("rangeSelect").value;

    console.log("Carregando dashboard para host:", hostId, "range:", range);

    // Memória
    const mem = await loadMetrics(hostId, range, "memory_percent_avg");
    if (mem && mem.length > 0) {
        const labels = mem.map(m => new Date(m.timestamp).toLocaleString('pt-BR'));
        const valuesMem = mem.map(m => m.value);
        console.log("Renderizando memória com", mem.length, "pontos");
        renderChart("memoryChart", "Memória (%)", labels, valuesMem);
    } else {
        console.warn("Nenhum dado de memória");
    }

    // Disco
    const disk = await loadMetrics(hostId, range, "disk_percent_avg");
    if (disk && disk.length > 0) {
        const labels = disk.map(d => new Date(d.timestamp).toLocaleString('pt-BR'));
        const valuesDisk = disk.map(d => d.value);
        console.log("Renderizando disco com", disk.length, "pontos");
        renderChart("diskChart", "Disco (%)", labels, valuesDisk);
    } else {
        console.warn("Nenhum dado de disco");
    }

    // CPU
    const cpu = await loadMetrics(hostId, range, "cpu_percent_avg");
    if (cpu && cpu.length > 0) {
        const labels = cpu.map(c => new Date(c.timestamp).toLocaleString('pt-BR'));
        const valuesCpu = cpu.map(c => c.value);
        console.log("Renderizando CPU com", cpu.length, "pontos");
        renderChart("cpuChart", "CPU (%)", labels, valuesCpu);
    } else {
        console.warn("Nenhum dado de CPU");
    }
}

// --------------------------------
// Gera relatório (CSV ou JSON)
// --------------------------------
async function generateReport() {
    const hostId = document.getElementById("hostSelect").value;
    const range = document.getElementById("rangeSelect").value;
    const format = document.getElementById("formatSelect")?.value || "json";

    try {
        // Uso o endpoint correto: /api/metrics/report/
        let url = `/api/metrics/report/?host=${hostId}&range=${range}`;

        console.log("Gerando relatório:", url);
        const res = await fetch(url);
        
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        
        const data = await res.json();
        console.log("Relatório gerado:", data);

        if (format === "csv") {
            downloadCSV(data.report, hostId);
        } else {
            downloadJSON(data, hostId);
        }
    } catch (error) {
        console.error("Erro ao gerar relatório:", error);
        alert("Erro ao gerar relatório!");
    }
}

// --------------------------------
// Download CSV
// --------------------------------
function downloadCSV(metrics, hostId) {
    if (!metrics || metrics.length === 0) {
        alert("Nenhum dado para exportar!");
        return;
    }

    const headers = ["Hostname", "Tipo de Métrica", "Valor", "Timestamp"];
    const rows = metrics.map(m => [
        m.hostname || "N/A",
        m.metric_type,
        m.value,
        m.timestamp
    ]);

    let csv = headers.join(",") + "\n";
    rows.forEach(row => {
        csv += row.map(cell => `"${cell}"`).join(",") + "\n";
    });

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `relatorio_${hostId}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// --------------------------------
// Download JSON
// --------------------------------
function downloadJSON(data, hostId) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `relatorio_${hostId}_${new Date().toISOString().split('T')[0]}.json`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// --------------------------------
// Inicialização da página
// --------------------------------
document.addEventListener("DOMContentLoaded", async () => {
    await loadHosts();
    loadDashboard();

    // Atualizar ao mudar filtros
    document.getElementById("hostSelect").addEventListener("change", loadDashboard);
    document.getElementById("rangeSelect").addEventListener("change", loadDashboard);
    
    // Auto-refresh a cada 30 segundos
    setInterval(loadDashboard, 30000);
});
