# Sound Effects Directory

This directory contains premium sound effects for the luxury desktop application.

## Required Files

### click.wav
- Soft metal click sound for button interactions
- Duration: ~100ms
- Format: WAV, 44.1kHz, 16-bit
- Volume: Soft, non-intrusive

### success.wav
- Premium success sound for payment completion
- Duration: ~200ms
- Format: WAV, 44.1kHz, 16-bit
- Volume: Pleasant, celebratory

## Implementation Notes

The application will work without these files - it falls back to system beeps if the sound files are not found.

## Production Setup

In production, add actual sound files here or modify the paths in `luxury_app.py` to point to your sound files.

## Fallback Behavior

- If sound files are missing: Uses `QApplication.beep()`
- If multimedia is not available: Silent operation
- User can toggle sounds in Settings menu

## Audio Guidelines

- Keep sounds subtle and professional
- Avoid loud or distracting audio
- Ensure consistent volume levels
- Test on different systems
