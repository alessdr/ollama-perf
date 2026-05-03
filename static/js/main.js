// Common utility functions
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'API request failed');
        }
        return { success: true, data };
    } catch (error) {
        console.error('API Error:', error);
        alert(error.message);
        return { success: false, error: error.message };
    }
}

// --- Dashboard Logic ---
let avgTimeChartInstance = null;
let avgTPSChartInstance = null;
let avgTTFTChartInstance = null;

async function loadDashboardData() {
    const tableBody = document.querySelector('#recentTestsTable tbody');
    if (!tableBody) return; // Not on dashboard page

    const res = await fetchAPI('/api/dashboard');
    if (!res.success) return;

    const data = res.data;

    // Render Table
    tableBody.innerHTML = '';
    if (data.recent.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No tests run yet.</td></tr>';
    } else {
        data.recent.forEach(test => {
            const row = document.createElement('tr');
            const promptSnippet = test.prompt.length > 50 ? test.prompt.substring(0, 50) + '...' : test.prompt;
            const dateStr = new Date(test.created_at).toLocaleString();
            
            row.innerHTML = `
                <td><strong>${test.model_name}</strong></td>
                <td title="${test.prompt}">${promptSnippet}</td>
                <td>${test.response_time_ms.toFixed(2)}</td>
                <td>${test.tokens_per_second ? test.tokens_per_second.toFixed(2) : '-'}</td>
                <td>${test.ttft_ms ? test.ttft_ms.toFixed(2) : '-'}</td>
                <td><small>${test.prompt_tokens || 0} / ${test.response_tokens || 0}</small></td>
                <td>${dateStr}</td>
            `;
            tableBody.appendChild(row);
        });
    }

    if (data.averages.length === 0) return;

    const labels = data.averages.map(a => a.model_name);
    
    // 1. Latency Chart
    avgTimeChartInstance = createBarChart(
        'avgTimeChart', 
        labels, 
        data.averages.map(a => a.avg_time_ms), 
        'Latency (ms)', 
        'rgba(59, 130, 246, 0.6)', 
        avgTimeChartInstance,
        'ms'
    );

    // 2. Speed Chart
    avgTPSChartInstance = createBarChart(
        'avgTPSChart', 
        labels, 
        data.averages.map(a => a.avg_tps), 
        'Speed (Tok/s)', 
        'rgba(16, 185, 129, 0.6)', 
        avgTPSChartInstance,
        'tok/s'
    );

    // 3. TTFT Chart
    avgTTFTChartInstance = createBarChart(
        'avgTTFTChart', 
        labels, 
        data.averages.map(a => a.avg_ttft), 
        'TTFT (ms)', 
        'rgba(245, 158, 11, 0.6)', 
        avgTTFTChartInstance,
        'ms'
    );

    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function createBarChart(canvasId, labels, data, label, color, existingInstance, unit) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    if (existingInstance) existingInstance.destroy();

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: color,
                borderColor: color.replace('0.6', '1'),
                borderWidth: 2,
                borderRadius: 6,
                barThickness: 'flex',
                maxBarThickness: 50
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.15)', drawBorder: false },
                    ticks: { 
                        color: '#94a3b8', 
                        font: { size: 10 },
                        callback: (v) => v + ' ' + unit
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8', font: { size: 10 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1e293b',
                    padding: 10,
                    cornerRadius: 8
                }
            }
        }
    });
}

async function clearDashboardData() {
    if (!confirm("Tem certeza que deseja zerar todos os dados dos testes? Esta ação não pode ser desfeita.")) {
        return;
    }
    
    const res = await fetchAPI('/api/dashboard/clear', {
        method: 'POST'
    });
    
    if (res.success) {
        if (avgTimeChartInstance) avgTimeChartInstance.destroy();
        if (avgTPSChartInstance) avgTPSChartInstance.destroy();
        if (avgTTFTChartInstance) avgTTFTChartInstance.destroy();
        loadDashboardData();
    }
}

