try {
    $containerNames = docker ps --format "{{.Names}}"

    if (-not $containerNames) {
        Write-Host "No running containers found."
        exit 1
    }

    $matches = $containerNames | Where-Object { $_ -match 'rag|backend' }

    if (-not $matches) {
        Write-Host "No running container names matched 'rag' or 'backend'."
        Write-Host "Available containers:"
        $containerNames | ForEach-Object { Write-Host "- $_" }
        exit 1
    }

    foreach ($name in $matches) {
        Write-Host "Copy-paste this command:"
        Write-Host "docker exec $name python -m src.ingestion"
    }
}
catch {
    Write-Host "Failed to inspect Docker containers: $($_.Exception.Message)"
    exit 1
}
