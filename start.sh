#!/bin/bash

# AI ChatBot - Quick Start Script
# This script helps you get the chatbot running quickly

set -e

echo "🤖 AI ChatBot - Quick Start"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from template..."
    cp config/.env.template .env
    print_warning "Please edit .env file and add your AI provider API key!"
    echo ""
    echo "Required: At least one of OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY"
    echo ""
    read -p "Press Enter to continue after editing .env file..."
fi

# Check for required tools
check_requirements() {
    print_status "Checking requirements..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    print_success "All requirements satisfied"
}

# Create necessary directories
create_directories() {
    print_status "Creating directories..."
    mkdir -p data/conversations
    mkdir -p logs
    print_success "Directories created"
}

# Start services
start_services() {
    print_status "Starting AI ChatBot services..."

    # Build and start containers
    docker compose up --build -d

    print_success "Services started!"
    echo ""
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔧 Backend API: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo ""
}

# Check service health
check_health() {
    print_status "Checking service health..."
    local timeout=60
    local interval=5
    local elapsed=0
    local backend_healthy=false
    local frontend_healthy=false

    while [ $elapsed -lt $timeout ]; do
        # Check backend health
        if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
            print_success "Backend is healthy"
            backend_healthy=true
        else
            print_warning "Backend not yet healthy..."
        fi

        # Check frontend health
        if curl -f http://localhost:3000 > /dev/null 2>&1; then
            print_success "Frontend is accessible"
            frontend_healthy=true
        else
            print_warning "Frontend not yet accessible..."
        fi

        if $backend_healthy && $frontend_healthy; then
            print_success "All services are healthy!"
            return 0
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    print_error "Services did not become healthy within the timeout period."
    return 1
}

# Show logs
show_logs() {
    echo ""
    print_status "Recent logs:"
    docker compose logs --tail=20
}

# Main execution
main() {
    check_requirements
    create_directories
    start_services
    check_health

    echo ""
    print_success "AI ChatBot is running!"
    echo ""
    echo "📖 Next steps:"
    echo "1. Open http://localhost:3000 in your browser"
    echo "2. Start chatting with the AI"
    echo "3. Try voice input by clicking the microphone button"
    echo ""
    echo "🔧 Management commands:"
    echo "- View logs: docker compose logs -f"
    echo "- Stop services: docker compose down"
    echo "- Restart: docker compose restart"
    echo ""

    # Ask if user wants to see logs
    read -p "Show live logs? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Showing live logs (Ctrl+C to exit)..."
        docker compose logs -f
    fi
}

# Handle script arguments
case "${1:-}" in
    "stop")
        print_status "Stopping AI ChatBot..."
        docker compose down
        print_success "Services stopped"
        ;;
    "restart")
        print_status "Restarting AI ChatBot..."
        docker compose restart
        print_success "Services restarted"
        ;;
    "logs")
        docker compose logs -f
        ;;
    "status")
        docker compose ps
        ;;
    "clean")
        print_warning "This will remove all containers and volumes for this project!"
        read -p "Are you sure? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose down -v --remove-orphans
            print_success "Cleanup completed"
        fi
        ;;
    "help"|"-h"|"--help")
        echo "AI ChatBot - Quick Start Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (no args)  Start the chatbot"
        echo "  stop       Stop all services"
        echo "  restart    Restart all services"
        echo "  logs       Show live logs"
        echo "  status     Show service status"
        echo "  clean      Remove all containers and data"
        echo "  help       Show this help"
        ;;
    *)
        main
        ;;
esac
