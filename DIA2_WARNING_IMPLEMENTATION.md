# Dia2 Warning System Implementation

## Overview
Dia2 has been disabled by default and warning messages have been added to prevent users from accidentally using it for audiobook generation, as it is NOT designed for voice cloning.

## Changes Made

### 1. Backend: Disabled Dia2 by Default
**File**: `web-ui/app.py` (lines 84-94)

```python
# Register Dia2 provider (EXPERIMENTAL - NOT RECOMMENDED)
# Dia2 is designed for dialogue continuation, not voice cloning
# Voice cloning quality is poor compared to CosyVoice
# Only register if explicitly enabled
DIA2_ENABLED = False  # Set to True to enable Dia2 (not recommended)

if DIA2_ENABLED:
    try:
        from engine.providers.tts.dia2 import Dia2Provider
        ProviderRegistry.register_tts(Dia2Provider)
        print("⚠ WARNING: Dia2 enabled - voice cloning quality will be poor!")
    except ImportError as e:
        print(f"⚠ Warning: Could not load Dia2 provider: {e}")
```

**Result**: Dia2 will NOT appear in provider dropdowns unless `DIA2_ENABLED = True`

### 2. Frontend: Added Warnings to All Provider Dropdowns
**Files Modified**:
- `web-ui/static/app.js` (lines 167-180)
- `web-ui/static/project.js` (lines 296-309)

**Changes**:
1. Default to CosyVoice if no provider is selected
2. Add warning text to Dia2 option: "⚠️ NOT RECOMMENDED - Poor voice cloning"
3. Show alert dialog when Dia2 is selected

**Before**:
```javascript
function populateProviderDropdown(selectElement, selectedProvider = null) {
    selectElement.innerHTML = availableProviders.map(provider => `
        <option value="${provider.name}" ${provider.name === selectedProvider ? 'selected' : ''}>
            ${provider.display_name}
        </option>
    `).join('');
}
```

**After**:
```javascript
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
```

### 3. Frontend: Added Alert Dialog on Selection
**File**: `web-ui/static/project.js` (lines 797-809)

Added event listener for both:
1. **Modal TTS Provider** (individual chunk editing)
2. **Bulk TTS Provider** (bulk generation)

```javascript
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
```

Similar code was added for the bulk provider dropdown (lines 704-726).

## User Experience

### If Dia2 is Disabled (Default)
1. Dia2 will NOT appear in any provider dropdown
2. CosyVoice is the default provider
3. Users cannot accidentally select Dia2

### If Dia2 is Enabled (DIA2_ENABLED = True)
1. Dia2 appears in dropdowns with warning: "Dia2 ⚠️ NOT RECOMMENDED - Poor voice cloning"
2. When selected, shows alert:
   ```
   ⚠️ WARNING: Dia2 is NOT recommended for audiobook generation!

   Dia2 is designed for dialogue continuation, not voice cloning.
   Voice quality will be poor and unpredictable.

   Use CosyVoice instead for better results.
   ```
3. User must click "OK" to proceed (acknowledges the warning)

## Why Dia2 is Not Suitable

### Dia2 Design
- **Purpose**: Real-time dialogue continuation for conversational AI
- **Voice Cloning Method**: Uses prefix audio for "warmup" then trims it from output
- **Quality**: Random voices per generation, NOT voice cloning

### CosyVoice Design
- **Purpose**: Zero-shot voice cloning for TTS
- **Voice Cloning Method**: Analyzes seed audio and clones voice characteristics
- **Quality**: Excellent voice cloning consistency

### Comparison Results
| Metric | Dia2 | CosyVoice |
|--------|------|-----------|
| Voice Cloning Quality | Poor (random voices) | Excellent |
| Speed (CPU) | ~0.03x realtime (277s for 9s) | ~0.5x realtime |
| Consistency | Random per generation | Consistent |
| Sample Rate | 24kHz | 22.05kHz |
| Purpose | Dialogue continuation | Voice cloning |

## Testing

### To Test Warning System (Dia2 Disabled)
1. Start server: `python web-ui/app.py`
2. Open project page
3. Check provider dropdowns - Dia2 should NOT appear
4. CosyVoice should be selected by default

### To Test Warning System (Dia2 Enabled)
1. Set `DIA2_ENABLED = True` in `web-ui/app.py`
2. Restart server
3. Console should show: `⚠ WARNING: Dia2 enabled - voice cloning quality will be poor!`
4. Open project page
5. Provider dropdowns should show: "Dia2 ⚠️ NOT RECOMMENDED - Poor voice cloning"
6. Select Dia2 - alert dialog should appear
7. Click OK to dismiss

## Re-enabling Dia2 (Not Recommended)

If you absolutely need to enable Dia2 for testing:

1. Edit `web-ui/app.py`:
   ```python
   DIA2_ENABLED = True  # Enable Dia2
   ```

2. Restart the server

3. Warning will be displayed in console and UI

**IMPORTANT**: Dia2 will produce poor quality voice cloning compared to CosyVoice. Only enable for experimentation or if you understand the limitations.

## Summary

- ✅ Dia2 disabled by default
- ✅ CosyVoice is default provider
- ✅ Warning text added to Dia2 option (if enabled)
- ✅ Alert dialog shows when Dia2 is selected (if enabled)
- ✅ Applied to all provider dropdowns (modal + bulk)
- ✅ Code kept for future improvements or alternative use cases
- ✅ Clear documentation of why Dia2 is unsuitable
