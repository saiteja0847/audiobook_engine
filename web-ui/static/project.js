/**
 * Audiobook Engine - Project Page JavaScript
 * ===========================================
 *
 * Handles project-specific functionality:
 * - Chunk management
 * - Generation controls
 * - Chunk editing modal
 */

// Global state
let projectData = null;
let allChunks = [];
let filteredChunks = [];
let selectedChunkIds = new Set();
let currentEditingChunk = null;
let statusPollInterval = null;

// Note: availableProviders and availableEffects are declared in app.js
// We access them as global variables here

/**
 * Load TTS providers
 */
async function loadProviders() {
    try {
        const data = await apiRequest('/providers/tts');
        availableProviders = data.providers || [];
    } catch (error) {
        console.error('Failed to load providers:', error);
        availableProviders = [];
    }
}

/**
 * Load audio effects
 */
async function loadEffects() {
    try {
        const data = await apiRequest('/effects');
        availableEffects = data.effects || [];
    } catch (error) {
        console.error('Failed to load effects:', error);
        availableEffects = [];
    }
}

/**
 * Load project data
 */
async function loadProject() {
    try {
        const data = await apiRequest(`/projects/${PROJECT_SLUG}`);
        projectData = data.project;
        allChunks = data.chunks || [];

        // Update UI
        document.getElementById('project-name').textContent = projectData.name || PROJECT_SLUG;
        updateStats(data);
        populateSpeakerFilter(allChunks);
        filteredChunks = allChunks;
        renderChunks();

        // Populate bulk generation settings
        populateBulkSettings();

        // Check if full audio exists
        checkFullAudioAvailability();

    } catch (error) {
        console.error('Failed to load project:', error);
    }
}

/**
 * Check if full audiobook exists and update UI
 */
async function checkFullAudioAvailability() {
    try {
        const response = await fetch(`${API_BASE}/projects/${PROJECT_SLUG}/audiobook/full.wav`, {
            method: 'HEAD'
        });

        const playerContainer = document.getElementById('full-audio-player-container');
        const placeholder = document.getElementById('full-audio-placeholder');
        const audioSource = document.getElementById('full-audio-source');
        const audioPlayer = document.getElementById('full-audio-player');

        if (response.ok) {
            // Full audio exists
            audioSource.src = `${API_BASE}/projects/${PROJECT_SLUG}/audiobook/full.wav?t=${Date.now()}`;
            audioPlayer.load();
            playerContainer.style.display = 'block';
            placeholder.style.display = 'none';
        } else {
            // Full audio doesn't exist
            playerContainer.style.display = 'none';
            placeholder.style.display = 'block';
        }
    } catch (error) {
        console.error('Failed to check full audio:', error);
        document.getElementById('full-audio-player-container').style.display = 'none';
        document.getElementById('full-audio-placeholder').style.display = 'block';
    }
}

/**
 * Rebuild full audiobook from available chunks
 */
async function rebuildFullAudio() {
    const rebuildBtn = document.getElementById('rebuild-full-audio');
    const statsSpan = document.getElementById('full-audio-stats');

    try {
        rebuildBtn.disabled = true;
        rebuildBtn.textContent = '🔄 Building...';

        const response = await apiRequest(`/projects/${PROJECT_SLUG}/audiobook/combine`, {
            method: 'POST'
        });

        if (response.success) {
            showNotification('Full audiobook rebuilt successfully!', 'success');

            // Update stats
            const stats = response.stats;
            statsSpan.textContent = `${stats.total_chunks} chunks • ${stats.duration_minutes} min • ${stats.file_size_mb} MB`;

            // Refresh audio player
            await checkFullAudioAvailability();
        } else {
            showNotification(response.error || 'Failed to rebuild audiobook', 'error');
        }
    } catch (error) {
        console.error('Failed to rebuild full audio:', error);
        showNotification('Failed to rebuild audiobook', 'error');
    } finally {
        rebuildBtn.disabled = false;
        rebuildBtn.textContent = '🔄 Rebuild';
    }
}

/**
 * Populate bulk generation settings dropdowns
 */
function populateBulkSettings() {
    // Populate bulk TTS provider
    const bulkProviderSelect = document.getElementById('bulk-tts-provider');
    if (bulkProviderSelect && availableProviders.length > 0) {
        // Default to CosyVoice (first provider if only one available)
        const defaultProvider = 'cosyvoice';

        bulkProviderSelect.innerHTML = availableProviders.map(provider => {
            const isDefault = provider.name === defaultProvider;
            const warning = provider.name === 'dia2' ? ' ⚠️ NOT RECOMMENDED - Poor voice cloning' : '';
            return `<option value="${provider.name}" ${isDefault ? 'selected' : ''}>${provider.display_name}${warning}</option>`;
        }).join('');

        // Add event listener to update inference methods and show warnings
        bulkProviderSelect.addEventListener('change', () => {
            const selectedProvider = bulkProviderSelect.value;
            updateBulkInferenceMethods(selectedProvider);

            // Show warning if Dia2 is selected
            if (selectedProvider === 'dia2') {
                alert('⚠️ WARNING: Dia2 is NOT recommended for audiobook generation!\n\n' +
                      'Dia2 is designed for dialogue continuation, not voice cloning.\n' +
                      'Voice quality will be poor and unpredictable.\n\n' +
                      'Use CosyVoice instead for better results.');
            }
        });

        // Initialize inference methods for default provider
        updateBulkInferenceMethods(bulkProviderSelect.value);
    }
}

