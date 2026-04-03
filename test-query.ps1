$body = '{"query": "What is the refund policy?"}'
$response = Invoke-RestMethod -Uri "http://localhost:8000/query" -Method POST -ContentType "application/json" -Body $body
$response | ConvertTo-Json -Depth 10
