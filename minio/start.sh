#!/bin/bash

# Load environment variables from .env file
set -a
source .env
set +a

# Create data directory if not exists
mkdir -p "${MINIO_STORAGE_LOCATION}"

# Pull latest images and start services
docker-compose pull
docker-compose up --remove-orphans -d

echo "Waiting for MinIO to be ready..."
sleep 5

# MinIO client command alias
mc='docker exec -it minio-client mc'

# Create additional console user and policy (optional)
echo "Creating console user..."
$mc admin user add minio/ ${MINIO_CONSOLE_USER} ${MINIO_CONSOLE_PASSWORD} || echo "User may already exist"

# Note: You can add custom policies here if needed
# $mc admin policy add minio/ consoleAdmin /root/.mc/admin.json
# $mc admin policy set minio consoleAdmin user=${MINIO_CONSOLE_USER}

echo "MinIO is ready!"
echo "API: http://localhost:${MINIO_PORT}"
echo "Console: http://localhost:${MINIO_CONSOLE_PORT}"
echo "Root User: ${MINIO_ROOT_USER}"


