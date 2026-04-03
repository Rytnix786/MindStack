function Write-Status {
    param(
        [string]$Label,
        [bool]$Ok,
        [string]$Message
    )

    if ($Ok) {
        Write-Host "[OK] $Label: $Message" -ForegroundColor Green
    }
    else {
        Write-Host "[FAIL] $Label: $Message" -ForegroundColor Red
    }
}

Write-Host "Checking Docker Desktop status..."
try {
    $dockerProcesses = Get-Process | Where-Object {
        $_.ProcessName -match '^Docker' -or $_.ProcessName -match '^com\.docker'
    }

    if ($dockerProcesses) {
        Write-Status -Label "Docker Desktop" -Ok $true -Message "Running"
    }
    else {
        Write-Status -Label "Docker Desktop" -Ok $false -Message "Not running"
    }
}
catch {
    Write-Status -Label "Docker Desktop" -Ok $false -Message $_.Exception.Message
}

Write-Host "`nListing running containers..."
try {
    $containers = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        if ($containers) {
            Write-Host $containers
            Write-Status -Label "Docker containers" -Ok $true -Message "docker ps completed successfully"
        }
        else {
            Write-Status -Label "Docker containers" -Ok $true -Message "No running containers"
        }
    }
    else {
        throw "docker ps failed: $containers"
    }
}
catch {
    Write-Status -Label "Docker containers" -Ok $false -Message $_.Exception.Message
}

Write-Host "`nTesting health endpoint..."
try {
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10 -UseBasicParsing
    if ($healthResponse.StatusCode -eq 200) {
        Write-Status -Label "Health endpoint" -Ok $true -Message "http://localhost:8000/health responded with 200"
    }
    else {
        Write-Status -Label "Health endpoint" -Ok $false -Message "Unexpected status code $($healthResponse.StatusCode)"
    }
}
catch {
    Write-Status -Label "Health endpoint" -Ok $false -Message $_.Exception.Message
}

Write-Host "`nTesting metrics endpoint..."
try {
    $metricsResponse = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -Method Get -TimeoutSec 10 -UseBasicParsing
    if ($metricsResponse.StatusCode -eq 200) {
        Write-Status -Label "Metrics endpoint" -Ok $true -Message "http://localhost:8000/metrics responded with 200"
    }
    else {
        Write-Status -Label "Metrics endpoint" -Ok $false -Message "Unexpected status code $($metricsResponse.StatusCode)"
    }
}
catch {
    Write-Status -Label "Metrics endpoint" -Ok $false -Message $_.Exception.Message
}
