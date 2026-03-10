const bands = [
    { id: 'band_1', label: 'Bass Boost', freq: '120 Hz', gainMin: 0, gainMax: 10, qMin: 0.1, qMax: 5 },
    { id: 'band_2', label: 'Foundation', freq: '200 Hz', gainMin: 0, gainMax: 10, qMin: 0.1, qMax: 5 },
    { id: 'band_3', label: 'Warmth', freq: '400 Hz', gainMin: 0, gainMax: 10, qMin: 0.1, qMax: 5 },
    { id: 'band_4', label: 'Anti-Boxy', freq: '600 Hz', gainMin: -5, gainMax: 0, qMin: 0.1, qMax: 5 },
    { id: 'band_5', label: 'Anti-Nasal', freq: '1000 Hz', gainMin: -5, gainMax: 0, qMin: 0.1, qMax: 5 },
    { id: 'band_6', label: 'Midrange', freq: '1500 Hz', gainMin: -5, gainMax: 0, qMin: 0.1, qMax: 5 },
    { id: 'band_7', label: 'Anti-Plastic', freq: '2000 Hz', gainMin: -5, gainMax: 0, qMin: 0.1, qMax: 5 },
    { id: 'band_8', label: 'Presence', freq: '4500 Hz', gainMin: 0, gainMax: 5, qMin: 0.1, qMax: 5 },
    { id: 'band_9', label: 'Brilliance', freq: '9000 Hz', gainMin: 0, gainMax: 5, qMin: 0.1, qMax: 5 },
    { id: 'band_10', label: 'Air', freq: '12000 Hz', gainMin: 0, gainMax: 5, qMin: 0.1, qMax: 5 }
];

const originalGains = {};
let currentGains = {};
let saveTimeout;
let currentConfig = null;
let configCheckInterval = null;

async function initializeEQ() {
    try {
        const response = await fetch('/api/gains');
        
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        
        currentGains = await response.json();
        Object.assign(originalGains, currentGains);
        
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('eqGrid').style.display = 'grid';
        document.getElementById('controlsSection').style.display = 'flex';
        
        renderEQ();
        showStatus(_('Configuration loaded successfully'), 'success');
        startConfigPolling();
        
    } catch (error) {
        // Use default values on error
        bands.forEach(band => {
            currentGains[`${band.id}`] = 0;
            currentGains[`${band.id}_q`] = 1.0;
        });
        Object.assign(originalGains, currentGains);
        
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('eqGrid').style.display = 'grid';
        document.getElementById('controlsSection').style.display = 'flex';
        
        renderEQ();
        showStatus(`${_('Error loading configuration')}: ${error.message}`, 'error');
    }
}

function renderEQ() {
    const grid = document.getElementById('eqGrid');
    grid.innerHTML = '';

    bands.forEach(band => {
        const gainValue = currentGains[band.id] || 0;
        const qValue = currentGains[`${band.id}_q`] || 1.0;
        
        const bandHtml = `
            <div class="eq-band">
                <div class="band-label">${band.label}</div>
                <div class="band-freq">${band.freq}</div>
                
                <div class="slider-label">${_('Gain (dB)')}</div>
                <div class="slider-container">
                    <input type="range" 
                           id="slider_${band.id}" 
                           min="${band.gainMin}" 
                           max="${band.gainMax}" 
                           step="0.1" 
                           value="${gainValue}"
                           oninput="onSliderInput('${band.id}')"
                           onmouseup="onSliderEnd('${band.id}')"
                           ontouchend="onSliderEnd('${band.id}')">
                    <div class="value-display" id="value_${band.id}">${parseFloat(gainValue).toFixed(1)} dB</div>
                    <div class="band-range">${band.gainMin} - ${band.gainMax} dB</div>
                </div>
                
                <div class="slider-label">${_('Q (Width)')}</div>
                <div class="slider-container">
                    <input type="range" 
                           id="slider_${band.id}_q" 
                           min="${band.qMin}" 
                           max="${band.qMax}" 
                           step="0.1" 
                           value="${qValue}"
                           oninput="onQSliderChange('${band.id}')">
                    <div class="value-display" id="value_${band.id}_q">${parseFloat(qValue).toFixed(1)}</div>
                    <div class="band-range">${band.qMin} - ${band.qMax}</div>
                </div>
            </div>
        `;
        grid.innerHTML += bandHtml;
    });
}

