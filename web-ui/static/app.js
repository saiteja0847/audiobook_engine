/**
 * Audiobook Engine - Main JavaScript
 * ===================================
 *
 * Shared functions and utilities for the web UI.
 */

// API base URL
const API_BASE = '/api';

// Global state
let availableProviders = [];
let availableEffects = [];

/**
 * Make API request
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(API_BASE + url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Request failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Add to body
    document.body.appendChild(notification);

    // Trigger animation
    setTimeout(() => notification.classList.add('show'), 10);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Format duration (seconds to mm:ss)
 */
function formatDuration(seconds) {
    if (!seconds || isNaN(seconds)) return '-';

    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Load projects list
 */
async function loadProjects() {
    const listElement = document.getElementById('projects-list');

    try {
        listElement.innerHTML = '<div class="loading">Loading projects...</div>';

        const data = await apiRequest('/projects');
        const projects = data.projects || [];

        if (projects.length === 0) {
            listElement.innerHTML = '<div class="empty-state">No projects found</div>';
            return;
        }

        listElement.innerHTML = projects.map(project => `
            <div class="project-card">
                <h3>${project.name || project.slug}</h3>
                <div class="project-meta">
                    <span>Slug: ${project.slug}</span>
                    ${project.metadata ? `
                        <span>Chunks: ${project.metadata.total_chunks || 0}</span>
                        <span>Generated: ${project.metadata.generated_chunks || 0}</span>
                    ` : ''}
                </div>
                <a href="/project/${project.slug}" class="btn btn-primary">Open Project</a>
            </div>
        `).join('');

    } catch (error) {
        listElement.innerHTML = '<div class="error-state">Failed to load projects</div>';
    }
}

/**
 * Load TTS providers
 */
async function loadProviders() {
    const listElement = document.getElementById('providers-list');

    try {
        const data = await apiRequest('/providers/tts');
        availableProviders = data.providers || [];

        if (availableProviders.length === 0) {
            listElement.innerHTML = '<div class="empty-state-small">No providers</div>';
            return;
        }

        listElement.innerHTML = availableProviders.map(provider => `
            <div class="provider-item">
                <strong>${provider.display_name}</strong>
                <div class="provider-methods">${provider.methods.join(', ')}</div>
            </div>
        `).join('');

    } catch (error) {
        listElement.innerHTML = '<div class="error-state-small">Failed to load</div>';
    }
}

/**
 * Load audio effects
 */
async function loadEffects() {
    const listElement = document.getElementById('effects-list');

    try {
        const data = await apiRequest('/effects');
        availableEffects = data.effects || [];

        if (availableEffects.length === 0) {
            listElement.innerHTML = '<div class="empty-state-small">No effects</div>';
            return;
        }

        listElement.innerHTML = availableEffects.map(effect => `
            <div class="effect-item">
                <strong>${effect.display_name}</strong>
            </div>
        `).join('');

    } catch (error) {
        listElement.innerHTML = '<div class="error-state-small">Failed to load</div>';
    }
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
 * Create effect UI element
 */
function createEffectElement(effect, index) {
    const effectData = availableEffects.find(e => e.name === effect.type);
    if (!effectData) return '';

    const params = effect.params || {};

    return `
        <div class="effect-item-editable" data-index="${index}">
            <div class="effect-header">
                <strong>${effectData.display_name}</strong>
                <button class="btn-icon remove-effect" data-index="${index}">✕</button>
            </div>
            <div class="effect-params">
                ${Object.entries(effectData.parameters).map(([paramName, paramInfo]) => {
                    const value = params[paramName] ?? paramInfo.default;
                    return `
                        <div class="param-group">
                            <label>${paramName}</label>
                            <input
                                type="${paramInfo.type === 'int' ? 'number' : paramInfo.type === 'bool' ? 'checkbox' : 'range'}"
                                name="${paramName}"
                                value="${value}"
                                ${paramInfo.min !== undefined ? `min="${paramInfo.min}"` : ''}
                                ${paramInfo.max !== undefined ? `max="${paramInfo.max}"` : ''}
                                ${paramInfo.type === 'float' ? 'step="0.1"' : ''}
                                ${paramInfo.type === 'bool' && value ? 'checked' : ''}
                                data-effect-index="${index}"
                                data-param="${paramName}"
                            >
                            <span class="param-value">${value}</span>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

/**
 * Get current effects from UI
 */
function getEffectsFromUI() {
    const effectElements = document.querySelectorAll('.effect-item-editable');
    const effects = [];

    effectElements.forEach(el => {
        const index = el.dataset.index;
        const effectType = el.querySelector('strong').textContent;
        const effectData = availableEffects.find(e => e.display_name === effectType);

        if (!effectData) return;

        const params = {};
        el.querySelectorAll('input').forEach(input => {
            const paramName = input.dataset.param;
            if (input.type === 'checkbox') {
                params[paramName] = input.checked;
            } else if (input.type === 'number' || input.type === 'range') {
                params[paramName] = parseFloat(input.value);
            }
        });

        effects.push({
            type: effectData.name,
            params
        });
    });

    return effects;
}

/**
 * Update parameter value display
 */
function updateParamValue(input) {
    const valueSpan = input.parentElement.querySelector('.param-value');
    if (valueSpan) {
        valueSpan.textContent = input.type === 'checkbox' ? input.checked : input.value;
    }
}

/**
 * Stop the server
 */
async function stopServer() {
    if (!confirm('Are you sure you want to stop the server?')) {
        return;
    }

    try {
        await fetch(`${API_BASE}/shutdown`, {
            method: 'POST'
        });
        // Server will shut down, show message
        document.body.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; font-family: Arial, sans-serif;">
                <h1>Server Stopped</h1>
                <p>The audiobook engine server has been shut down successfully.</p>
                <p style="color: #666;">You can close this window now.</p>
            </div>
        `;
    } catch (error) {
        // Expected - server shuts down before responding
        setTimeout(() => {
            document.body.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100vh; flex-direction: column; font-family: Arial, sans-serif;">
                    <h1>Server Stopped</h1>
                    <p>The audiobook engine server has been shut down successfully.</p>
                    <p style="color: #666;">You can close this window now.</p>
                </div>
            `;
        }, 500);
    }
}

/**
 * Initialize event listeners
 */
function initEventListeners() {
    // Stop server button
    const stopButton = document.getElementById('stop-server');
    if (stopButton) {
        stopButton.addEventListener('click', stopServer);
    }

    // Refresh projects button
    const refreshButton = document.getElementById('refresh-projects');
    if (refreshButton) {
        refreshButton.addEventListener('click', loadProjects);
    }
}

// Initialize when page loads (only on homepage)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Only run on homepage (has projects-list element)
        if (document.getElementById('projects-list')) {
            loadProjects();
            loadProviders();
            loadEffects();
            initEventListeners();
        }
    });
} else {
    // Only run on homepage (has projects-list element)
    if (document.getElementById('projects-list')) {
        loadProjects();
        loadProviders();
        loadEffects();
        initEventListeners();
    }
}
