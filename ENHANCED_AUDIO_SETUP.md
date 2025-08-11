# Enhanced Audio-to-Text Setup Guide

This document explains how to set up the enhanced audio-to-text functionality with improved recognition quality and support for multiple engines.

## New Features

### 🎯 **Improved Recognition Quality**
- **Smart chunking**: Audio is split into optimal chunks (30s by default) with overlap for better context
- **Silence detection**: Automatically detects natural speech pauses for better segmentation  
- **Multiple engines**: Supports Whisper (local), Google Speech Recognition, and Sphinx
- **Enhanced preprocessing**: Audio normalization, noise reduction, and speech enhancement filters

### 🔧 **Advanced Audio Processing**
- **Noise reduction**: Multiple levels (light, medium, strong, auto)
- **Speech enhancement**: Band-pass filtering for speech frequencies (300-3400 Hz)
- **Volume normalization**: Automatic gain adjustment
- **Format optimization**: Converts to optimal format (16kHz mono WAV) for recognition

### 📝 **Better Output**
- **Timestamp support**: Precise timing information for each segment
- **Post-processing**: Text cleanup, punctuation, capitalization
- **Language-specific fixes**: Russian and English text improvements
- **Detailed metadata**: Processing statistics and engine information

## Installation

### 1. Install Required Libraries

```bash
# Install enhanced audio processing libraries
pip install faster-whisper>=1.0.0
pip install speechrecognition>=3.10.0
pip install pydub>=0.25.1
pip install noisereduce>=3.0.0
pip install openai-whisper>=20240930
pip install scipy>=1.12.0
pip install numpy>=1.24.3
pip install librosa>=0.10.1
pip install soundfile>=0.12.1
```

### 2. System Dependencies

#### For Windows:
```bash
# Install FFmpeg (required for audio processing)
# Download from https://ffmpeg.org/download.html
# Add to PATH environment variable
```

#### For Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg portaudio19-dev python3-dev
```

#### For macOS:
```bash
brew install ffmpeg portaudio
```

### 3. Optional: Install Whisper Models

The system will automatically download models when first used, but you can pre-install them:

```python
# In Python shell
import whisper
whisper.load_model("base")  # Downloads base model (~140MB)
# Other options: tiny, small, medium, large
```

## API Usage

### Basic Request

```javascript
const formData = new FormData();
formData.append('audio', audioFile);
formData.append('engine', 'whisper');  // or 'google', 'sphinx'
formData.append('language', 'ru');  // or 'en', 'uk', etc.
formData.append('quality', 'high');

fetch('/api/audio-to-text/', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('Recognized text:', data.text);
    console.log('Segments:', data.segments);
});
```

### Advanced Settings

```javascript
const formData = new FormData();
formData.append('audio', audioFile);

// Engine settings
formData.append('engine', 'whisper');
formData.append('language', 'ru');
formData.append('quality', 'high');

// Processing settings  
formData.append('chunk_length', '30');  // seconds
formData.append('overlap', '2');  // seconds
formData.append('include_timestamps', 'true');

