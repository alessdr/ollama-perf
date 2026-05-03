// Global SweetAlert2 Config for Signal & Pulse Theme
const SignalAlert = Swal.mixin({
    background: '#09090b',
    color: '#fafafa',
    confirmButtonColor: '#f97316',
    cancelButtonColor: '#27272a',
    borderRadius: '0px',
    customClass: {
        popup: 'swal-signal-popup',
        confirmButton: 'swal-signal-btn',
        cancelButton: 'swal-signal-btn'
    }
});

// Global State for Stopping Tests
let currentTestAbortController = null;
let isStopRequested = false;

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
        SignalAlert.fire({
            icon: 'error',
            title: 'SYSTEM ERROR',
            text: error.message,
            confirmButtonText: 'ACKNOWLEDGE'
        });
        return { success: false, error: error.message };
    }
}

// --- Dashboard Logic ---
let avgTimeChartInstance = null;
let avgTPSChartInstance = null;
let avgTTFTChartInstance = null;
let recentTestsCache = [];

async function loadDashboardData() {
    const tableBody = document.querySelector('#recentTestsTable tbody');
    if (!tableBody) return; // Not on dashboard page

    const res = await fetchAPI('/api/dashboard');
    if (!res.success) return;

    const data = res.data;
    recentTestsCache = data.recent;

    // Render Table
    tableBody.innerHTML = '';
    if (data.recent.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" class="text-center">No tests run yet.</td></tr>';
    } else {
        data.recent.forEach((test, index) => {
            const row = document.createElement('tr');
            row.setAttribute('onclick', `showTestDetails(${index})`);
            row.classList.add('clickable-row');
            
            const promptSnippet = test.prompt.length > 20 ? test.prompt.substring(0, 20) + '...' : test.prompt;
            const dateStr = new Date(test.created_at).toLocaleString();
            
            row.innerHTML = `
                <td><strong>${test.model_name}</strong></td>
                <td>
                    <span class="prompt-badge-static">
                        <i data-lucide="eye" style="width:12px;height:12px;"></i> ${promptSnippet}
                    </span>
                </td>
                <td><span style="color: var(--primary);">${test.response_time_ms.toFixed(2)}</span></td>
                <td style="font-family: var(--font-code);">${test.tokens_per_second ? test.tokens_per_second.toFixed(2) : '-'}</td>
                <td style="font-family: var(--font-code);">${test.ttft_ms ? test.ttft_ms.toFixed(2) : '-'}</td>
                <td><small>${test.prompt_tokens || 0} / ${test.response_tokens || 0}</small></td>
                <td><small style="color: var(--text-muted);">${dateStr}</small></td>
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
        'rgba(249, 115, 22, 0.4)', 
        avgTimeChartInstance,
        'ms'
    );

    // 2. Speed Chart
    avgTPSChartInstance = createBarChart(
        'avgTPSChart', 
        labels, 
        data.averages.map(a => a.avg_tps), 
        'Speed (Tok/s)', 
        'rgba(34, 197, 94, 0.4)', 
        avgTPSChartInstance,
        'tok/s'
    );

    // 3. TTFT Chart
    avgTTFTChartInstance = createBarChart(
        'avgTTFTChart', 
        labels, 
        data.averages.map(a => a.avg_ttft), 
        'TTFT (ms)', 
        'rgba(161, 161, 170, 0.4)', 
        avgTTFTChartInstance,
        'ms'
    );

    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function showTestDetails(index) {
    const test = recentTestsCache[index];
    if (!test) return;

    SignalAlert.fire({
        title: `LOG INSPECTION: ${test.model_name}`,
        width: '800px',
        html: `
            <div style="text-align: left; font-family: var(--font-family);">
                <!-- Prompt Section -->
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 0.7rem; text-transform: uppercase; color: var(--primary); margin-bottom: 8px; letter-spacing: 0.1em;">Test Prompt</div>
                    <div style="background: #000; padding: 16px; border: 1px solid var(--border); font-family: var(--font-code); font-size: 0.85rem; color: #d4d4d8; white-space: pre-wrap; max-height: 150px; overflow-y: auto;">${test.prompt}</div>
                </div>

                <!-- Model Response Section -->
                <div style="margin-bottom: 20px;">
                    <div style="font-size: 0.7rem; text-transform: uppercase; color: var(--success); margin-bottom: 8px; letter-spacing: 0.1em;">Model Response</div>
                    <div style="background: #000; padding: 16px; border: 1px solid var(--border); font-family: var(--font-code); font-size: 0.85rem; color: var(--success); white-space: pre-wrap; max-height: 250px; overflow-y: auto;">${test.response || '<span style="color:var(--text-muted); opacity: 0.5;">[DATA NOT PERSISTED IN OLD LOGS]</span>'}</div>
                </div>

                <!-- Technical Metrics Grid -->
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                    <div style="background: rgba(255,255,255,0.02); padding: 12px; border: 1px solid var(--border);">
                        <span style="font-size: 0.6rem; color: var(--text-muted); display: block; text-transform: uppercase;">Latency</span>
                        <span style="font-size: 0.9rem; font-weight: 600; font-family: var(--font-code);">${test.response_time_ms.toFixed(2)}ms</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.02); padding: 12px; border: 1px solid var(--border);">
                        <span style="font-size: 0.6rem; color: var(--text-muted); display: block; text-transform: uppercase;">Speed</span>
                        <span style="font-size: 0.9rem; font-weight: 600; font-family: var(--font-code);">${test.tokens_per_second ? test.tokens_per_second.toFixed(2) : '0.00'}t/s</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.02); padding: 12px; border: 1px solid var(--border);">
                        <span style="font-size: 0.6rem; color: var(--text-muted); display: block; text-transform: uppercase;">TTFT</span>
                        <span style="font-size: 0.9rem; font-weight: 600; font-family: var(--font-code);">${test.ttft_ms ? test.ttft_ms.toFixed(2) : '0.00'}ms</span>
                    </div>
                    <div style="background: rgba(255,255,255,0.02); padding: 12px; border: 1px solid var(--border);">
                        <span style="font-size: 0.6rem; color: var(--text-muted); display: block; text-transform: uppercase;">Tokens</span>
                        <span style="font-size: 0.9rem; font-weight: 600; font-family: var(--font-code);">${test.prompt_tokens || 0}/${test.response_tokens || 0}</span>
                    </div>
                </div>

                <div style="margin-top: 16px; font-size: 0.7rem; color: var(--text-muted); text-align: right;">
                    Diagnostic Timestamp: ${new Date(test.created_at).toLocaleString()}
                </div>
            </div>
        `,
        confirmButtonText: 'CLOSE INSPECTOR'
    });
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
                borderColor: color.replace('0.4', '1'),
                borderWidth: 1,
                borderRadius: 0,
                barThickness: 20
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                    ticks: { 
                        color: '#71717a', 
                        font: { size: 10, family: 'JetBrains Mono' },
                        callback: (v) => v + ' ' + unit
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#71717a', font: { size: 10, family: 'JetBrains Mono' } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#09090b',
                    titleFont: { family: 'Outfit', size: 13 },
                    bodyFont: { family: 'JetBrains Mono', size: 11 },
                    padding: 12,
                    cornerRadius: 0,
                    borderColor: '#27272a',
                    borderWidth: 1
                }
            }
        }
    });
}

async function clearDashboardData() {
    const result = await SignalAlert.fire({
        title: 'WIPE ALL DATA?',
        text: "This action will permanently delete all test metrics from the database.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'CONFIRM WIPE',
        cancelButtonText: 'ABORT',
        reverseButtons: true
    });

    if (result.isConfirmed) {
        const res = await fetchAPI('/api/dashboard/clear', {
            method: 'POST'
        });
        
        if (res.success) {
            SignalAlert.fire({
                icon: 'success',
                title: 'DATA WIPED',
                text: 'The diagnostic database has been cleared.',
                timer: 2000,
                showConfirmButton: false
            });
            if (avgTimeChartInstance) avgTimeChartInstance.destroy();
            if (avgTPSChartInstance) avgTPSChartInstance.destroy();
            if (avgTTFTChartInstance) avgTTFTChartInstance.destroy();
            loadDashboardData();
        }
    }
}

async function generateReport() {
    const btn = document.getElementById('reportBtn');
    const btnText = document.getElementById('reportBtnText');
    const canvasTime = document.getElementById('avgTimeChart');
    const canvasTPS = document.getElementById('avgTPSChart');
    const canvasTTFT = document.getElementById('avgTTFTChart');
    
    if (!canvasTime || !avgTimeChartInstance) {
        SignalAlert.fire({
            icon: 'info',
            title: 'NO DATA',
            text: "Nenhum dado disponível para gerar o relatório.",
            confirmButtonText: 'UNDERSTOOD'
        });
        return;
    }

    const originalText = btnText.innerText;
    btn.disabled = true;
    btnText.innerText = 'Analyzing...';

    // Show Loading Modal
    SignalAlert.fire({
        title: 'GENERATING AUDIT REPORT',
        html: 'Capturing charts and compiling AI technical analysis...<br><br><div class="custom-loader"></div>',
        allowOutsideClick: false,
        showConfirmButton: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    try {
        const chartImageTime = canvasTime.toDataURL('image/png');
        const chartImageTPS = canvasTPS ? canvasTPS.toDataURL('image/png') : null;
        const chartImageTTFT = canvasTTFT ? canvasTTFT.toDataURL('image/png') : null;
        
        const response = await fetch('/api/report/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                chart_latency: chartImageTime,
                chart_speed: chartImageTPS,
                chart_ttft: chartImageTTFT
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
        SignalAlert.fire({
            icon: 'error',
            title: 'REPORT FAILED',
            text: error.message
        });
    } finally {
        btn.disabled = false;
        btnText.innerText = originalText;
        Swal.close();
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
    
    // Show Stop Button
    const stopBtn = document.getElementById('stopTestBtn');
    if (stopBtn) stopBtn.classList.remove('hidden');

    // Reset Stop State
    isStopRequested = false;
    currentTestAbortController = new AbortController();

    if (!modelName) {
        SignalAlert.fire({
            icon: 'warning',
            title: 'SELECTION REQUIRED',
            text: "Please select a model for diagnostics.",
            confirmButtonText: 'OK'
        });
        return;
    }

    // Set loading state
    btn.disabled = true;
    selectEl.disabled = true;
    document.getElementById('promptInput').disabled = true;
    
    btnText.textContent = 'Running Test...';
    spinner.classList.remove('hidden');
    const runIcon = document.getElementById('runIcon');
    if (runIcon) runIcon.classList.add('hidden');
    
    resultBox.innerHTML = '';
    resultBox.classList.remove('empty');

    logToConsole('Diagnostic environment initialized...');

    if (modelName === 'ALL') {
        const modelsToTest = Array.from(selectEl.options)
            .map(opt => opt.value)
            .filter(val => val !== '' && val !== 'ALL');
            
        const totalModels = modelsToTest.length;
        logToConsole(`Starting sequential test for ${totalModels} models...`);
        
        for (let i = 0; i < totalModels; i++) {
            if (isStopRequested) break;

            const m = modelsToTest[i];
            const currentProgress = `(${i + 1}/${totalModels})`;
            
            try {
                logToConsole(`Testing model ${currentProgress}: ${m}...`);
                resultBox.innerHTML += `<div style="margin-bottom: 20px;"><h4>Evaluating ${currentProgress}: ${m}</h4><p class="placeholder-text" style="color: var(--text-muted);">Waiting for response...</p></div>`;
                resultBox.scrollTop = resultBox.scrollHeight;
                
                const res = await fetchAPI('/api/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_name: m, prompt: prompt }),
                    signal: currentTestAbortController.signal
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
                    if (isStopRequested) throw new Error("Stop Requested");
                    logToConsole(`[${m}] Test failed: ${res.error}`, true);
                    resultBox.innerHTML += `
                        <div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px dashed var(--border);">
                            <h4 style="color: var(--danger); margin-bottom: 10px;">${m}</h4>
                            <p style="color: var(--danger)">Error: ${res.error}</p>
                        </div>
                    `;
                }
            } catch (err) {
                if (isStopRequested) {
                    logToConsole(`[${m}] Test aborted by user.`, true);
                } else {
                    logToConsole(`[${m}] Unexpected error: ${err.message}`, true);
                }
            } finally {
                // ALWAYS unload model to save VRAM, even if aborted
                logToConsole(`[${m}] Releasing VRAM resources...`);
                await fetchAPI('/api/models/unload', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ model_name: m })
                });
                resultBox.scrollTop = resultBox.scrollHeight;
            }
        }
        logToConsole(`Sequential testing completed.`);
    } else {
        logToConsole(`Starting test for model: ${modelName}`);
        logToConsole(`Prompt length: ${prompt.length} characters`);
        
        resultBox.innerHTML = '<p class="placeholder-text">Waiting for response...</p>';

        logToConsole(`Request sent to Ollama API. Waiting for response...`);
        try {
            const res = await fetchAPI('/api/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName, prompt: prompt }),
                signal: currentTestAbortController.signal
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
                if (isStopRequested) throw new Error("Stop Requested");
                logToConsole(`Test failed: ${res.error}`, true);
                resultBox.innerHTML = `<p class="placeholder-text" style="color: var(--danger)">Error: ${res.error}</p>`;
            }
        } catch (err) {
            if (isStopRequested) {
                logToConsole(`Test aborted by user.`, true);
            } else {
                logToConsole(`Error: ${err.message}`, true);
            }
        } finally {
            // Auto-unload model after test
            logToConsole(`Releasing VRAM for ${modelName}...`);
            await fetchAPI('/api/models/unload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: modelName })
            });
        }
    }

    // Reset button and input states
    btn.disabled = false;
    selectEl.disabled = false;
    document.getElementById('promptInput').disabled = false;
    if (stopBtn) stopBtn.classList.add('hidden');
    
    btnText.textContent = 'Run Test';
    spinner.classList.add('hidden');
    if (runIcon) runIcon.classList.remove('hidden');

    if (isStopRequested) {
        logToConsole('DIAGNOSTIC HALTED BY USER.', true);
        SignalAlert.fire({
            icon: 'info',
            title: 'HALTED',
            text: 'The diagnostic sequence was stopped manually.',
            confirmButtonText: 'OK'
        });
    } else {
        // Completion Popup
        SignalAlert.fire({
            icon: 'success',
            title: 'DIAGNOSTIC COMPLETE',
            text: modelName === 'ALL' ? 'Sequential testing of all models finished.' : `Test for ${modelName} finished successfully.`,
            confirmButtonText: 'VIEW METRICS'
        });
    }

    currentTestAbortController = null;

    // Final global cleanup to ensure no models remain in memory
    logToConsole('Finalizing: Ensuring all models are unloaded...');
    await fetchAPI('/api/models/unload_all', { method: 'POST' });
}

async function stopTest() {
    const result = await SignalAlert.fire({
        title: 'HALT DIAGNOSTIC?',
        text: "This will terminate the current test and unload models from memory.",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'YES, STOP NOW',
        cancelButtonText: 'CONTINUE TEST',
        reverseButtons: true
    });

    if (result.isConfirmed) {
        isStopRequested = true;
        if (currentTestAbortController) {
            currentTestAbortController.abort();
        }
        const stopBtn = document.getElementById('stopTestBtn');
        if (stopBtn) {
            stopBtn.innerText = 'Stopping...';
            stopBtn.disabled = true;
        }
    }
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
