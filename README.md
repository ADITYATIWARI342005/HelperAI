# HelperAI - DeepSeek R1 MCQ Solver

A FastAPI-based MCQ solving application powered exclusively by the **deepseek-r1:70b-llama-distill-q4_K_M** model. The application processes images through OCR to extract text, then uses the AI model to solve multiple-choice questions with detailed explanations and step-by-step reasoning.

## Features

- **Single Model Architecture**: Uses only deepseek-r1:70b-llama-distill-q4_K_M for all text processing
- **Image Processing**: OCR-based text extraction with watermark removal capabilities
- **Mobile Connectivity**: QR code generation for easy mobile device connection via localhost/LAN
- **Auto-refresh**: Page refreshes every 45 seconds for continuous operation
- **Single Correct Answer**: Supports only single correct answer questions (no multi-correct)
- **Structured Output**: 
  - 2-line explanations above results
  - Detailed step-by-step reasoning below results
  - Complete thought process for freeform questions
- **Correct Answer Highlighting**: Automatically highlights correct options in green

## Architecture

- **Frontend**: HTML/CSS/JavaScript with responsive design for both desktop and mobile
- **Backend**: FastAPI with async processing
- **AI Model**: deepseek-r1:70b-llama-distill-q4_K_M via Ollama
- **Image Processing**: PaddleOCR for text extraction, OpenCV for preprocessing
- **Mobile Interface**: Dedicated mobile-optimized interface with camera support

## Installation

### Prerequisites

1. **Python 3.8+** installed on your system
2. **Ollama** installed and running locally
3. **Git** for cloning the repository

### Step 1: Install Ollama

Visit [ollama.ai](https://ollama.ai) and install Ollama for your operating system.

### Step 2: Pull the Required Model

```bash
ollama pull deepseek-r1:70b-llama-distill-q4_K_M
```

### Step 3: Clone and Setup the Project

```bash
git clone <your-repository-url>
cd HelperAI
```

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Start the Application

```bash
cd app
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at:
- **Desktop**: http://localhost:8000
- **Mobile**: http://YOUR_LOCAL_IP:8000/mobile
- **QR Code**: http://localhost:8000/qr

## Usage

### Desktop Interface
1. Open http://localhost:8000 in your browser
2. Enter question and options manually, or upload an image
3. Click "Get Answer" to process with the AI model
4. View results with explanations and reasoning

### Mobile Interface
1. Scan the QR code from http://localhost:8000/qr
2. Use camera or gallery to capture MCQ screenshots
3. Images are automatically processed through OCR
4. Results show parsed question/options and AI-generated answers

### Auto-refresh
- Enable auto-refresh for continuous operation (refreshes every 45 seconds)
- Useful for monitoring and continuous question processing

## File Structure

```
HelperAI/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application and routes
│   ├── models.py            # AI model interaction logic
│   ├── config.py            # Configuration management
│   ├── schemas.py           # Pydantic data models
│   └── ocr.py              # Image processing and OCR
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Configuration

### Model Configuration
The application uses a single configuration file (`app/config.py`) that can be modified to change the Ollama model:

```python
# In app/config.py, line 8
model: str = 'deepseek-r1:70b-llama-distill-q4_K_M'
```

### Changing the Ollama Model

To use a different Ollama model, you need to modify the following files:

#### 1. app/config.py
**Line 8**: Change the model name
```python
model: str = 'your-new-model-name'
```

#### 2. app/main.py
**Line 32**: Update the title and description
```python
app = FastAPI(title="HelperAI - Your Model MCQ Solver")
```

**Line 135**: Update the model display
```html
<strong>Model:</strong> your-new-model-name<br>
```

**Line 135**: Update the mobile interface model display
```html
<strong>Model:</strong> your-new-model-name<br>
```

#### 3. requirements.txt
Update if your new model requires different dependencies.

### Keep-Alive Settings
In `app/config.py`, line 9:
```python
keep_alive: str = '0'  # '0' unload asap, or durations like '10m'
```

## API Endpoints

- `GET /` - Desktop interface
- `GET /mobile` - Mobile interface
- `GET /qr` - QR code for mobile connection
- `POST /api/answer_text` - Process text-based MCQ questions
- `POST /api/answer_image` - Process image uploads with OCR
- `POST /api/answer_freeform` - Handle freeform questions
- `GET /config` - Get current configuration
- `GET /status` - System status and memory usage

## Mobile Connectivity

### Local Network Access
1. Ensure your phone and laptop are on the same WiFi network
2. Find your laptop's local IP address (displayed in the app)
3. Connect to http://YOUR_LOCAL_IP:8000/mobile

### QR Code Connection
1. Visit http://localhost:8000/qr on your laptop
2. Scan the generated QR code with your phone's camera
3. Open the link to access the mobile interface

## Troubleshooting

### Common Issues

1. **Model Not Found**: Ensure you've pulled the correct model with `ollama pull deepseek-r1:70b-llama-distill-q4_K_M`

2. **OCR Errors**: Check that PaddleOCR dependencies are properly installed

3. **Mobile Connection Issues**: Verify both devices are on the same network and firewall settings allow the connection

4. **Memory Issues**: The model requires significant RAM. Adjust `keep_alive` settings in config.py if needed.

### Performance Optimization

- Use `keep_alive: '0'` for minimal memory usage
- Adjust `num_predict` in models.py for faster/slower responses
- Monitor memory usage via the `/status` endpoint

## Development

### Adding New Features
- All model logic is centralized in `app/models.py`
- UI changes can be made in the HTML strings within `app/main.py`
- New endpoints can be added to the FastAPI app in `app/main.py`

### Testing
```bash
cd app
python -m pytest  # If you add tests
```

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
