# Ollama Setup for Suna Local AI

This guide will help you set up Ollama models for local AI inference with Suna.

## Prerequisites

1. **Ollama must be running** - Either via Docker or native installation
2. **Suna backend must be configured** with `ENABLE_LOCAL_LLM=true`
3. **At least 8GB RAM** recommended for running models locally

## Quick Start

### Option 1: Docker Setup (Recommended)

1. **Start Ollama via Docker:**
```bash
docker-compose -f docker-compose.self-hosted.yml up ollama -d
```

2. **Run the setup script:**
```bash
# Make script executable (Windows/PowerShell)
# On Linux/Mac: chmod +x scripts/setup-ollama-models.sh

# Run setup
./scripts/setup-ollama-models.sh
```

### Option 2: Native Ollama Installation

1. **Install Ollama** from [ollama.ai](https://ollama.ai)
2. **Start Ollama service:**
```bash
ollama serve
```

3. **Run the setup script:**
```bash
./scripts/setup-ollama-models.sh
```

## Available Models

The setup script will install these recommended models:

### Core Models (Automatically installed)
- **Llama 3.2 (3B)** - Fast, efficient general-purpose model
- **Llama 3.1 (8B)** - Good balance of speed and capability
- **CodeLlama (7B)** - Specialized for coding tasks

### Optional Models (Install individually)
```bash
# General purpose
ollama pull mistral:7b

# Microsoft's Phi-3 model
ollama pull phi3:3.8b

# Larger code model
ollama pull codellama:13b

# Largest available model
ollama pull llama3.1:70b
```

## Model Recommendations

| Use Case | Recommended Model | Reasoning |
|----------|------------------|-----------|
| General Chat | `llama3.2:3b` | Fast responses, good quality |
| Code Generation | `codellama:7b` | Specialized for programming |
| Complex Reasoning | `llama3.1:8b` | Better reasoning capabilities |
| Maximum Quality | `llama3.1:70b` | Highest quality (requires more RAM) |

## Configuration

### Backend Configuration

Ensure your `.env` file includes:

```env
# Enable local LLM
ENABLE_LOCAL_LLM=true

# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434
ENABLE_LOCAL_EMBEDDINGS=false

# Model configuration
DEFAULT_LOCAL_MODELS='{
  "chat": "llama3.2:3b",
  "code": "codellama:7b",
  "reasoning": "llama3.1:8b"
}'
```

### Frontend Configuration

Set the environment to local mode:

```env
NEXT_PUBLIC_ENV_MODE=local
```

## Monitoring Models

### Check Available Models
```bash
ollama list
```

### Check Model Performance
```bash
curl http://localhost:8000/api/local-ai/models/{model_name}/performance
```

### Model Health Check
```bash
curl http://localhost:8000/api/local-ai/health
```

## Troubleshooting

### Common Issues

1. **"Model not available" error**
   - Check if Ollama is running: `curl http://localhost:11434/api/tags`
   - Pull the model: `ollama pull <model_name>`

2. **Slow responses**
   - Use smaller models like `llama3.2:3b`
   - Check RAM usage
   - Consider GPU acceleration

3. **Backend can't connect to Ollama**
   - Verify `OLLAMA_BASE_URL` in environment
   - Check Docker network if using containers

### Performance Tips

1. **Use GPU acceleration** (if available):
   - Ollama automatically detects GPU
   - Add GPU resources in docker-compose.yml

2. **Model caching**:
   - Models are cached locally after first pull
   - Multiple models can be loaded simultaneously

3. **Memory management**:
   - Smaller models use less RAM
   - Use `ollama stop <model>` to free memory

## API Usage

### List Available Models
```bash
curl http://localhost:8000/api/local-ai/models
```

### Test a Model
```bash
curl -X POST http://localhost:8000/api/local-ai/models/llama3.2:3b/test \
  -H "Content-Type: application/json"
```

### Pull a New Model
```bash
curl -X POST http://localhost:8000/api/local-ai/models/pull \
  -H "Content-Type: application/json" \
  -d '{"model_name": "mistral:7b"}'
```

## Security Considerations

- Local models run entirely on your hardware
- No data is sent to external AI providers
- Models are cached locally for privacy
- Consider firewall rules for Ollama API access

## Next Steps

1. **Test the models** in the Suna UI
2. **Monitor performance** and adjust model sizes as needed
3. **Experiment with different models** for your use cases
4. **Consider GPU acceleration** for better performance

## Support

If you encounter issues:

1. Check the Suna logs: `docker-compose logs backend`
2. Verify Ollama is accessible: `curl http://localhost:11434/api/tags`
3. Check model availability: `ollama list`
4. Review the troubleshooting section above

For additional support, check the Suna documentation or create an issue in the repository.


