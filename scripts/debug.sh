#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# Color output functions
log_info() { echo -e "\033[1;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[1;32m[SUCCESS]\033[0m $1"; }
log_error() { echo -e "\033[1;31m[ERROR]\033[0m $1"; }
log_warn() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v docker &>/dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker is not running. Please start Docker."
        exit 1
    fi

    if ! command -v python &>/dev/null; then
        log_error "Python not found. Please install Python 3.x."
        exit 1
    fi

    # Check required Python libraries
    if ! python -c "import boto3" 2>/dev/null; then
        log_warn "boto3 library not installed. Installing now..."
        pip install boto3 -q || {
            log_error "Failed to install boto3. Please run: pip install boto3"
            exit 1
        }
        log_success "boto3 installed successfully!"
    fi
}

# Service configuration
REDIS_NAME="redis-service"
MINIO_NAME="minio-service"
DJANGO_NAME="django-service"
DFDETECT_NAME="dfdetect-service"

# Port configuration
REDIS_PORT=6379
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
DJANGO_PORT=8000
DFDETECT_PORT=5555

# MinIO configuration
MINIO_USER="minioadmin"
MINIO_PASSWORD="minioadmin"
MINIO_BUCKET="purepost-media"

# Temporary directory path
TEMP_DIR="/tmp/debug-script-temp"

# Ensure service is stopped
ensure_service_stopped() {
    local service_name=$1
    if docker ps --format '{{.Names}}' | grep -q "^${service_name}$"; then
        log_info "Stopping running ${service_name}..."
        docker stop ${service_name} >/dev/null
    fi
}

# Start Redis
start_redis() {
    ensure_service_stopped $REDIS_NAME

    log_info "Starting Redis service..."
    docker run --rm -d \
        --name $REDIS_NAME \
        -p $REDIS_PORT:6379 \
        redis:7 >/dev/null || {
        log_error "Failed to start Redis"
        return 1
    }
    log_success "Redis service started successfully! (Port: $REDIS_PORT)"
}

# Start MinIO
start_minio() {
    ensure_service_stopped $MINIO_NAME

    log_info "Starting MinIO service..."
    mkdir -p $TEMP_DIR/minio-data

    docker run --rm -d \
        --name $MINIO_NAME \
        -v $TEMP_DIR/minio-data:/data \
        -p $MINIO_API_PORT:9000 \
        -p $MINIO_CONSOLE_PORT:9001 \
        -e MINIO_ROOT_USER=$MINIO_USER \
        -e MINIO_ROOT_PASSWORD=$MINIO_PASSWORD \
        minio/minio server /data --console-address ":9001" >/dev/null || {
        log_error "Failed to start MinIO"
        return 1
    }

    log_success "MinIO service started successfully!"
    log_info "- API Port: $MINIO_API_PORT"
    log_info "- Console Port: $MINIO_CONSOLE_PORT"
    log_info "- Username: $MINIO_USER"
    log_info "- Password: $MINIO_PASSWORD"
    log_info "- Console URL: http://localhost:$MINIO_CONSOLE_PORT"

    # Wait for MinIO to be ready
    log_info "Waiting for MinIO to initialize..."
    for i in {1..10}; do
        if curl -s http://localhost:$MINIO_API_PORT/minio/health/ready >/dev/null; then
            break
        fi
        if [ $i -eq 10 ]; then
            log_error "MinIO startup timed out, please check service status"
            return 1
        fi
        sleep 1
        echo -n "."
    done
    echo

    # Create MinIO bucket
    ensure_minio_bucket
}

# Ensure MinIO bucket exists
ensure_minio_bucket() {
    log_info "Ensuring MinIO bucket '$MINIO_BUCKET' exists..."
    create_bucket_python
}

# Start DeepFake Detection Service
start_dfdetect() {
    ensure_service_stopped $DFDETECT_NAME

    local MODEL_DIR="./dfdetect_service/model"
    if [ ! -f "$MODEL_DIR/ResNet18.onnx" ] && [ ! -f "$MODEL_DIR/resnet_quantized.onnx" ]; then
        log_error "DeepFake detection model files not found in $MODEL_DIR"
        log_info "Please download model files from: https://drive.google.com/drive/folders/1RDpiDjiX9IyoV4Zk5HfDfTOQPadhZnHP?usp=sharing"
        return 1
    fi

    log_info "Starting DeepFake Detection service..."

    # Use Docker to run the FastAPI app
    docker run --rm -d \
        --name $DFDETECT_NAME \
        -p $DFDETECT_PORT:5555 \
        -v "$(pwd)/dfdetect_service/model:/app/model" \
        -w /app \
        --entrypoint uvicorn \
        $(docker build -q ./dfdetect_service) \
        app:app --host 0.0.0.0 --port 5555 --reload >/dev/null || {
        log_error "Failed to start DeepFake Detection service"
        return 1
    }

    log_success "DeepFake Detection service started successfully! (Port: $DFDETECT_PORT)"
    log_info "API URL: http://localhost:$DFDETECT_PORT/predict"
}

# Start Django
start_django() {
    log_info "Starting Django development server..."

    # Run Django server
    python manage.py runserver 0.0.0.0:$DJANGO_PORT || {
        log_error "Failed to start Django server"
        return 1
    }
}

