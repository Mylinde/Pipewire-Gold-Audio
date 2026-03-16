function _(msgid) {
    if (window.gettext && typeof window.gettext === 'function') {
        const result = window.gettext(msgid);
        // .log(`_('${msgid}') -> '${result}'`);
        return result;
    }
    // console.warn(`No translation for: ${msgid}`);
    return msgid;
}

const originalGains = {};
let currentGains = {};
let saveTimeout;
let currentConfig = null;
let configCheckInterval = null;
let bands = [];  // Global bands reference
let specialFilters = [];  // Global special filters reference

function getBands() {
    return [
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
}

async function initializeEQ() {
    try {
        bands = getBands();
        
        const response = await fetch('/api/gains');
        
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        
        currentGains = await response.json();
        Object.assign(originalGains, currentGains);
        
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('eqGrid').style.display = 'grid';
        document.getElementById('specialFiltersSection').style.display = 'block';
        document.getElementById('controlsSection').style.display = 'flex';
        
        renderEQ(bands);
        renderSpecialFilters();
        showStatus(_('Configuration loaded successfully'), 'success');
        startConfigPolling();
        
    } catch (error) {
        const bands = getBands();
        bands.forEach(band => {
            currentGains[`${band.id}`] = 0;
            currentGains[`${band.id}_q`] = 1.0;
        });
        
        Object.assign(originalGains, currentGains);
        
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('eqGrid').style.display = 'grid';
        document.getElementById('specialFiltersSection').style.display = 'block';
        document.getElementById('controlsSection').style.display = 'flex';
        
        renderEQ(bands);
        renderSpecialFilters();
        showStatus(`${_('Error loading configuration')}: ${error.message}`, 'error');
    }
}

function renderEQ(bands) {
    const grid = document.getElementById('eqGrid');
    grid.innerHTML = '';

    bands.forEach(band => {
        const gainValue = currentGains[band.id] || 0;
        const qValue = currentGains[`${band.id}_q`] || 1.0;
        
        const bandHtml = `
            <div class="eq-band">
                <div class="band-label">${_(band.label)}</div>
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

function renderSpecialFilters() {
    // console.log('renderSpecialFilters() called, window.gettext available:', !!window.gettext);
    
    specialFilters = [
        { id: 'eq_hp', label: _('High-Pass Filter'),
          controls: [
            { param: 'freq', label: _('Frequency (Hz)'), min: 20, max: 200, step: 1, default: 65, format: 'Hz' },
            { param: 'q', label: _('Q (Sharpness)'), min: 0.1, max: 10, step: 0.1, default: 0.3, format: 'number' }
          ],
          help: _('Removes low-frequency rumble and noise below the cutoff frequency.')
        },
        { id: 'de_esser', label: _('De-Esser'),
          controls: [
            { param: 'gain', label: _('Gain (dB)'), min: -12, max: 12, step: 0.1, default: -1.5, format: 'dB' },
            { param: 'q', label: _('Q (Width)'), min: 0.1, max: 10, step: 0.1, default: 2.0, format: 'number' }
          ],
          help: _('Reduces sibilance and harsh high-frequency sounds in vocals and speech.')
        },
        { id: 'final_gain', label: _('Final Gain'),
          controls: [
            { param: 'gain', label: _('Gain (Factor)'), min: 0.5, max: 2.0, step: 0.01, default: 1.15, format: 'factor' }
          ],
          help: _('Tip: Keep below 1.2 to avoid clipping.')
        },
        { id: 'soft_limiter', label: _('Soft Limiter'),
          controls: [
            { param: 'gain', label: _('Gain (dB)'), min: -3, max: 0, step: 0.1, default: -1.0, format: 'dB' },
            { param: 'q', label: _('Q (Response)'), min: 0.1, max: 2, step: 0.1, default: 0.7, format: 'number' }
          ],
          help: _('Protects from digital clipping at high frequencies.')
        }
    ];

    const container = document.getElementById('specialFiltersGrid');
    container.innerHTML = '';

    specialFilters.forEach(filter => {
        let controlsHtml = '';
        
        filter.controls.forEach(control => {
            const value = currentGains[`${filter.id}_${control.param}`];
            const displayedValue = value !== undefined ? value : control.default;
            
            let displayValue = '';
            
            if (control.format === 'Hz') {
                displayValue = `${parseFloat(displayedValue).toFixed(1)} Hz`;
            } else if (control.format === 'dB') {
                displayValue = `${parseFloat(displayedValue).toFixed(1)} dB`;
            } else if (control.format === 'factor') {
                const db = (20 * Math.log10(displayedValue)).toFixed(2);
                displayValue = `${displayedValue.toFixed(2)} (≈ ${db > 0 ? '+' : ''}${db} dB)`;
            } else {
                displayValue = `${parseFloat(displayedValue).toFixed(1)}`;
            }
            
            controlsHtml += `
                <div class="slider-label">${control.label}</div>
                <div class="slider-container">
                    <input type="range" 
                           id="sf_${filter.id}_${control.param}"
                           min="${control.min}" 
                           max="${control.max}" 
                           step="${control.step}" 
                           value="${displayedValue}"
                           oninput="onSpecialFilterChange('${filter.id}', '${control.param}')"
                           onmouseup="onSpecialFilterEnd('${filter.id}')"
                           ontouchend="onSpecialFilterEnd('${filter.id}')">
                    <div class="value-display" id="sf_value_${filter.id}_${control.param}">${displayValue}</div>
                </div>
            `;
        });
        
        let helpHtml = '';
        if (filter.help) {
            helpHtml = `<div class="eq-help-text">${filter.help}</div>`;
        }

        const filterHtml = `
            <div class="eq-band-special">
                <div class="band-label">${filter.label}</div>
                ${controlsHtml}
                ${helpHtml}
            </div>
        `;
        
        container.innerHTML += filterHtml;
    });
}

function onSpecialFilterChange(filterId, paramType) {
    const inputId = `sf_${filterId}_${paramType}`;
    const valueId = `sf_value_${filterId}_${paramType}`;
    const input = document.getElementById(inputId);
    const valueDisplay = document.getElementById(valueId);
    
    if (input && valueDisplay) {
        const value = parseFloat(input.value);
        currentGains[`${filterId}_${paramType}`] = value;
        
        // Find control format for display
        const filter = specialFilters.find(f => f.id === filterId);
        const control = filter.controls.find(c => c.param === paramType);
        
        if (control) {
            if (control.format === 'Hz') {
                valueDisplay.textContent = `${value.toFixed(1)} Hz`;
            } else if (control.format === 'dB') {
                valueDisplay.textContent = `${value.toFixed(1)} dB`;
            } else if (control.format === 'factor') {
                const db = (20 * Math.log10(value)).toFixed(2);
                valueDisplay.textContent = `${value.toFixed(2)} (≈ ${db > 0 ? '+' : ''}${db}dB)`;
            } else {
                valueDisplay.textContent = `${value.toFixed(1)}`;
            }
        }
    }
    
    showStatus(_('Adjusting value (will save on release)'), 'info');
}

function onSpecialFilterEnd(filterId) {
    showStatus(_('Saving changes...'), 'info');
    
    const data = {};
    
    // Only send values that have changed
    specialFilters.forEach(filter => {
        filter.controls.forEach(control => {
            const key = `${filter.id}_${control.param}`;
            const isQ = key.includes('_q');
            const currentValue = isQ ? Math.round(currentGains[key] * 100) / 100 : Math.round(currentGains[key] * 10) / 10;
            const originalValue = originalGains[key] !== undefined ? (isQ ? Math.round(originalGains[key] * 100) / 100 : Math.round(originalGains[key] * 10) / 10) : (isQ ? 1.0 : 0);
            if (currentValue !== originalValue) {
                data[key] = currentValue;
            }
        });
    });
    
    // If no changes, show message and return
    if (Object.keys(data).length === 0) {
        showStatus(_('No changes to save'), 'info');
        return;
    }
    
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
            // Update originalGains to reflect saved changes
            Object.assign(originalGains, data);
        } else {
            showStatus(`${result.message}`, 'error');
        }
    })
    .catch(error => showStatus(`Error: ${error.message}`, 'error'));
}

function updateValue(key, value) {
    currentGains[key] = parseFloat(value);
    document.getElementById(`value_${key}`).textContent = parseFloat(value).toFixed(1) + (key.includes('_q') ? '' : ' dB');
}

function onSliderInput(bandId) {
    const gainSlider = document.getElementById(`slider_${bandId}`);
    const valueDisplay = document.getElementById(`value_${bandId}`);
    if (gainSlider && valueDisplay) {
        valueDisplay.textContent = parseFloat(gainSlider.value).toFixed(1) + ' dB';
        currentGains[bandId] = parseFloat(gainSlider.value);
    }
    showStatus(_('Adjusting value (will save on release)'), 'info');
}

function onSliderEnd(bandId) {
    showStatus(_('Saving changes...'), 'info');
    
    const data = {};
    const currentBands = bands.length > 0 ? bands : getBands();
    
    // Only send values that have changed
    currentBands.forEach(band => {
        const gainSlider = document.getElementById(`slider_${band.id}`);
        const qSlider = document.getElementById(`slider_${band.id}_q`);
        
        // Check if gain changed
        if (gainSlider) {
            const currentValue = parseFloat(gainSlider.value);
            const originalValue = originalGains[band.id] !== undefined ? originalGains[band.id] : 0;
            if (Math.abs(currentValue - originalValue) > 0.01) {
                data[band.id] = currentValue;
            }
        }
        
        // Check if Q changed
        if (qSlider) {
            const currentValue = parseFloat(qSlider.value);
            const originalValue = originalGains[`${band.id}_q`] !== undefined ? originalGains[`${band.id}_q`] : 1.0;
            if (Math.abs(currentValue - originalValue) > 0.01) {
                data[`${band.id}_q`] = currentValue;
            }
        }
    });
    
    // If no changes, show message and return
    if (Object.keys(data).length === 0) {
        showStatus(_('No changes to save'), 'info');
        return;
    }
    
    // Check if backup is in progress before saving
    fetch('/api/backup-status')
    .then(r => r.json())
    .then(backupResult => {
        if (backupResult.backupInProgress) {
            showStatus(_('Backup in progress. Please wait before making changes.'), 'error');
            return;
        }
        
        data['_backup'] = true;
        data['_restart'] = true;
        
        fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(result => {
            if (result.status === 'ok' || result.status === 'partial') {
                showStatus(_('Changes applied, PipeWire restarted'), 'success');
                Object.assign(originalGains, data);
            } else if (result.status === 'error' && result.message && result.message.includes('Backup in progress')) {
                showStatus(_('Backup in progress. Please wait before making changes.'), 'error');
            } else {
                showStatus(`${result.message}`, 'error');
            }
        })
        .catch(error => showStatus(`Error: ${error.message}`, 'error'));
    })
    .catch(error => {
        console.error('Backup status check failed, continuing with update:', error);
        // Continue anyway if backup status check fails
        data['_backup'] = true;
        data['_restart'] = true;
        
        fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(r => r.json())
        .then(result => {
            if (result.status === 'ok' || result.status === 'partial') {
                showStatus(_('Changes applied, PipeWire restarted'), 'success');
                Object.assign(originalGains, data);
            } else if (result.status === 'error' && result.message && result.message.includes('Backup in progress')) {
                showStatus(_('Backup in progress. Please wait before making changes.'), 'error');
            } else {
                showStatus(`${result.message}`, 'error');
            }
        })
        .catch(error => showStatus(`Error: ${error.message}`, 'error'));
    });
}

function onQSliderChange(bandId) {
    const qSlider = document.getElementById(`slider_${bandId}_q`);
    const valueDisplay = document.getElementById(`value_${bandId}_q`);
    if (qSlider && valueDisplay) {
        valueDisplay.textContent = parseFloat(qSlider.value).toFixed(1);
        currentGains[`${bandId}_q`] = parseFloat(qSlider.value);
    }
    
    showStatus(_('Saving changes...'), 'info');
    
    clearTimeout(saveTimeout);
    saveTimeout = setTimeout(() => {
        saveChanges();
    }, 500);
}

async function saveChanges() {
    const data = {};
    const currentBands = bands.length > 0 ? bands : getBands();
    
    // Only send values that have changed
    currentBands.forEach(band => {
        const gainSlider = document.getElementById(`slider_${band.id}`);
        const qSlider = document.getElementById(`slider_${band.id}_q`);
        
        // Check if gain changed (round to 0.1 dB)
        if (gainSlider) {
            const currentValue = Math.round(parseFloat(gainSlider.value) * 10) / 10;
            const originalValue = originalGains[band.id] !== undefined ? Math.round(originalGains[band.id] * 10) / 10 : 0;
            if (currentValue !== originalValue) {
                data[band.id] = currentValue;
            }
        }
        
        // Check if Q changed (round to 0.02)
        if (qSlider) {
            const currentValue = Math.round(parseFloat(qSlider.value) * 100) / 100;
            const originalValue = originalGains[`${band.id}_q`] !== undefined ? Math.round(originalGains[`${band.id}_q`] * 100) / 100 : 1.0;
            if (currentValue !== originalValue) {
                data[`${band.id}_q`] = currentValue;
            }
        }
    });
    
    // If no changes, show message and return
    if (Object.keys(data).length === 0) {
        showStatus(_('No changes to save'), 'info');
        return;
    }
    
    data['_backup'] = true;
    data['_restart'] = true;
    
    try {
        const response = await fetch('/api/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.status === 'ok' || result.status === 'partial') {
            showStatus(_('Changes applied, restarting PipeWire...'), 'success');
            // Update originalGains to reflect saved changes
            Object.assign(originalGains, data);
            // Restart PipeWire to apply changes
            try {
                await fetch('/api/restart', { method: 'POST' });
            } catch (error) {
                console.error('Error restarting PipeWire:', error);
            }
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
        const data = {};
        
        // Only send values that have changed
        for (const key in currentGains) {
            const isQ = key.includes('_q');
            const currentValue = isQ ? Math.round(currentGains[key] * 100) / 100 : Math.round(currentGains[key] * 10) / 10;
            const originalValue = originalGains[key] !== undefined ? (isQ ? Math.round(originalGains[key] * 100) / 100 : Math.round(originalGains[key] * 10) / 10) : (isQ ? 1.0 : 0);
            if (currentValue !== originalValue) {
                data[key] = currentValue;
            }
        }
        
        // If no changes, still proceed with restart if requested
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
            // Update originalGains to reflect saved changes
            Object.assign(originalGains, data);
        } else {
            showStatus(`Error: ${result.message}`, 'error');
        }
    } catch (error) {
        showStatus(`Error saving changes: ${error.message}`, 'error');
    }
}

function resetAll() {
    if (confirm(_('Reset all values to default (0 dB)?'))) {
        showStatus(_('Resetting all values...'), 'info');
        
        const data = {};
        const currentBands = bands.length > 0 ? bands : getBands();
        
        // Set all bands to 0
        currentBands.forEach(band => {
            data[band.id] = 0;
            data[`${band.id}_q`] = 1.0;
            currentGains[band.id] = 0;
            currentGains[`${band.id}_q`] = 1.0;
        });
        
        // Reset special filters to defaults
        specialFilters.forEach(filter => {
            filter.controls.forEach(control => {
                data[`${filter.id}_${control.param}`] = control.default;
                currentGains[`${filter.id}_${control.param}`] = control.default;
            });
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
                showStatus(_('All values reset to default'), 'success');
                Object.assign(originalGains, data);
                renderEQ(getBands());
                renderSpecialFilters();
            } else {
                showStatus(`${result.message}`, 'error');
            }
        })
        .catch(error => showStatus(`Error: ${error.message}`, 'error'));
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
        const currentBands = bands.length > 0 ? bands : getBands();
        currentBands.forEach(band => {
            if (!currentGains[`${band.id}_q`]) {
                currentGains[`${band.id}_q`] = 1.0;
            }
        });
        renderEQ(getBands());
        renderSpecialFilters();
        saveChanges();
        showStatus(_('Preset loaded'), 'success');
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

async function loadBackups() {
    try {
        const response = await fetch('/api/backups');
        const data = await response.json();
        
        if (data.status === 'ok') {
            const backupsContainer = document.getElementById('backupsList');
            if (!backupsContainer) return;
            
            backupsContainer.innerHTML = '';
            
            if (data.backups.length === 0) {
                backupsContainer.innerHTML = `<p class="backup-empty">${_('No backups available')}</p>`;
                return;
            }
            
            // Sort backups by timestamp in descending order (newest first)
            const sortedBackups = data.backups.slice().sort((b, a) => {
                const dateA = new Date(a.timestamp);
                const dateB = new Date(b.timestamp);
                return dateB - dateA;
            });
            
            sortedBackups.forEach((backup, index) => {
                const backupEl = document.createElement('div');
                backupEl.className = 'backup-item';
                backupEl.innerHTML = `
                    <div class="backup-info">
                        <div class="backup-time">${backup.timestamp}</div>
                    </div>
                    <button class="btn-small" onclick="restoreSelectedBackup('${backup.filename}')" aria-label="${_('Restore')}">
                        <span class="material-icons-round" aria-hidden="true">restore</span>
                        ${_('Restore')}
                    </button>
                `;
                backupsContainer.appendChild(backupEl);
            });
        }
    } catch (error) {
        console.error('Error loading backups:', error);
        showStatus(`${_('Error loading backups')}: ${error.message}`, 'error');
    }
}

async function restoreSelectedBackup(filename) {
    if (confirm(_('Restore this backup? Current configuration will be backed up.'))) {
        showStatus(_('Restoring backup...'), 'info');
        
        try {
            const response = await fetch('/api/restore-backup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename: filename })
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showStatus(_('Backup restored successfully'), 'success');
                // Reload gains after restore
                setTimeout(() => reloadGains(), 1000);
                // Reload backup list
                await loadBackups();
            } else {
                showStatus(`${_('Error')}: ${result.message}`, 'error');
            }
        } catch (error) {
            showStatus(`${_('Error restoring backup')}: ${error.message}`, 'error');
        }
    }
}

function toggleBackupsPanel() {
    const panel = document.getElementById('backupsPanel');
    const button = document.querySelector('[onclick="toggleBackupsPanel()"]');
    
    if (panel && panel.classList.contains('closing')) {
        // Panel is closed, open it
        panel.classList.remove('closing');
        if (button) button.setAttribute('aria-expanded', 'true');
        loadBackups();
        // Scroll to the bottom of the page after loading content
        setTimeout(() => {
            const scrollHeight = Math.max(
                document.body.scrollHeight,
                document.documentElement.scrollHeight,
                document.body.offsetHeight,
                document.documentElement.offsetHeight
            );
            window.scrollTo({
                top: scrollHeight,
                behavior: 'smooth'
            });
        }, 300);
    } else if (panel) {
        // Panel is open, close it
        closeBackupsPanel();
    }
}

function closeBackupsPanel() {
    const panel = document.getElementById('backupsPanel');
    const button = document.querySelector('[onclick="toggleBackupsPanel()"]');
    
    if (panel) {
        panel.classList.add('closing');
        if (button) button.setAttribute('aria-expanded', 'false');
    }
}

async function reloadGains() {
    try {
        const response = await fetch('/api/gains');
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        
        const newGains = await response.json();
        Object.assign(currentGains, newGains);
        Object.assign(originalGains, newGains);
        
        renderEQ(getBands());
        renderSpecialFilters();
        showStatus(_('Configuration reloaded'), 'success');
    } catch (error) {
        console.error('Error reloading gains:', error);
    }
}

function startConfigPolling() {
    configCheckInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/config-info');
            const data = await response.json();
            
            if (data.status === 'ok' && data.changed) {
                // Reload gains instead of full page reload
                await reloadGains();
            }
        } catch (error) {
            // Silently ignore polling errors
        }
    }, 2000);
}

if (document.readyState === 'loading') {
    window.addEventListener('load', initializeEQ);
} else {
    initializeEQ();
}

window.addEventListener('beforeunload', () => {
    if (configCheckInterval) {
        clearInterval(configCheckInterval);
    }
});
