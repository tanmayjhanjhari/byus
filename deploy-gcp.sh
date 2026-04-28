#!/bin/bash

# ByUs — Google Cloud Deployment Script (Bash)

PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No GCP Project ID found. Please run 'gcloud init' first."
    exit 1
fi

REGION="us-central1"
SERVICE_NAME_BACKEND="byus-backend"
SERVICE_NAME_FRONTEND="byus-frontend"

echo "🚀 Starting deployment for Project: $PROJECT_ID"

# 1. Build and Deploy Backend
echo "📦 Deploying Backend..."
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME_BACKEND
gcloud run deploy $SERVICE_NAME_BACKEND \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME_BACKEND \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated

# Get Backend URL
BACKEND_URL=$(gcloud run services describe $SERVICE_NAME_BACKEND --platform managed --region $REGION --format 'value(status.url)')
echo "✅ Backend deployed at: $BACKEND_URL"

# 2. Build and Deploy Frontend
echo "📦 Deploying Frontend..."
cd ../frontend
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME_FRONTEND --build-arg VITE_API_URL=$BACKEND_URL
gcloud run deploy $SERVICE_NAME_FRONTEND \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME_FRONTEND \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated

FRONTEND_URL=$(gcloud run services describe $SERVICE_NAME_FRONTEND --platform managed --region $REGION --format 'value(status.url)')

echo "🎉 Deployment Complete!"
echo "--------------------------------------------------"
echo "Frontend URL: $FRONTEND_URL"
echo "Backend URL:  $BACKEND_URL"
echo "--------------------------------------------------"
cd ..