# Create MinIO bucket using Python
create_bucket_python() {
    python -c "
import boto3
from botocore.client import Config
import json

try:
    s3 = boto3.client(
        's3',
        endpoint_url='http://localhost:$MINIO_API_PORT',
        aws_access_key_id='$MINIO_USER',
        aws_secret_access_key='$MINIO_PASSWORD',
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )
    
    # Try to list buckets
    buckets = s3.list_buckets()
    bucket_exists = False
    
    for bucket in buckets['Buckets']:
        if bucket['Name'] == '$MINIO_BUCKET':
            bucket_exists = True
            print(f\"Bucket '$MINIO_BUCKET' already exists\")
            break
    
    if not bucket_exists:
        s3.create_bucket(Bucket='$MINIO_BUCKET')
        print(f\"Created bucket: '$MINIO_BUCKET'\")
        
        # Set bucket policy to public-read
        policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Sid': 'PublicReadGetObject',
                'Effect': 'Allow',
                'Principal': '*',
                'Action': ['s3:GetObject'],
                'Resource': [f'arn:aws:s3:::$MINIO_BUCKET/*']
            }]
        }
        s3.put_bucket_policy(
            Bucket='$MINIO_BUCKET',
            Policy=json.dumps(policy)
        )
        print(f\"Set '$MINIO_BUCKET' to public-read access\")
except Exception as e:
    print(f\"Error: {str(e)}\")
    exit(1)
" || {
        log_error "Failed to create MinIO bucket"
        return 1
    }
}

# Stop all services
stop_services() {
    log_info "Stopping all services..."
    docker stop $REDIS_NAME $MINIO_NAME $DFDETECT_NAME >/dev/null || {
        log_error "Failed to stop services"
        return 1
    }
    log_success "All services stopped"
}

# Check service status
check_status() {
    log_info "Checking running containers..."

    echo "-----------------------------------------"
    echo "| Service Name   | Status    | Ports     |"
    echo "-----------------------------------------"

    # Check Redis
    if docker ps --format '{{.Names}}' | grep -q "^${REDIS_NAME}$"; then
        echo "| Redis          | Running   | $REDIS_PORT    |"
    else
        echo "| Redis          | Stopped   | -         |"
    fi

    # Check MinIO
    if docker ps --format '{{.Names}}' | grep -q "^${MINIO_NAME}$"; then
        echo "| MinIO          | Running   | $MINIO_API_PORT,$MINIO_CONSOLE_PORT |"
    else
        echo "| MinIO          | Stopped   | -         |"
    fi

    # Check DeepFake Detection
    if docker ps --format '{{.Names}}' | grep -q "^${DFDETECT_NAME}$"; then
        echo "| DeepFake Detect  | Running   | $DFDETECT_PORT    |"
    else
        echo "| DeepFake Detect  | Stopped   | -         |"
    fi

    # Check Django (simple port check)
    if netstat -tuln 2>/dev/null | grep -q ":$DJANGO_PORT "; then
        echo "| Django         | Running   | $DJANGO_PORT    |"
    else
        echo "| Django         | Stopped   | -         |"
    fi

    echo "-----------------------------------------"
}

# Start all services in parallel
start_all_services() {
    log_info "Starting all services in parallel..."

    # Create temp directory
    mkdir -p $TEMP_DIR

    # Start Redis and MinIO in parallel
    start_redis &
    REDIS_PID=$!

    start_minio &
    MINIO_PID=$!

    # Start DeepFake Detection service in background
    start_dfdetect &
    DFDETECT_PID=$!

    # Wait for Redis and MinIO to start
    log_info "Waiting for services to initialize..."
    wait $REDIS_PID || {
        log_error "Redis startup failed"
        stop_services
        exit 1
    }

    wait $MINIO_PID || {
        log_error "MinIO startup failed"
        stop_services
        exit 1
    }

    wait $DFDETECT_PID || {
        log_error "DeepFake Detection service startup failed"
        stop_services
        exit 1
    }

    log_success "All background services started successfully!"
    log_info "Starting Django server in foreground..."

    # Start Django in foreground
    start_django
}

# Display help information
show_help() {
    echo "Usage: ./debug.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start      Start all services (Redis, MinIO, Django)"
    echo "  redis      Start only Redis service"
    echo "  minio      Start only MinIO service"
    echo "  dfdetect   Start only DeepFake Detection service"
    echo "  django     Start only Django server"
    echo "  stop       Stop all services"
    echo "  status     Check status of all services"
    echo "  bucket     Create MinIO bucket (without starting other services)"
    echo "  clean      Clean temporary data"
    echo "  help       Show this help message"
    echo ""
}

# Clean temporary data
clean_temp() {
    log_info "Cleaning temporary data..."
    rm -rf $TEMP_DIR
    log_success "Cleanup completed"
}

# Main logic
main() {
    check_dependencies

    case $1 in
    start)
        start_all_services
        ;;
    redis)
        start_redis
        ;;
    minio)
        start_minio
        ;;
    dfdetect)
        start_dfdetect
        ;;
    django)
        start_django
        ;;
    stop)
        stop_services
        ;;
    status)
        check_status
        ;;
    bucket)
        # If MinIO is not running, start temporary MinIO service
        if ! docker ps --format '{{.Names}}' | grep -q "^${MINIO_NAME}$"; then
            log_info "MinIO is not running. Starting temporary MinIO service..."
            start_minio
            log_info "Stopping temporary MinIO service..."
            docker stop $MINIO_NAME >/dev/null
        else
            create_bucket_python
        fi
        ;;
    clean)
        clean_temp
        ;;
    help | *)
        show_help
        ;;
    esac
}

# Execute main function
main "$@"