function updateValue(key, value) {
    currentGains[key] = parseFloat(value);
    document.getElementById(`value_${key}`).textContent = parseFloat(value).toFixed(1) + (key.includes('_q') ? '' : ' dB');
}

function onSliderInput(bandId) {
    // Frontend update only - no server call
    const gainSlider = document.getElementById(`slider_${bandId}`);
    const valueDisplay = document.getElementById(`value_${bandId}`);
    if (gainSlider && valueDisplay) {
        valueDisplay.textContent = parseFloat(gainSlider.value).toFixed(1) + ' dB';
        currentGains[bandId] = parseFloat(gainSlider.value);
    }
    showStatus(_('Adjusting value (will save on release)'), 'info');
}

function onSliderEnd(bandId) {
    // Called when user releases slider (mouseup/touchend)
    showStatus(_('Saving changes...'), 'info');
    
    const data = {};
    bands.forEach(band => {
        const gainSlider = document.getElementById(`slider_${band.id}`);
        const qSlider = document.getElementById(`slider_${band.id}_q`);
        if (gainSlider) data[band.id] = parseFloat(gainSlider.value);
        if (qSlider) data[`${band.id}_q`] = parseFloat(qSlider.value);
    });
    
    data['_backup'] = false;
    data['_restart'] = true;
    
    fetch('/api/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(result => {
        if (result.status === 'ok' || result.status === 'partial') {
            showStatus(_('Changes applied'), 'success');
        } else {
            showStatus(`_${result.message}`, 'error');
        }
    })
    .catch(error => showStatus(`Error: ${error.message}`, 'error'));
}

function onQSliderChange(bandId) {
    // Update frontend immediately
    const qSlider = document.getElementById(`slider_${bandId}_q`);
    const valueDisplay = document.getElementById(`value_${bandId}_q`);
    if (qSlider && valueDisplay) {
        valueDisplay.textContent = parseFloat(qSlider.value).toFixed(1);
        currentGains[`${bandId}_q`] = parseFloat(qSlider.value);
    }
    
    showStatus(_('Saving changes...'), 'info');
    
    // Debounce: save after 500ms inactivity
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        saveChanges();
    }, 500);
}

async function saveChanges() {
    const data = {};
    
    // Collect all slider values
    bands.forEach(band => {
        const gainSlider = document.getElementById(`slider_${band.id}`);
        const qSlider = document.getElementById(`slider_${band.id}_q`);
        
        if (gainSlider) data[band.id] = parseFloat(gainSlider.value);
        if (qSlider) data[`${band.id}_q`] = parseFloat(qSlider.value);
    });
    
    try {
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.status === 'ok' || result.status === 'partial') {
            showStatus(_('Changes applied'), 'success');
        } else {
            showStatus(`Error: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
}

async function applyChangesWithRestart() {
    showStatus(_('Saving changes and restarting PipeWire...'), 'info');

    try {
        const data = { ...currentGains };
        data['_backup'] = true;
        data['_restart'] = true;
        
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        
        if (response.ok) {
            showStatus(`${result.message}`, 'success');
        } else {
            showStatus(`Error: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`Error saving changes: ${error.message}`, 'error');
    }
}