/**
 * Update bulk inference methods based on selected provider
 */
function updateBulkInferenceMethods(providerName) {
    const provider = availableProviders.find(p => p.name === providerName);
    const methodSelect = document.getElementById('bulk-inference-method');

    if (!provider || !methodSelect) return;

    methodSelect.innerHTML = provider.methods.map(method => `
        <option value="${method}">${method}</option>
    `).join('');
}

/**
 * Update project statistics
 */
function updateStats(data) {
    const totalChunks = data.chunks?.length || 0;
    const audioCount = data.audio_count || 0;
    const duration = projectData.metadata?.total_duration || 0;
    const seedCount = data.seeds?.length || 0;

    document.getElementById('total-chunks').textContent = totalChunks;
    document.getElementById('generated-chunks').textContent = audioCount;
    document.getElementById('total-duration').textContent = formatDuration(duration);
    document.getElementById('voice-seeds').textContent = seedCount;
}

/**
 * Populate speaker filter dropdown
 */
function populateSpeakerFilter(chunks) {
    const speakers = [...new Set(chunks.map(c => c.speaker))];
    const select = document.getElementById('filter-speaker');

    select.innerHTML = '<option value="">All Speakers</option>' +
        speakers.map(speaker => `<option value="${speaker}">${speaker}</option>`).join('');
}

/**
 * Render chunks list
 */
function renderChunks() {
    const listElement = document.getElementById('chunks-list');

    if (filteredChunks.length === 0) {
        listElement.innerHTML = '<div class="empty-state">No chunks found</div>';
        return;
    }

    listElement.innerHTML = filteredChunks.map(chunk => {
        const chunkId = chunk.chunk_id || chunk.id;
        const isSelected = selectedChunkIds.has(chunkId);
        const hasAudio = chunk.has_audio; // Will be checked via audio endpoint

        return `
            <div class="chunk-card ${isSelected ? 'selected' : ''}" data-chunk-id="${chunkId}">
                <div class="chunk-header">
                    <label class="checkbox-label">
                        <input type="checkbox" class="chunk-select" data-chunk-id="${chunkId}" ${isSelected ? 'checked' : ''}>
                        <span class="chunk-number">#${chunkId}</span>
                    </label>
                    <div class="chunk-meta">
                        <span class="badge badge-speaker">${chunk.speaker}</span>
                        <span class="badge badge-type">${chunk.type || 'dialogue'}</span>
                        ${chunk.audio_effects?.length ? `<span class="badge badge-effects">${chunk.audio_effects.length} effects</span>` : ''}
                    </div>
                </div>

                <div class="chunk-text">${chunk.text}</div>

                <div class="chunk-footer">
                    <div class="chunk-config">
                        <span>TTS: ${chunk.tts_config?.provider || 'cosyvoice'}</span>
                        <span>Method: ${chunk.tts_config?.inference_method || 'auto'}</span>
                    </div>
                    <div class="chunk-actions">
                        <button class="btn btn-small btn-secondary play-chunk" data-chunk-id="${chunkId}" style="display: none;">▶️ Play</button>
                        <button class="btn btn-small edit-chunk" data-chunk-id="${chunkId}">Edit</button>
                        <button class="btn btn-small btn-success generate-chunk" data-chunk-id="${chunkId}">Generate</button>
                    </div>
                </div>
                <audio class="chunk-inline-audio" data-chunk-id="${chunkId}" style="display: none; margin-top: 0.5rem; width: 100%;" controls></audio>
            </div>
        `;
    }).join('');

    // Attach event listeners
    attachChunkEventListeners();

    // Check which chunks have audio
    checkChunksAudioAvailability();
}

/**
 * Attach event listeners to chunk elements
 */
function attachChunkEventListeners() {
    // Checkbox selection
    document.querySelectorAll('.chunk-select').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
            const chunkId = parseInt(e.target.dataset.chunkId);
            if (e.target.checked) {
                selectedChunkIds.add(chunkId);
            } else {
                selectedChunkIds.delete(chunkId);
            }
            updateSelectionUI();
        });
    });

    // Edit button
    document.querySelectorAll('.edit-chunk').forEach(button => {
        button.addEventListener('click', (e) => {
            const chunkId = parseInt(e.target.dataset.chunkId);
            openChunkModal(chunkId);
        });
    });

    // Play button
    document.querySelectorAll('.play-chunk').forEach(button => {
        button.addEventListener('click', (e) => {
            const chunkId = parseInt(e.target.dataset.chunkId);
            playChunkAudio(chunkId);
        });
    });

    // Generate button
    document.querySelectorAll('.generate-chunk').forEach(button => {
        button.addEventListener('click', (e) => {
            const chunkId = parseInt(e.target.dataset.chunkId);
            generateChunks([chunkId]);
        });
    });
}

/**
 * Update selection UI state
 */
function updateSelectionUI() {
    const generateButton = document.getElementById('generate-selected');
    generateButton.disabled = selectedChunkIds.size === 0;
    generateButton.textContent = `Generate Selected (${selectedChunkIds.size})`;

    // Update chunk cards
    document.querySelectorAll('.chunk-card').forEach(card => {
        const chunkId = parseInt(card.dataset.chunkId);
        if (selectedChunkIds.has(chunkId)) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });
}

