Write-Host "Step 1/5: Stopping all containers with docker-compose down..."
docker-compose down

Write-Host "Step 2/5: Removing ChromaDB volume if it exists..."
docker volume rm rag-system_chroma-data 2>$null

Write-Host "Step 3/5: Starting containers with docker-compose up -d..."
docker-compose up -d

Write-Host "Step 4/5: Waiting 10 seconds for services to initialize..."
Start-Sleep -Seconds 10

Write-Host "Step 5/5: Checking container status with docker ps..."
docker ps