async function applyChanges() {
    showStatus(_('Saving changes...'), 'info');

    try {
        const data = { ...currentGains };
        data['_backup'] = true;
        data['_restart'] = true;
        
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        
        if (response.ok) {
            showStatus(`${result.message}`, 'success');
        } else {
            showStatus(`Error: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`Error saving changes: ${error.message}`, 'error');
    }
}

function resetAll() {
    if (confirm(_('Reset all EQ values to default?'))) {
        Object.keys(currentGains).forEach(key => {
            currentGains[key] = originalGains[key] || 0;
        });
        renderEQ();
        applyChangesWithRestart();
    }
}

function resetPreset() {
    if (confirm(_('Restore last backup?'))) {
        Object.assign(currentGains, originalGains);
        renderEQ();
        applyChangesWithRestart();
    }
}

function loadPreset(preset) {
    const presets = {
        music: { band_1: 5, band_2: 5, band_3: 3, band_4: -1.5, band_5: -2, band_6: -2, band_7: -3, band_8: 1.5, band_9: 2, band_10: 2 },
        podcast: { band_1: 2, band_2: 1.5, band_3: 1.5, band_4: -1, band_5: -1.5, band_6: -1.5, band_7: -2, band_8: 2.5, band_9: 1.5, band_10: 0 },
        bright: { band_1: 1, band_2: 1, band_3: 1, band_4: -0.5, band_5: -1, band_6: -1, band_7: -1.5, band_8: 3, band_9: 3, band_10: 3 },
        warm: { band_1: 6, band_2: 6, band_3: 4, band_4: -1, band_5: -1.5, band_6: -1.5, band_7: -2, band_8: 0.5, band_9: 1, band_10: 1 }
    };

    if (presets[preset]) {
        currentGains = { ...presets[preset] };
        // Set Q values to default
        bands.forEach(band => {
            if (!currentGains[`${band.id}_q`]) {
                currentGains[`${band.id}_q`] = 1.0;
            }
        });
        renderEQ();
        applyChanges();
        showStatus(`_${('Preset loaded')}`, 'success');
    }
}

function restorePipeWire() {
    if (confirm(_('Restart PipeWire? (audio will be interrupted for ~2 seconds)'))) {
        showStatus(_('Restarting PipeWire...'), 'info');
        fetch('/api/restart', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                showStatus(_('PipeWire restarted'), 'success');
            })
            .catch(error => {
                showStatus(`Error: ${error.message}`, 'error');
            });
    }
}

function showStatus(message, type) {
    const statusEl = document.getElementById('statusMessage');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    
    setTimeout(() => {
        statusEl.className = 'status-message';
    }, 3000);
}

// Check every 2 seconds if config has changed
function startConfigPolling() {
    configCheckInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/config-info');
            const data = await response.json();
            
            if (data.status === 'ok' && data.changed) {
                location.reload();
            }
        } catch (error) {
            // Silently ignore polling errors
        }
    }, 2000);
}

// Initialize on page load
window.addEventListener('load', initializeEQ);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (configCheckInterval) {
        clearInterval(configCheckInterval);
    }
});

// Translations mapping for JavaScript
const translations = {
    'en': {
        'Configuration loaded successfully': 'Configuration loaded successfully',
        'Error loading configuration': 'Error loading configuration',
        'Adjusting value (will save on release)': 'Adjusting value (will save on release)',
        'Saving changes...': 'Saving changes...',
        'Changes applied': 'Changes applied',
        'Error': 'Error',
        'Saving changes and restarting PipeWire...': 'Saving changes and restarting PipeWire...',
        'Reset all EQ values to default?': 'Reset all EQ values to default?',
        'Restore last backup?': 'Restore last backup?',
        'Preset loaded': 'Preset loaded',
        'Restart PipeWire? (audio will be interrupted for ~2 seconds)': 'Restart PipeWire? (audio will be interrupted for ~2 seconds)',
        'PipeWire restarted': 'PipeWire restarted',
        'Loading current configuration...': 'Loading current configuration...',
        'Gain (dB)': 'Gain (dB)',
        'Q (Width)': 'Q (Width)'
    },
    'de': {
        'Configuration loaded successfully': 'Konfiguration erfolgreich geladen',
        'Error loading configuration': 'Fehler beim Laden der Konfiguration',
        'Adjusting value (will save on release)': 'Wert wird angepasst (speichert beim Loslassen)',
        'Saving changes...': 'Speichere Änderungen...',
        'Changes applied': 'Änderungen angewendet',
        'Error': 'Fehler',
        'Saving changes and restarting PipeWire...': 'Speichere Änderungen und starte PipeWire neu...',
        'Reset all EQ values to default?': 'Alle EQ-Werte auf Standard zurücksetzen?',
        'Restore last backup?': 'Letztes Backup wiederherstellen?',
        'Preset loaded': 'Preset geladen',
        'Restart PipeWire? (audio will be interrupted for ~2 seconds)': 'PipeWire neu starten? (Audio wird für ~2 Sekunden unterbrochen)',
        'PipeWire restarted': 'PipeWire neu gestartet',
        'Loading current configuration...': 'Lade aktuelle Konfiguration...',
        'Gain (dB)': 'Verstärkung (dB)',
        'Q (Width)': 'Q (Breite)'
    }
};

// Get current language from HTML lang attribute
const currentLanguage = document.documentElement.lang || 'en';

function _(key) {
    return translations[currentLanguage]?.[key] || key;
}