/**
 * Apply filters
 */
function applyFilters() {
    const searchTerm = document.getElementById('search-chunks').value.toLowerCase();
    const speakerFilter = document.getElementById('filter-speaker').value;
    const typeFilter = document.getElementById('filter-type').value;
    const statusFilter = document.getElementById('filter-status').value;

    filteredChunks = allChunks.filter(chunk => {
        // Search filter
        if (searchTerm && !chunk.text.toLowerCase().includes(searchTerm)) {
            return false;
        }

        // Speaker filter
        if (speakerFilter && chunk.speaker !== speakerFilter) {
            return false;
        }

        // Type filter (check metadata.type)
        if (typeFilter) {
            const chunkType = chunk.metadata?.type || chunk.type;
            if (chunkType !== typeFilter) {
                return false;
            }
        }

        // Status filter (check if audio exists)
        if (statusFilter) {
            const chunkId = chunk.chunk_id || chunk.id;
            const hasAudio = document.querySelector(`.chunk-inline-audio[data-chunk-id="${chunkId}"]`) !== null;

            if (statusFilter === 'generated' && !hasAudio) {
                return false;
            }
            if (statusFilter === 'not-generated' && hasAudio) {
                return false;
            }
        }

        return true;
    });

    renderChunks();
}

/**
 * Populate TTS provider dropdown
 */
function populateProviderDropdown(selectElement, selectedProvider = null) {
    // Default to CosyVoice if no provider is selected
    const defaultProvider = selectedProvider || 'cosyvoice';

    selectElement.innerHTML = availableProviders.map(provider => {
        const isSelected = provider.name === defaultProvider;
        const warning = provider.name === 'dia2' ? ' ⚠️ NOT RECOMMENDED - Poor voice cloning' : '';
        return `
            <option value="${provider.name}" ${isSelected ? 'selected' : ''}>
                ${provider.display_name}${warning}
            </option>
        `;
    }).join('');
}

/**
 * Update inference methods based on selected provider
 */
function updateInferenceMethods(providerName, selectedMethod = null) {
    const provider = availableProviders.find(p => p.name === providerName);
    const methodSelect = document.getElementById('modal-inference-method');

    if (!provider || !methodSelect) return;

    methodSelect.innerHTML = provider.methods.map(method => `
        <option value="${method}" ${method === selectedMethod ? 'selected' : ''}>
            ${method}
        </option>
    `).join('');
}

/**
 * Get effects from UI
 */
function getEffectsFromUI() {
    const effectElements = document.querySelectorAll('#modal-effects .effect-item');
    const effects = [];

    effectElements.forEach(element => {
        const type = element.dataset.effectType;
        const params = {};

        element.querySelectorAll('input').forEach(input => {
            const paramName = input.dataset.param;
            params[paramName] = parseFloat(input.value);
        });

        effects.push({ type, params });
    });

    return effects;
}

/**
 * Create effect element HTML
 */
function createEffectElement(effect, index) {
    const effectInfo = availableEffects.find(e => e.name === effect.type);
    if (!effectInfo) return '';

    const paramInputs = Object.entries(effectInfo.parameters).map(([name, info]) => {
        const value = effect.params[name] !== undefined ? effect.params[name] : info.default;
        return `
            <div class="param-input">
                <label>${name}:</label>
                <input
                    type="number"
                    data-param="${name}"
                    value="${value}"
                    min="${info.min}"
                    max="${info.max}"
                    step="${info.step || 0.01}"
                >
                <span class="param-value">${value}</span>
            </div>
        `;
    }).join('');

    return `
        <div class="effect-item" data-effect-type="${effect.type}">
            <div class="effect-header">
                <strong>${effectInfo.display_name}</strong>
                <button class="remove-effect" data-index="${index}">×</button>
            </div>
            <div class="effect-params">
                ${paramInputs}
            </div>
        </div>
    `;
}

/**
 * Update parameter value display
 */
function updateParamValue(input) {
    const valueSpan = input.nextElementSibling;
    if (valueSpan) {
        valueSpan.textContent = input.value;
    }
}

/**
 * Open chunk edit modal
 */
function openChunkModal(chunkId) {
    const chunk = allChunks.find(c => (c.chunk_id || c.id) === chunkId);
    if (!chunk) return;

    currentEditingChunk = { ...chunk };

    // Populate modal
    document.getElementById('modal-chunk-id').textContent = chunkId;
    document.getElementById('modal-text').value = chunk.text;
    document.getElementById('modal-speaker').value = chunk.speaker;
    document.getElementById('modal-type').value = chunk.type || 'dialogue';

    // TTS config
    const ttsProvider = chunk.tts_config?.provider || 'cosyvoice';
    const inferenceMethod = chunk.tts_config?.inference_method || 'instruct2';
    const speed = chunk.tts_config?.speed || 1.0;

    populateProviderDropdown(document.getElementById('modal-tts-provider'), ttsProvider);
    updateInferenceMethods(ttsProvider, inferenceMethod);

    // Speed
    const modalSpeed = document.getElementById('modal-speed');
    const modalSpeedValue = document.getElementById('modal-speed-value');
    if (modalSpeed && modalSpeedValue) {
        modalSpeed.value = speed;
        modalSpeedValue.textContent = `${speed.toFixed(1)}x`;
    }

    // Emotion prompt
    document.getElementById('modal-emotion-prompt').value = chunk.emotion_prompt || '';

    // Populate effect selector
    const effectSelector = document.getElementById('effect-selector');
    effectSelector.innerHTML = availableEffects.map(effect => `
        <option value="${effect.name}">${effect.display_name}</option>
    `).join('');

    // Audio effects
    renderModalEffects(chunk.audio_effects || []);

    // Load audio if exists
    checkChunkAudio(chunkId);

    // Show modal
    document.getElementById('chunk-modal').style.display = 'flex';
}