async function generateReport() {
    const btn = document.getElementById('reportBtn');
    const btnText = document.getElementById('reportBtnText');
    const canvas = document.getElementById('avgTimeChart');
    
    if (!canvas || !avgTimeChartInstance) {
        alert("Nenhum dado disponível para gerar o relatório.");
        return;
    }

    const originalText = btnText.innerText;
    btn.disabled = true;
    btnText.innerText = 'Gerando...';

    try {
        const chartImage = canvas.toDataURL('image/png');
        
        const response = await fetch('/api/report/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chart_image: chartImage
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Falha ao gerar relatório');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ollama_performance_report_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error('Report Error:', error);
        alert(error.message);
    } finally {
        btn.disabled = false;
        btnText.innerText = originalText;
    }
}

// --- Models List Logic ---
async function loadModelsList() {
    const tableBody = document.querySelector('#modelsTable tbody');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading models...</td></tr>';

    const res = await fetchAPI('/api/models');
    if (!res.success) {
        tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error loading models. Make sure Ollama is running.</td></tr>`;
        return;
    }

    tableBody.innerHTML = '';
    
    if (res.data.models.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="6" class="text-center">No models found in Ollama. Try pulling one first (e.g., ollama run llama3).</td></tr>';
        return;
    }

    res.data.models.forEach(model => {
        const row = document.createElement('tr');
        const isRunning = model.status === 'Running';
        
        const badgeClass = isRunning ? 'badge success' : 'badge danger';
        const badgeIcon = '<span style="display:inline-block;width:8px;height:8px;background:currentcolor;border-radius:50%;margin-right:6px;"></span>';
        
        let actionBtn = '';
        if (isRunning) {
            actionBtn = `<button class="btn btn-danger btn-sm" onclick="toggleModel('${model.name}', 'unload', this)"><i data-lucide="power-off" style="width:16px;height:16px;"></i> Stop</button>`;
        } else {
            actionBtn = `<button class="btn btn-primary btn-sm" onclick="toggleModel('${model.name}', 'load', this)"><i data-lucide="power" style="width:16px;height:16px;"></i> Load to Memory</button>`;
        }

        row.innerHTML = `
            <td><strong>${model.name}</strong></td>
            <td><span style="color: var(--text-muted);">${model.size_gb ? model.size_gb + ' GB' : '-'}</span></td>
            <td><span class="badge" style="background: rgba(255,255,255,0.1);">${model.parameter_size || '-'}</span></td>
            <td><span class="badge" style="background: rgba(255,255,255,0.1);">${model.quantization || '-'}</span></td>
            <td><span class="${badgeClass}">${badgeIcon}${model.status}</span></td>
            <td>${actionBtn}</td>
        `;
        tableBody.appendChild(row);
    });

    if (window.lucide) {
        window.lucide.createIcons();
    }
}

async function toggleModel(modelName, action, btnElement) {
    const originalText = btnElement.innerText;
    btnElement.innerText = 'Working...';
    btnElement.disabled = true;

    const res = await fetchAPI(`/api/models/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_name: modelName })
    });

    if (res.success) {
        loadModelsList(); // Refresh list to update status
    } else {
        btnElement.innerText = originalText;
        btnElement.disabled = false;
    }
}

// --- Test Page Logic ---
async function populateModelsDropdown() {
    const select = document.getElementById('modelSelect');
    if (!select) return;

    const res = await fetchAPI('/api/models');
    if (!res.success) {
        select.innerHTML = '<option value="">Error loading models</option>';
        return;
    }

    select.innerHTML = '<option value="" disabled selected>Select a model...</option>';
    if (res.data.models.length > 0) {
        select.innerHTML += '<option value="ALL">-- Test All Models Sequentially --</option>';
    }
    
    res.data.models.forEach(model => {
        const option = document.createElement('option');
        option.value = model.name;
        option.textContent = model.name + (model.status === 'Running' ? ' (Loaded)' : '');
        select.appendChild(option);
    });
}

