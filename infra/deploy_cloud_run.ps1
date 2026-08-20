param(
    [string]$ProjectId = "agentic-fleet-2026",
    [string]$Region = "us-central1",
    [string]$Service = "duty-of-care-agent-backend",
    [string]$ServiceAccount = "duty-care-runtime@agentic-fleet-2026.iam.gserviceaccount.com",
    [string]$DataStore = "duty-of-care-guidance"
)

$ErrorActionPreference = "Stop"
$environment = "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT_ID=$ProjectId,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region,VERTEX_SEARCH_LOCATION=global,VERTEX_SEARCH_DATA_STORE=$DataStore,GEMINI_MODEL=gemini-2.5-flash"

gcloud run deploy $Service `
    --source . `
    --project $ProjectId `
    --region $Region `
    --service-account $ServiceAccount `
    --set-env-vars $environment `
    --allow-unauthenticated `
    --quiet

if ($LASTEXITCODE -ne 0) {
    throw "Cloud Run deployment failed."
}

Write-Output "Deployment completed without printing credentials."