/**
 * Close chunk modal
 */
function closeChunkModal() {
    document.getElementById('chunk-modal').style.display = 'none';
    currentEditingChunk = null;
}

/**
 * View book content
 */
async function viewBookContent() {
    try {
        const response = await fetch(`${API_BASE}/projects/${PROJECT_SLUG}`);
        const data = await response.json();

        // Try to read book.txt
        const bookPath = `projects/${PROJECT_SLUG}/book.txt`;
        const bookResponse = await fetch(`/${bookPath}`);

        if (bookResponse.ok) {
            const bookText = await bookResponse.text();
            document.getElementById('book-content').value = bookText;
            document.getElementById('book-modal').style.display = 'flex';
        } else {
            showNotification('Book content not found', 'error');
        }
    } catch (error) {
        console.error('Failed to load book content:', error);
        showNotification('Failed to load book content', 'error');
    }
}

/**
 * Close book modal
 */
function closeBookModal() {
    document.getElementById('book-modal').style.display = 'none';
}

/**
 * Render effects in modal
 */
function renderModalEffects(effects) {
    const container = document.getElementById('modal-effects');
    container.innerHTML = effects.map((effect, index) =>
        createEffectElement(effect, index)
    ).join('');

    // Attach effect parameter listeners
    container.querySelectorAll('input').forEach(input => {
        input.addEventListener('input', () => updateParamValue(input));
    });

    // Attach remove button listeners
    container.querySelectorAll('.remove-effect').forEach(button => {
        button.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            removeEffect(index);
        });
    });
}

/**
 * Add effect to modal
 */
function addEffect() {
    if (availableEffects.length === 0) {
        showNotification('No effects available', 'warning');
        return;
    }

    // Get selected effect from dropdown
    const effectSelector = document.getElementById('effect-selector');
    const selectedEffectName = effectSelector.value;
    const selectedEffect = availableEffects.find(e => e.name === selectedEffectName);

    if (!selectedEffect) return;

    const currentEffects = getEffectsFromUI();

    currentEffects.push({
        type: selectedEffect.name,
        params: Object.fromEntries(
            Object.entries(selectedEffect.parameters).map(([name, info]) => [name, info.default])
        )
    });

    renderModalEffects(currentEffects);
}

/**
 * Remove effect from modal
 */
function removeEffect(index) {
    const currentEffects = getEffectsFromUI();
    currentEffects.splice(index, 1);
    renderModalEffects(currentEffects);
}

/**
 * Save chunk changes
 */
async function saveChunkChanges(options = {}) {
    if (!currentEditingChunk) return;

    const chunkId = currentEditingChunk.chunk_id || currentEditingChunk.id;

    // Collect updated data
    const emotionPrompt = document.getElementById('modal-emotion-prompt').value.trim();

    const updatedChunk = {
        tts_config: {
            provider: document.getElementById('modal-tts-provider').value,
            inference_method: document.getElementById('modal-inference-method').value,
            speed: parseFloat(document.getElementById('modal-speed').value)
        },
        audio_effects: getEffectsFromUI(),
        emotion_prompt: emotionPrompt || null  // null if empty
    };

    try {
        await apiRequest(`/projects/${PROJECT_SLUG}/chunks/${chunkId}`, {
            method: 'PUT',
            body: JSON.stringify(updatedChunk)
        });

        // Update current chunk with saved data
        Object.assign(currentEditingChunk, updatedChunk);

        if (!options.skipNotification) {
            showNotification('Chunk updated successfully', 'success');
        }

        if (!options.keepModalOpen) {
            closeChunkModal();
            loadProject(); // Reload to reflect changes
        }

    } catch (error) {
        showNotification('Failed to update chunk', 'error');
        throw error; // Re-throw so generate button knows save failed
    }
}

/**
 * Check if chunk has audio
 */
async function checkChunkAudio(chunkId) {
    try {
        const response = await fetch(`${API_BASE}/projects/${PROJECT_SLUG}/chunks/${chunkId}/audio`);

        if (response.ok) {
            // Audio exists
            const audioPlayer = document.getElementById('modal-audio-player');
            const audio = document.getElementById('modal-audio');
            audio.src = `${API_BASE}/projects/${PROJECT_SLUG}/chunks/${chunkId}/audio`;
            audioPlayer.style.display = 'block';
        } else {
            document.getElementById('modal-audio-player').style.display = 'none';
        }
    } catch (error) {
        document.getElementById('modal-audio-player').style.display = 'none';
    }
}

/**
 * Check audio availability for all visible chunks
 */
