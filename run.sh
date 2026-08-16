#!/bin/bash

# Exit on error
set -e

echo "===== Dhanvantari AI Doctor Server Launcher ====="
echo "Step 1: Seeding database..."
python seed_data.py

echo "Step 2: Starting FastAPI app with Uvicorn..."
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
