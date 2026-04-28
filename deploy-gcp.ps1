# ByUs — Google Cloud Deployment Script (PowerShell)

$PROJECT_ID = gcloud config get-value project
if (-not $PROJECT_ID) {
    Write-Error "No GCP Project ID found. Please run 'gcloud init' first."
    exit
}

$REGION = "us-central1" # Change as needed
$SERVICE_NAME_BACKEND = "byus-backend"
$SERVICE_NAME_FRONTEND = "byus-frontend"

Write-Host "🚀 Starting deployment for Project: $PROJECT_ID" -ForegroundColor Cyan

# 1. Build and Deploy Backend
Write-Host "📦 Deploying Backend..." -ForegroundColor Yellow
cd backend
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME_BACKEND
gcloud run deploy $SERVICE_NAME_BACKEND `
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME_BACKEND `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --set-env-vars "GEMINI_API_KEY=YOUR_API_KEY_HERE"

# Get Backend URL
$BACKEND_URL = gcloud run services describe $SERVICE_NAME_BACKEND --platform managed --region $REGION --format 'value(status.url)'
Write-Host "✅ Backend deployed at: $BACKEND_URL" -ForegroundColor Green

# 2. Build and Deploy Frontend
Write-Host "📦 Deploying Frontend..." -ForegroundColor Yellow
cd ../frontend
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME_FRONTEND --build-arg VITE_API_URL=$BACKEND_URL
gcloud run deploy $SERVICE_NAME_FRONTEND `
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME_FRONTEND `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated

$FRONTEND_URL = gcloud run services describe $SERVICE_NAME_FRONTEND --platform managed --region $REGION --format 'value(status.url)'

Write-Host "🎉 Deployment Complete!" -ForegroundColor Green
Write-Host "--------------------------------------------------"
Write-Host "Frontend URL: $FRONTEND_URL" -ForegroundColor Cyan
Write-Host "Backend URL:  $BACKEND_URL" -ForegroundColor Cyan
Write-Host "--------------------------------------------------"
Write-Host "NOTE: Remember to update the GEMINI_API_KEY in the Cloud Run console or via gcloud if you haven't yet." -ForegroundColor Gray
cd ..