async function checkChunksAudioAvailability() {
    for (const chunk of filteredChunks) {
        const chunkId = chunk.chunk_id || chunk.id;
        try {
            const response = await fetch(`${API_BASE}/projects/${PROJECT_SLUG}/chunks/${chunkId}/audio`);
            if (response.ok) {
                // Audio exists - show play button
                const playBtn = document.querySelector(`.play-chunk[data-chunk-id="${chunkId}"]`);
                if (playBtn) {
                    playBtn.style.display = 'inline-block';
                }
            }
        } catch (error) {
            // Audio doesn't exist - button stays hidden
        }
    }
}

/**
 * Play chunk audio inline
 */
function playChunkAudio(chunkId) {
    const audioElement = document.querySelector(`.chunk-inline-audio[data-chunk-id="${chunkId}"]`);
    const playBtn = document.querySelector(`.play-chunk[data-chunk-id="${chunkId}"]`);
    if (!audioElement || !playBtn) return;

    // Check if audio is already playing
    if (!audioElement.paused) {
        // Pause audio
        audioElement.pause();
        playBtn.textContent = '▶️ Play';
        return;
    }

    // Set source if not already set
    if (!audioElement.src || !audioElement.src.includes(`/chunks/${chunkId}/audio`)) {
        audioElement.src = `${API_BASE}/projects/${PROJECT_SLUG}/chunks/${chunkId}/audio`;
    }

    // Show player and play
    audioElement.style.display = 'block';
    audioElement.play();
    playBtn.textContent = '⏸️ Pause';

    // Update button when audio ends
    audioElement.addEventListener('ended', () => {
        playBtn.textContent = '▶️ Play';
    }, { once: true });

    // Update button if playback is paused externally
    audioElement.addEventListener('pause', () => {
        if (audioElement.currentTime < audioElement.duration) {
            playBtn.textContent = '▶️ Play';
        }
    }, { once: true });
}

/**
 * Generate chunks
 */
async function generateChunks(chunkIds = null, force = false) {
    const requestData = {
        force: force || document.getElementById('force-regenerate').checked
    };

    if (chunkIds) {
        requestData.chunks = chunkIds;
    }

    // Add bulk generation settings
    const bulkProvider = document.getElementById('bulk-tts-provider');
    const bulkMethod = document.getElementById('bulk-inference-method');
    const bulkSpeed = document.getElementById('bulk-speed');

    if (bulkProvider && bulkMethod) {
        requestData.default_provider = bulkProvider.value;
        requestData.default_method = bulkMethod.value;
    }

    if (bulkSpeed) {
        requestData.default_speed = parseFloat(bulkSpeed.value);
    }

    try {
        await apiRequest(`/projects/${PROJECT_SLUG}/generate`, {
            method: 'POST',
            body: JSON.stringify(requestData)
        });

        showNotification('Generation started', 'success');
        showProgressBar();

    } catch (error) {
        showNotification('Failed to start generation', 'error');
    }
}

/**
 * Show progress bar
 */
function showProgressBar() {
    document.getElementById('generation-progress').style.display = 'block';
}

/**
 * Hide progress bar
 */
function hideProgressBar() {
    document.getElementById('generation-progress').style.display = 'none';
}

/**
 * Update progress bar
 */
function updateProgress(status) {
    const fill = document.getElementById('progress-fill');
    const message = document.getElementById('progress-message');
    const percentage = document.getElementById('progress-percentage');

    fill.style.width = `${status.progress || 0}%`;
    percentage.textContent = `${status.progress || 0}%`;

    if (status.current_chunk) {
        message.textContent = `Generating chunk ${status.current_chunk}...`;
    } else if (status.status === 'completed') {
        message.textContent = 'Generation completed!';
        setTimeout(hideProgressBar, 3000);
        loadProject(); // Reload project data
        // Refresh audio availability for all chunks
        setTimeout(() => {
            checkChunksAudioAvailability();
            // Auto-rebuild full audio after generation
            rebuildFullAudio();
        }, 500);
    } else if (status.status === 'failed') {
        message.textContent = `Generation failed: ${status.error || 'Unknown error'}`;
        setTimeout(hideProgressBar, 5000);
    }
}

/**
 * Add log message to logger panel
 */
function addLogMessage(message, type = 'info') {
    const loggerOutput = document.getElementById('logger-output');
    const logLine = document.createElement('div');
    logLine.className = `log-line ${type}`;

    const timestamp = new Date().toLocaleTimeString();
    logLine.textContent = `[${timestamp}] ${message}`;

    loggerOutput.appendChild(logLine);

    // Auto-scroll to bottom
    loggerOutput.scrollTop = loggerOutput.scrollHeight;
}

/**
 * Poll generation status
 */
async function pollGenerationStatus() {
    try {
        const data = await apiRequest(`/projects/${PROJECT_SLUG}/generate/status`);

        if (data.status === 'in_progress') {
            updateProgress(data);

            // Add log messages
            if (data.current_chunk) {
                addLogMessage(`Generating chunk ${data.current_chunk}/${data.total_chunks}`, 'info');
            }
        } else if (data.status === 'completed') {
            updateProgress(data);
            addLogMessage(`Generation completed! Generated: ${data.generated}, Failed: ${data.failed}`, 'success');
        } else if (data.status === 'failed') {
            updateProgress(data);
            addLogMessage(`Generation failed: ${data.error || 'Unknown error'}`, 'error');
        }

    } catch (error) {
        console.error('Failed to poll status:', error);
    }
}

/**
 * Start status polling
 */
function startStatusPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
    }
    statusPollInterval = setInterval(pollGenerationStatus, 2000);
}

