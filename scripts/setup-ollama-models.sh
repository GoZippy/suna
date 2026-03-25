#!/bin/bash

# Suna Ollama Model Setup Script
# This script helps set up popular Ollama models for local inference

set -e

echo "🤖 Suna Ollama Model Setup"
echo "=========================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
    esac
}

# Check if Ollama is running
check_ollama() {
    print_status "INFO" "Checking if Ollama is running..."
    if ! curl -s http://localhost:11434/api/tags > /dev/null; then
        print_status "ERROR" "Ollama is not running. Please start Ollama first:"
        echo "  docker-compose -f docker-compose.self-hosted.yml up ollama -d"
        echo "  Or run: ollama serve"
        exit 1
    fi
    print_status "SUCCESS" "Ollama is running"
}

# Function to pull a model
pull_model() {
    local model_name=$1
    local display_name=$2

    print_status "INFO" "Pulling $display_name..."
    if ollama pull "$model_name" 2>/dev/null; then
        print_status "SUCCESS" "$display_name pulled successfully"
    else
        print_status "ERROR" "Failed to pull $display_name"
        return 1
    fi
}

# Main setup function
setup_models() {
    print_status "INFO" "Setting up recommended Ollama models for Suna..."

    # Quick and efficient models
    pull_model "llama3.2:3b" "Llama 3.2 (3B) - Fast and efficient"
    pull_model "llama3.1:8b" "Llama 3.1 (8B) - Good balance of speed and capability"

    # Code-focused models
    pull_model "codellama:7b" "CodeLlama (7B) - Great for coding tasks"

    # Alternative models
    echo ""
    print_status "INFO" "Optional models (run individually if needed):"
    echo "  ollama pull mistral:7b        # General purpose model"
    echo "  ollama pull phi3:3.8b         # Microsoft's Phi-3 model"
    echo "  ollama pull codellama:13b     # Larger code model"
    echo "  ollama pull llama3.1:70b      # Largest Llama model"

    echo ""
    print_status "SUCCESS" "Core models setup complete!"
    print_status "INFO" "You can now use local models in Suna"
    echo ""
    print_status "INFO" "Available models:"
    ollama list
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help          Show this help message"
    echo "  --setup         Setup recommended models (default)"
    echo "  --list          List available models"
    echo "  --pull MODEL    Pull a specific model"
    echo ""
    echo "Examples:"
    echo "  $0                           # Setup recommended models"
    echo "  $0 --list                    # List available models"
    echo "  $0 --pull llama3.2:3b       # Pull specific model"
}

# Parse command line arguments
case "${1:-}" in
    --help|-h)
        show_usage
        exit 0
        ;;
    --list|-l)
        print_status "INFO" "Available Ollama models:"
        ollama list
        exit 0
        ;;
    --pull|-p)
        if [ -z "$2" ]; then
            print_status "ERROR" "--pull requires a model name"
            show_usage
            exit 1
        fi
        check_ollama
        pull_model "$2" "$2"
        exit 0
        ;;
    --setup|"")
        check_ollama
        setup_models
        ;;
    *)
        print_status "ERROR" "Unknown option: $1"
        show_usage
        exit 1
        ;;
esac


