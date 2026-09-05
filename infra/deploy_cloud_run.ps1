param(
    [string]$ProjectId = "agentic-fleet-2026",
    [string]$Region = "us-central1",
    [string]$Service = "duty-of-care-agent-backend",
    [string]$ServiceAccount = "duty-care-runtime@agentic-fleet-2026.iam.gserviceaccount.com",
    [string]$DataStore = "duty-of-care-guidance",
    [string]$KeySecret = "duty-of-care-api-key-secret",
    [string]$ModelArmorTemplate = "projects/agentic-fleet-2026/locations/us-central1/templates/duty-of-care-agent-output",
    [string]$AgentEngineResource = $env:AGENT_ENGINE_RESOURCE,
    [int]$MinInstances = 1
)

$ErrorActionPreference = "Stop"
$environment = "GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT_ID=$ProjectId,GOOGLE_CLOUD_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region,VERTEX_SEARCH_LOCATION=global,VERTEX_SEARCH_DATA_STORE=$DataStore,GEMINI_MODEL=gemini-2.5-flash,MODEL_ARMOR_TEMPLATE=$ModelArmorTemplate"
if ($AgentEngineResource) {
    $environment = "$environment,AGENT_ENGINE_RESOURCE=$AgentEngineResource"
}

# The API-key signing secret is mounted from Secret Manager; it is never passed
# on the command line, printed, or committed. One warm instance keeps a judge's
# first click off a cold start during the judging window.
gcloud run deploy $Service `
    --source . `
    --project $ProjectId `
    --region $Region `
    --service-account $ServiceAccount `
    --set-env-vars $environment `
    --set-secrets "DUTY_OF_CARE_API_KEY_SECRET=${KeySecret}:latest" `
    --min-instances $MinInstances `
    --allow-unauthenticated `
    --quiet

if ($LASTEXITCODE -ne 0) {
    throw "Cloud Run deployment failed."
}

Write-Output "Deployment completed without printing credentials."