/**
 * Parse chunk range string (e.g., "1,2-10,18") into array of chunk IDs
 */
function parseChunkRange(rangeStr) {
    if (!rangeStr || !rangeStr.trim()) {
        return [];
    }

    const chunkIds = new Set();
    const parts = rangeStr.split(',').map(p => p.trim()).filter(p => p);

    for (const part of parts) {
        if (part.includes('-')) {
            // Range (e.g., "2-10")
            const [start, end] = part.split('-').map(n => parseInt(n.trim()));
            if (isNaN(start) || isNaN(end)) {
                showNotification(`Invalid range: ${part}`, 'error');
                continue;
            }
            for (let i = start; i <= end; i++) {
                chunkIds.add(i);
            }
        } else {
            // Single number (e.g., "1")
            const num = parseInt(part);
            if (isNaN(num)) {
                showNotification(`Invalid chunk number: ${part}`, 'error');
                continue;
            }
            chunkIds.add(num);
        }
    }

    return Array.from(chunkIds).sort((a, b) => a - b);
}

/**
 * Select chunks by range input
 */
function selectChunksByRange() {
    const rangeInput = document.getElementById('chunk-range-input');
    const rangeStr = rangeInput.value.trim();

    if (!rangeStr) {
        showNotification('Please enter chunk numbers or ranges', 'warning');
        return;
    }

    const chunkIds = parseChunkRange(rangeStr);

    if (chunkIds.length === 0) {
        showNotification('No valid chunk numbers found', 'error');
        return;
    }

    // Validate chunk IDs exist
    const validChunkIds = chunkIds.filter(id => allChunks.some(c => (c.chunk_id || c.id) === id));
    const invalidIds = chunkIds.filter(id => !allChunks.some(c => (c.chunk_id || c.id) === id));

    if (invalidIds.length > 0) {
        showNotification(`Warning: Chunks not found: ${invalidIds.join(', ')}`, 'warning');
    }

    if (validChunkIds.length === 0) {
        showNotification('No valid chunks to select', 'error');
        return;
    }

    // Select the chunks
    selectedChunkIds = new Set(validChunkIds);
    updateSelectionUI();

    // Update checkboxes
    document.querySelectorAll('.chunk-select').forEach(cb => {
        const chunkId = parseInt(cb.dataset.chunkId);
        cb.checked = selectedChunkIds.has(chunkId);
    });

    showNotification(`Selected ${validChunkIds.length} chunk(s)`, 'success');
}

/**
 * Generate chunks by range input
 */
