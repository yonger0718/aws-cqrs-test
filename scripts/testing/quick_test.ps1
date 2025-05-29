# Quick Test Script for LocalStack Services
Write-Host "Quick LocalStack Test" -ForegroundColor Green
Write-Host "====================" -ForegroundColor Green

$AWS_ENDPOINT = "http://localhost:4566"
$EKS_ENDPOINT = "http://localhost:8000"

# Test 1: EKS Handler Health Check
Write-Host "`n1. Testing EKS Handler..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri $EKS_ENDPOINT -Method GET
    Write-Host "✅ EKS Handler OK" -ForegroundColor Green
    Write-Host $response -ForegroundColor Cyan
}
catch {
    Write-Host "❌ EKS Handler Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: LocalStack Health
Write-Host "`n2. Testing LocalStack..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$AWS_ENDPOINT/health" -Method GET
    Write-Host "✅ LocalStack OK" -ForegroundColor Green
    $response.services | Get-Member -MemberType NoteProperty | ForEach-Object {
        $serviceName = $_.Name
        $status = $response.services.$serviceName
        Write-Host "  $serviceName : $status" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "❌ LocalStack Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: DynamoDB Tables
Write-Host "`n3. Testing DynamoDB..." -ForegroundColor Yellow
$headers = @{
    "Content-Type" = "application/x-amz-json-1.0"
    "X-Amz-Target" = "DynamoDB_20120810.ListTables"
}
try {
    $response = Invoke-RestMethod -Uri $AWS_ENDPOINT -Method POST -Headers $headers -Body '{}'
    Write-Host "✅ DynamoDB OK" -ForegroundColor Green
    Write-Host "Tables:" -ForegroundColor Cyan
    $response.TableNames | ForEach-Object { Write-Host "  - $_" -ForegroundColor Cyan }
}
catch {
    Write-Host "❌ DynamoDB Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Query API
Write-Host "`n4. Testing Query API..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$EKS_ENDPOINT/query/user" -Method GET
    Write-Host "✅ Query API OK" -ForegroundColor Green
    Write-Host "Records count: $($response.count)" -ForegroundColor Cyan
}
catch {
    Write-Host "❌ Query API Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n✅ Quick test completed!" -ForegroundColor Green
Read-Host "Press Enter to exit" 