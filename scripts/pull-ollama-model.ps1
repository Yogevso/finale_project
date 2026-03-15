# Pull the configured Ollama model into the running Ollama container.
# Usage: .\scripts\pull-ollama-model.ps1 [-Model "llama3.1:8b"]
param(
    [string]$Model = "llama3.1:8b",
    [string]$OllamaUrl = $env:OLLAMA_BASE_URL
)

if (-not $OllamaUrl) { $OllamaUrl = "http://localhost:11434" }

$MaxRetries = 3
$RetryDelay = 10

Write-Host "Pulling model '$Model' from Ollama at $OllamaUrl..."

for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
        $body = @{ name = $Model } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$OllamaUrl/api/pull" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 600
        Write-Host "Model '$Model' pulled successfully."
        exit 0
    } catch {
        Write-Warning "Attempt $i/$MaxRetries failed: $_"
        if ($i -lt $MaxRetries) {
            Write-Host "Retrying in ${RetryDelay}s..."
            Start-Sleep -Seconds $RetryDelay
        }
    }
}

Write-Error "Failed to pull model '$Model' after $MaxRetries attempts."
exit 1