// Audio enhancement
formData.append('noise_reduction', 'auto');  // none, light, medium, strong, auto
formData.append('enable_normalization', 'true');
formData.append('enhance_speech', 'true');
formData.append('remove_silence', 'true');
formData.append('volume_gain', '120');  // percentage
```

## Response Format

```json
{
    "success": true,
    "text": "Полный распознанный текст с правильной пунктуацией.",
    "segments": [
        {
            "start": 0.0,
            "end": 3.2,
            "text": "Полный распознанный текст"
        },
        {
            "start": 3.2,
            "end": 5.8,
            "text": "с правильной пунктуацией."
        }
    ],
    "metadata": {
        "engine": "whisper",
        "language": "ru",
        "duration": 5.8,
        "file_size": 1024000,
        "processing_time": 2.3,
        "chunks_processed": 1,
        "segments_found": 2,
        "text_length": 45,
        "words_count": 6
    },
    "processing_details": {
        "chunk_length": 30,
        "overlap": 2,
        "normalization": true,
        "speech_enhancement": true,
        "noise_reduction": "auto",
        "silence_detection": true
    }
}
```

## Supported Formats

### Input Formats
- **Audio**: MP3, WAV, M4A, AAC, OGG, FLAC, WMA, OPUS
- **Video**: MP4, AVI, MOV (audio track will be extracted)

### Languages Supported
- **Russian**: `ru` or `ru-RU`
- **English**: `en` or `en-US`
- **Ukrainian**: `uk` or `uk-UA`
- **German**: `de` or `de-DE`
- **French**: `fr` or `fr-FR`
- **Spanish**: `es` or `es-ES`
- **Italian**: `it` or `it-IT`
- **Japanese**: `ja` or `ja-JP`
- **Korean**: `ko` or `ko-KR`
- **Chinese**: `zh` or `zh-CN`

## Engine Comparison

| Engine | Accuracy | Speed | Offline | Cost | Best For |
|--------|----------|-------|---------|------|----------|
| **Whisper** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ Yes | Free | High accuracy, multiple languages |
| **Google** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ No | Free* | Fast processing, good for short audio |
| **Sphinx** | ⭐⭐ | ⭐⭐⭐⭐ | ✅ Yes | Free | Offline backup, low accuracy |

*Google has usage limits

## Performance Tips

### 1. **Choose Optimal Chunk Size**
- **Short audio (< 2min)**: Use chunk_length=30, overlap=2
- **Medium audio (2-10min)**: Use chunk_length=45, overlap=3
- **Long audio (> 10min)**: Use chunk_length=60, overlap=5

### 2. **Audio Quality Optimization**
- **Clean audio**: Use noise_reduction="none" for faster processing
- **Noisy audio**: Use noise_reduction="strong" for better results
- **Mixed quality**: Use noise_reduction="auto" for automatic detection

### 3. **Engine Selection**
- **High accuracy needed**: Use engine="whisper"
- **Speed priority**: Use engine="google" (requires internet)
- **Offline processing**: Use engine="whisper" or "sphinx"

## Troubleshooting

### Common Issues

#### "Required libraries not available"
```bash
# Install missing libraries
pip install speechrecognition pydub numpy scipy
```

#### "Whisper model loading failed"
```bash
# Check disk space and internet connection
# Models are downloaded to ~/.cache/whisper/
```

#### "FFmpeg not found"
```bash
# Windows: Download FFmpeg and add to PATH
# Linux: sudo apt install ffmpeg
# macOS: brew install ffmpeg
```

#### "Audio file too large"
```bash
# Current limit is 500MB
# For larger files, compress first:
ffmpeg -i input.wav -c:a libmp3lame -b:a 128k output.mp3
```

### Performance Issues

#### Slow processing
- Reduce chunk_length to 15-20 seconds
- Disable noise_reduction or use "light"
- Use "google" engine for faster processing

#### Poor accuracy
- Increase chunk_length to 45-60 seconds
- Enable all enhancement options
- Use "whisper" engine with quality="high"
- Check if audio language matches the language parameter

## Integration Examples

### Frontend Integration

```html
<!-- Audio upload form -->
<form id="audioForm" enctype="multipart/form-data">
    <input type="file" id="audioFile" accept="audio/*,video/*">
    
    <select id="engine">
        <option value="whisper">Whisper (High Accuracy)</option>
        <option value="google">Google (Fast)</option>
    </select>
    
    <select id="language">
        <option value="ru">Russian</option>
        <option value="en">English</option>
    </select>
    
    <button type="submit">Recognize Speech</button>
</form>

<script>
document.getElementById('audioForm').onsubmit = async (e) => {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('audio', document.getElementById('audioFile').files[0]);
    formData.append('engine', document.getElementById('engine').value);
    formData.append('language', document.getElementById('language').value);
    formData.append('quality', 'high');
    formData.append('include_timestamps', 'true');
    formData.append('enhance_speech', 'true');
    
    try {
        const response = await fetch('/api/audio-to-text/', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('result').textContent = result.text;
            console.log('Processing details:', result.metadata);
        } else {
            console.error('Error:', result.error);
        }
    } catch (error) {
        console.error('Network error:', error);
    }
};
</script>
```

### Python Integration

```python
import requests

# Prepare audio file
with open('audio.mp3', 'rb') as f:
    files = {'audio': f}
    data = {
        'engine': 'whisper',
        'language': 'ru',
        'quality': 'high',
        'chunk_length': 30,
        'noise_reduction': 'auto',
        'enhance_speech': 'true'
    }
    
    response = requests.post(
        'http://localhost:8000/api/audio-to-text/',
        files=files,
        data=data
    )
    
    result = response.json()
    
    if result['success']:
        print("Text:", result['text'])
        print("Segments:", len(result['segments']))
        print("Processing time:", result['metadata']['processing_time'])
    else:
        print("Error:", result['error'])
```

## Advanced Configuration

### Custom Whisper Models

```python
# In settings.py or environment variables
WHISPER_MODEL = 'medium'  # tiny, base, small, medium, large
WHISPER_DEVICE = 'cpu'    # cpu, cuda
WHISPER_COMPUTE_TYPE = 'int8'  # int8, int16, float16, float32
```

### Audio Processing Parameters

```python
# Fine-tune audio processing
AUDIO_PREPROCESSING = {
    'normalize': True,
    'high_pass_filter': 300,    # Hz
    'low_pass_filter': 3400,    # Hz
    'min_silence_len': 1000,    # ms
    'silence_threshold': -40,   # dB
    'keep_silence': 500,        # ms
}
```

This enhanced audio-to-text system provides significantly better accuracy and flexibility compared to the basic implementation. The chunking approach ensures that even long audio files are processed effectively, while the multiple engine support provides fallback options and optimization for different use cases.
