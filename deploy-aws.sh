#!/usr/bin/env bash
set -e

# GeoSight AWS EC2 deployment helper
# Run from the project root on Ubuntu/Amazon Linux with Docker installed.

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env. Edit it with your AWS bucket/region before continuing."
fi

echo "Building and starting GeoSight..."
docker compose up -d --build

echo "GeoSight is running. Check: http://YOUR_EC2_PUBLIC_IP/"
echo "Health check: http://YOUR_EC2_PUBLIC_IP/api/health"