async function generateChunksByRange() {
    const rangeInput = document.getElementById('chunk-range-input');
    const rangeStr = rangeInput.value.trim();

    if (!rangeStr) {
        showNotification('Please enter chunk numbers or ranges', 'warning');
        return;
    }

    const chunkIds = parseChunkRange(rangeStr);

    if (chunkIds.length === 0) {
        showNotification('No valid chunk numbers found', 'error');
        return;
    }

    // Validate chunk IDs exist
    const validChunkIds = chunkIds.filter(id => allChunks.some(c => (c.chunk_id || c.id) === id));
    const invalidIds = chunkIds.filter(id => !allChunks.some(c => (c.chunk_id || c.id) === id));

    if (invalidIds.length > 0) {
        showNotification(`Warning: Chunks not found: ${invalidIds.join(', ')}`, 'warning');
    }

    if (validChunkIds.length === 0) {
        showNotification('No valid chunks to generate', 'error');
        return;
    }

    // Generate the chunks
    await generateChunks(validChunkIds);
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Speed slider for bulk generation
    const bulkSpeed = document.getElementById('bulk-speed');
    const bulkSpeedValue = document.getElementById('bulk-speed-value');
    if (bulkSpeed && bulkSpeedValue) {
        bulkSpeed.addEventListener('input', (e) => {
            bulkSpeedValue.textContent = `${parseFloat(e.target.value).toFixed(1)}x`;
        });
    }

    // Speed slider for chunk modal
    const modalSpeed = document.getElementById('modal-speed');
    const modalSpeedValue = document.getElementById('modal-speed-value');
    if (modalSpeed && modalSpeedValue) {
        modalSpeed.addEventListener('input', (e) => {
            modalSpeedValue.textContent = `${parseFloat(e.target.value).toFixed(1)}x`;
        });
    }

    // Generation buttons
    document.getElementById('generate-all').addEventListener('click', () => {
        generateChunks();
    });

    document.getElementById('generate-selected').addEventListener('click', () => {
        generateChunks([...selectedChunkIds]);
    });

    // Selection buttons
    document.getElementById('select-all').addEventListener('click', () => {
        selectedChunkIds = new Set(filteredChunks.map(c => c.chunk_id || c.id));
        updateSelectionUI();
        document.querySelectorAll('.chunk-select').forEach(cb => cb.checked = true);
    });

    document.getElementById('deselect-all').addEventListener('click', () => {
        selectedChunkIds.clear();
        updateSelectionUI();
        document.querySelectorAll('.chunk-select').forEach(cb => cb.checked = false);
    });

    // Filters
    document.getElementById('search-chunks').addEventListener('input', applyFilters);
    document.getElementById('filter-speaker').addEventListener('change', applyFilters);
    document.getElementById('filter-type').addEventListener('change', applyFilters);
    document.getElementById('filter-status').addEventListener('change', applyFilters);

    // Chunk range buttons
    document.getElementById('select-by-range').addEventListener('click', selectChunksByRange);
    document.getElementById('generate-range').addEventListener('click', generateChunksByRange);

    // Full audio rebuild button
    document.getElementById('rebuild-full-audio').addEventListener('click', rebuildFullAudio);

    // Modal buttons
    document.querySelectorAll('.modal-close').forEach(button => {
        button.addEventListener('click', closeChunkModal);
    });

    document.getElementById('modal-save').addEventListener('click', saveChunkChanges);

    document.getElementById('modal-generate').addEventListener('click', async () => {
        if (currentEditingChunk) {
            const chunkId = currentEditingChunk.chunk_id || currentEditingChunk.id;

            // Save changes first (keep modal open, skip notification), then generate
            try {
                await saveChunkChanges({ keepModalOpen: true, skipNotification: true });
                // Now generate
                await generateChunks([chunkId], true);
                showNotification('Changes saved and generation started', 'success');
                closeChunkModal();
            } catch (error) {
                console.error('Failed to save and generate:', error);
                showNotification('Failed to save changes before generation', 'error');
            }
        }
    });

    document.getElementById('add-effect').addEventListener('click', addEffect);

    // TTS provider change - update inference methods
    document.getElementById('modal-tts-provider').addEventListener('change', (e) => {
        const selectedProvider = e.target.value;
        updateInferenceMethods(selectedProvider);

        // Show warning if Dia2 is selected
        if (selectedProvider === 'dia2') {
            alert('⚠️ WARNING: Dia2 is NOT recommended for audiobook generation!\n\n' +
                  'Dia2 is designed for dialogue continuation, not voice cloning.\n' +
                  'Voice quality will be poor and unpredictable.\n\n' +
                  'Use CosyVoice instead for better results.');
        }
    });

    // View book content button
    document.getElementById('view-book').addEventListener('click', viewBookContent);

    // Book modal close buttons
    document.querySelectorAll('.book-modal-close').forEach(button => {
        button.addEventListener('click', closeBookModal);
    });

    // Logger controls
    document.getElementById('show-logger').addEventListener('click', () => {
        document.getElementById('logger-panel').style.display = 'flex';
        document.getElementById('show-logger').style.display = 'none';
    });

    document.getElementById('toggle-logger').addEventListener('click', () => {
        document.getElementById('logger-panel').style.display = 'none';
        document.getElementById('show-logger').style.display = 'block';
    });

    document.getElementById('clear-logs').addEventListener('click', () => {
        document.getElementById('logger-output').innerHTML = '';
    });

    // Stop server button
    document.getElementById('stop-server').addEventListener('click', async () => {
        if (confirm('Are you sure you want to stop the server?')) {
            try {
                await fetch('/api/shutdown', { method: 'POST' });
                showNotification('Server shutting down...', 'info');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            } catch (error) {
                showNotification('Server stopped', 'info');
                setTimeout(() => {
                    window.location.href = '/';
                }, 2000);
            }
        }
    });

    // Close modals on background click
    document.getElementById('chunk-modal').addEventListener('click', (e) => {
        if (e.target.id === 'chunk-modal') {
            closeChunkModal();
        }
    });

    document.getElementById('book-modal').addEventListener('click', (e) => {
        if (e.target.id === 'book-modal') {
            closeBookModal();
        }
    });
}

/**
 * Initialize page
 */
async function init() {
    console.log('[Project] Initializing...');
    try {
        // Load providers and effects first
        console.log('[Project] Loading providers and effects...');
        await Promise.all([
            loadProviders(),
            loadEffects()
        ]);
        console.log('[Project] Providers and effects loaded');

        // Then load project data
        console.log('[Project] Loading project data...');
        await loadProject();
        console.log('[Project] Project data loaded');

        // Setup event listeners
        console.log('[Project] Setting up event listeners...');
        setupEventListeners();

        // Start status polling
        console.log('[Project] Starting status polling...');
        startStatusPolling();

        console.log('[Project] Initialization complete');
    } catch (error) {
        console.error('[Project] Initialization error:', error);
    }
}

// ===========================================================
// Tab Navigation
// ===========================================================

/**
 * Switch between tabs
 */
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Activate button
    const selectedBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (selectedBtn) {
        selectedBtn.classList.add('active');
    }

    // Load tab-specific content
    if (tabName === 'seeds') {
        loadSeeds();
    } else if (tabName === 'generation') {
        checkFullAudiobook();
    }
}

/**
 * Setup tab navigation listeners
 */
function setupTabListeners() {
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
}

// ===========================================================
// Seeds Tab Functions
// ===========================================================

let seedsData = [];

/**
 * Load seeds data
 */
async function loadSeeds() {
    try {
        const data = await apiRequest(`/projects/${PROJECT_SLUG}`);
        seedsData = data.seeds || [];

        // Extract unique characters
        const characters = new Set();
        seedsData.forEach(seed => {
            const char = seed.speaker || seed.character_name || seed.character;
            if (char) characters.add(char);
        });

        // Render character registry
        renderCharacters([...characters]);

        // Render seeds
        renderSeeds(seedsData);

    } catch (error) {
        console.error('Failed to load seeds:', error);
        document.getElementById('seeds-list').innerHTML = '<p class="error">Failed to load seeds</p>';
    }
}

/**
 * Render character registry
 */
