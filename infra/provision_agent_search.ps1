param(
    [string]$ProjectId = "agentic-fleet-2026",
    [string]$Location = "global",
    [string]$DataStoreId = "duty-of-care-guidance"
)

$ErrorActionPreference = "Stop"
$token = (& gcloud auth print-access-token).Trim()
if (-not $token) { throw "gcloud did not return an access token" }
$headers = @{
    Authorization = "Bearer $token"
    "Content-Type" = "application/json"
    "X-Goog-User-Project" = $ProjectId
}
$collection = "projects/$ProjectId/locations/$Location/collections/default_collection"
$apiRoot = "https://discoveryengine.googleapis.com/v1"
$storeName = "$collection/dataStores/$DataStoreId"

try {
    Invoke-RestMethod -Uri "$apiRoot/$storeName" -Headers $headers -Method Get | Out-Null
    Write-Output "data store exists: $storeName"
} catch {
    if ([int]$_.Exception.Response.StatusCode -ne 404) { throw }
    $createBody = @{
        displayName = "Duty of Care approved guidance"
        industryVertical = "GENERIC"
        solutionTypes = @("SOLUTION_TYPE_SEARCH")
    } | ConvertTo-Json -Depth 5
    Invoke-RestMethod -Uri "${apiRoot}/${collection}/dataStores?dataStoreId=$DataStoreId" -Headers $headers -Method Post -Body $createBody | Out-Null
    $ready = $false
    for ($attempt = 0; $attempt -lt 60 -and -not $ready; $attempt++) {
        Start-Sleep -Seconds 3
        try {
            Invoke-RestMethod -Uri "$apiRoot/$storeName" -Headers $headers -Method Get | Out-Null
            $ready = $true
        } catch {
            $status = [int]$_.Exception.Response.StatusCode
            if ($status -notin @(404, 503)) { throw }
        }
    }
    if (-not $ready) { throw "data store did not become readable within three minutes" }
    Write-Output "created data store: $storeName"
}

$corpusPath = Join-Path (Split-Path $PSScriptRoot -Parent) "guidance\corpus.json"
$records = Get-Content -Raw -LiteralPath $corpusPath | ConvertFrom-Json
$branch = "$storeName/branches/default_branch"
foreach ($record in $records) {
    $documentId = $record.clause_id
    $payload = @{ structData = $record } | ConvertTo-Json -Depth 10
    try {
        Invoke-RestMethod -Uri "${apiRoot}/${branch}/documents?documentId=$documentId" -Headers $headers -Method Post -Body $payload | Out-Null
        Write-Output "created $documentId"
    } catch {
        if ([int]$_.Exception.Response.StatusCode -ne 409) { throw }
        $patchPayload = @{
            name = "$branch/documents/$documentId"
            structData = $record
        } | ConvertTo-Json -Depth 10
        Invoke-RestMethod -Uri "${apiRoot}/${branch}/documents/${documentId}?updateMask=struct_data" -Headers $headers -Method Patch -Body $patchPayload | Out-Null
        Write-Output "updated $documentId"
    }
}

Write-Output "Agent Search corpus provisioned without printing credentials."