async function runTest(event) {
    event.preventDefault();
    
    const selectEl = document.getElementById('modelSelect');
    const modelName = selectEl.value;
    const prompt = document.getElementById('promptInput').value;
    const btn = document.getElementById('runTestBtn');
    const btnText = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.spinner');
    const resultBox = document.getElementById('testResultContent');

    if (!modelName) {
        alert("Please select a model.");
        return;
    }

    // Set loading state
    btn.disabled = true;
    btnText.textContent = 'Running Test...';
    spinner.classList.remove('hidden');
    const runIcon = document.getElementById('runIcon');
    if (runIcon) runIcon.classList.add('hidden');
    
    resultBox.innerHTML = '';
    resultBox.classList.remove('empty');

    if (modelName === 'ALL') {
        const modelsToTest = Array.from(selectEl.options)
            .map(opt => opt.value)
            .filter(val => val !== '' && val !== 'ALL');
            
        logToConsole(`Starting sequential test for ${modelsToTest.length} models...`);
        
        for (const m of modelsToTest) {
            logToConsole(`Testing model: ${m}...`);
            resultBox.innerHTML += `<div style="margin-bottom: 20px;"><h4>Evaluating: ${m}</h4><p class="placeholder-text" style="color: var(--text-muted);">Waiting for response...</p></div>`;
            resultBox.scrollTop = resultBox.scrollHeight;
            
            const res = await fetchAPI('/api/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: m, prompt: prompt })
            });
            
            // Remove the loading text for this model
            resultBox.lastChild.remove();
            
            if (res.success) {
                const data = res.data.metrics;
                logToConsole(`[${m}] Test completed: ${data.total_duration_ms.toFixed(2)} ms`);
                resultBox.innerHTML += `
                    <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px dashed var(--border);">
                        <h4 style="color: var(--primary); margin-bottom: 10px;">${m}</h4>
                        <div>${data.response.replace(/\n/g, '<br>')}</div>
                        <div class="metric-text" style="margin-top: 10px; padding-top: 0; border: none; font-size: 1rem;">
                            Response Time: ${data.total_duration_ms.toFixed(2)} ms
                        </div>
                    </div>
                `;
            } else {
                logToConsole(`[${m}] Test failed: ${res.error}`, true);
                resultBox.innerHTML += `
                    <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px dashed var(--border);">
                        <h4 style="color: var(--danger); margin-bottom: 10px;">${m}</h4>
                        <p style="color: var(--danger)">Error: ${res.error}</p>
                    </div>
                `;
            }
            resultBox.scrollTop = resultBox.scrollHeight;
        }
        logToConsole(`Sequential testing completed.`);
    } else {
        logToConsole(`Starting test for model: ${modelName}`);
        logToConsole(`Prompt length: ${prompt.length} characters`);
        
        resultBox.innerHTML = '<p class="placeholder-text">Waiting for response...</p>';

        logToConsole(`Request sent to Ollama API. Waiting for response...`);
        const res = await fetchAPI('/api/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: modelName, prompt: prompt })
        });

        if (res.success) {
            const data = res.data.metrics;
            logToConsole(`Test completed successfully.`);
            logToConsole(`Total Response Time: ${data.total_duration_ms.toFixed(2)} ms`);
            
            resultBox.innerHTML = `
                <div>${data.response.replace(/\n/g, '<br>')}</div>
                <div class="metric-text">
                    Response Time: ${data.total_duration_ms.toFixed(2)} ms
                </div>
            `;
        } else {
            logToConsole(`Test failed: ${res.error}`, true);
            resultBox.innerHTML = `<p class="placeholder-text" style="color: var(--danger)">Error: ${res.error}</p>`;
        }
    }

    // Reset button state
    btn.disabled = false;
    btnText.textContent = 'Run Test';
    spinner.classList.add('hidden');
    if (runIcon) runIcon.classList.remove('hidden');
}

// --- Console Helper ---
function logToConsole(message, isError = false) {
    const consoleBox = document.getElementById('executionConsole');
    if (!consoleBox) return;
    
    const time = new Date().toLocaleTimeString();
    const p = document.createElement('p');
    if (isError) {
        p.style.color = 'var(--danger)';
    }
    p.innerHTML = `<span class="console-time">[${time}]</span> ${message}`;
    
    consoleBox.appendChild(p);
    consoleBox.scrollTop = consoleBox.scrollHeight;
}