function renderCharacters(characters) {
    const container = document.getElementById('characters-list');
    if (characters.length === 0) {
        container.innerHTML = '<p class="text-secondary">No characters found</p>';
        return;
    }

    container.innerHTML = characters.map(char => `
        <div class="character-card">
            <div class="character-name">${char}</div>
            <div class="character-stats">
                <span class="badge">
                    ${seedsData.filter(s => (s.speaker || s.character_name || s.character) === char).length} seed(s)
                </span>
            </div>
        </div>
    `).join('');
}

/**
 * Render seeds list
 */
function renderSeeds(seeds) {
    const container = document.getElementById('seeds-list');
    if (seeds.length === 0) {
        container.innerHTML = '<p class="text-secondary">No voice seeds found</p>';
        return;
    }

    container.innerHTML = seeds.map(seed => {
        const speakerName = seed.speaker || seed.character_name || seed.character || 'Unknown';
        const audioPath = seed.audio_path || seed.audio_file || seed.seed_file;
        const transcript = seed.prompt_text || seed.transcript || '';

        return `
            <div class="seed-card">
                <div class="seed-header">
                    <h4>${speakerName}</h4>
                    <div class="seed-actions">
                        ${audioPath ? `<button class="btn btn-small btn-secondary play-seed" data-speaker="${speakerName}" data-audio="${audioPath}">
                            ▶️ Play
                        </button>` : ''}
                        <button class="btn btn-small btn-secondary" disabled>🔄 Regenerate</button>
                    </div>
                </div>
                <div class="seed-info">
                    <p class="seed-transcript">${transcript.substring(0, 150)}${transcript.length > 150 ? '...' : ''}</p>
                    ${seed.metadata ? `
                        <div class="seed-meta">
                            ${seed.metadata.voice_source ? `<span class="badge">Source: ${seed.metadata.voice_source}</span>` : ''}
                            ${seed.metadata.duration_seconds ? `<span class="badge">Duration: ${seed.metadata.duration_seconds.toFixed(1)}s</span>` : ''}
                        </div>
                    ` : ''}
                </div>
                <audio class="seed-audio" data-speaker="${speakerName}" style="display: none;">
                    <source type="audio/wav">
                </audio>
            </div>
        `;
    }).join('');

    // Add event listeners for play buttons
    document.querySelectorAll('.play-seed').forEach(btn => {
        btn.addEventListener('click', () => {
            const speaker = btn.getAttribute('data-speaker');
            const audioFile = btn.getAttribute('data-audio');
            playSeedAudio(speaker, audioFile);
        });
    });
}

/**
 * Play seed audio
 */
function playSeedAudio(speaker, audioFile) {
    const audioElement = document.querySelector(`.seed-audio[data-speaker="${speaker}"]`);
    const playBtn = document.querySelector(`.play-seed[data-speaker="${speaker}"]`);
    if (!audioElement || !playBtn) return;

    // Check if audio is already playing
    if (!audioElement.paused) {
        // Pause audio
        audioElement.pause();
        playBtn.innerHTML = '▶️ Play';
        return;
    }

    const seedsDir = `${API_BASE}/projects/${PROJECT_SLUG}/seeds`;
    const audioUrl = `${seedsDir}/${speaker}/${audioFile}`;

    // Set source if not already set
    if (!audioElement.src || !audioElement.src.includes(audioUrl)) {
        audioElement.src = audioUrl;
    }

    // Show player and play
    audioElement.style.display = 'block';
    audioElement.play();
    playBtn.innerHTML = '⏸️ Pause';

    // Update button when audio ends
    audioElement.addEventListener('ended', () => {
        playBtn.innerHTML = '▶️ Play';
    }, { once: true });

    // Update button if playback is paused externally
    audioElement.addEventListener('pause', () => {
        if (audioElement.currentTime < audioElement.duration) {
            playBtn.innerHTML = '▶️ Play';
        }
    }, { once: true });
}

// ===========================================================
// Full Audiobook Playback
// ===========================================================

/**
 * Check if full audiobook exists
 */
async function checkFullAudiobook() {
    try {
        const response = await fetch(`${API_BASE}/projects/${PROJECT_SLUG}/audiobook/full.wav`);

        if (response.ok) {
            const audio = document.getElementById('full-audiobook-audio');
            audio.src = `${API_BASE}/projects/${PROJECT_SLUG}/audiobook/full.wav`;
            audio.style.display = 'block';

            document.querySelector('#full-audiobook-player p').style.display = 'none';
            document.getElementById('audiobook-info').style.display = 'block';
            document.getElementById('download-audiobook').style.display = 'block';

            // Get file info
            const blob = await response.blob();
            const size = (blob.size / (1024 * 1024)).toFixed(2);
            document.getElementById('full-size').textContent = `${size} MB`;
        } else {
            document.querySelector('#full-audiobook-player p').textContent = 'No full audiobook generated yet. Generate all chunks first.';
        }
    } catch (error) {
        console.error('Error checking full audiobook:', error);
    }
}

// Initialize when page loads
console.log('[Project] Script loaded, readyState:', document.readyState);
if (document.readyState === 'loading') {
    console.log('[Project] Waiting for DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', init);
} else {
    console.log('[Project] DOM already loaded, initializing immediately');
    init();
}

// Add tab listeners on load
document.addEventListener('DOMContentLoaded', () => {
    setupTabListeners();
});
