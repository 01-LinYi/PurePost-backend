#!/bin/bash

if ! command -v docker &>/dev/null; then
    echo "Docker could not be found. Please install Docker."
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "Docker is not running. Please start Docker."
    exit 1
fi

# Service names
REDIS_NAME="redis-service"
MINIO_NAME="minio-service"
DJANGO_NAME="django-service"

# Ports
REDIS_PORT=6379
MINIO_API_PORT=9000
MINIO_CONSOLE_PORT=9001
DJANGO_PORT=8000

start_redis() {
    echo "Starting Redis service..."
    docker run --rm -d \
        --name $REDIS_NAME \
        -p $REDIS_PORT:6379 \
        redis:7 || {
        echo "Failed to start Redis"
        exit 1
    }
}

start_minio() {
    echo "Starting MinIO service..."
    docker run --rm -d \
        --name $MINIO_NAME \
        -p $MINIO_API_PORT:9000 \
        -p $MINIO_CONSOLE_PORT:9001 \
        -e MINIO_ROOT_USER=minioadmin \
        -e MINIO_ROOT_PASSWORD=minioadmin \
        minio/minio server /data --console-address ":9001" || {
        echo "Failed to start MinIO"
        exit 1
    }
}

start_django() {
    echo "Starting Django development server..."

    python manage.py runserver 0.0.0.0:$DJANGO_PORT || {
        echo "Failed to start Django server"
        exit 1
    }
}

stop_services() {
    echo "Stopping all services..."
    docker stop $REDIS_NAME $MINIO_NAME 2>/dev/null || true
}

check_status() {
    echo "Checking running containers..."
    docker ps
}

show_help() {
    echo "Usage: ./debug.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start      Start Redis, MinIO, and Django development server"
    echo "  stop       Stop all services"
    echo "  status     Check the status of running containers"
    echo ""
}

case $1 in
start)
    start_redis
    start_minio
    start_django
    ;;
stop)
    stop_services
    ;;
status)
    check_status
    ;;
*)
    show_help
    ;;
esac
