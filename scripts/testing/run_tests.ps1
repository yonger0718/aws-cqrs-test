# Query Service 測試執行腳本
# 支援單元測試、整合測試和覆蓋率報告

param(
    [Parameter(Mandatory = $false)]
    [string]$TestType = "all", # all, unit, integration, coverage

    [Parameter(Mandatory = $false)]
    [switch]$Verbose = $false,

    [Parameter(Mandatory = $false)]
    [switch]$InstallDeps = $false
)

Write-Host "🧪 Query Service 測試執行器" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

# 檢查 Python 版本
Write-Host "`n📌 檢查 Python 環境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "Python 版本: $pythonVersion"

# 安裝依賴（如果需要）
if ($InstallDeps) {
    Write-Host "`n📦 安裝測試依賴..." -ForegroundColor Yellow
    pip install -r requirements.txt
    pip install -r tests/requirements-test.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 依賴安裝失敗" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ 依賴安裝完成" -ForegroundColor Green
}

# 檢查服務狀態
function Check-Services {
    Write-Host "`n🔍 檢查服務狀態..." -ForegroundColor Yellow

    # 檢查 LocalStack
    try {
        $localstackHealth = Invoke-RestMethod -Uri "http://localhost:4566/_localstack/health" -Method Get
        Write-Host "✅ LocalStack: 運行中" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  LocalStack: 未運行 (整合測試將跳過)" -ForegroundColor Yellow
    }

    # 檢查 EKS Handler
    try {
        $eksHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
        Write-Host "✅ EKS Handler: 運行中" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  EKS Handler: 未運行 (部分測試將跳過)" -ForegroundColor Yellow
    }
}

# 執行單元測試
function Run-UnitTests {
    Write-Host "`n🚀 執行單元測試..." -ForegroundColor Cyan

    $testCommand = "pytest tests/test_eks_handler.py"
    if ($Verbose) {
        $testCommand += " -v -s"
    }

    Invoke-Expression $testCommand

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 單元測試通過" -ForegroundColor Green
    }
    else {
        Write-Host "❌ 單元測試失敗" -ForegroundColor Red
        exit 1
    }
}

# 執行整合測試
function Run-IntegrationTests {
    Write-Host "`n🚀 執行整合測試..." -ForegroundColor Cyan

    # 設定環境變數
    $env:LOCALSTACK_URL = "http://localhost:4566"
    $env:EKS_HANDLER_URL = "http://localhost:8000"

    $testCommand = "pytest tests/test_integration.py"
    if ($Verbose) {
        $testCommand += " -v -s"
    }

    Invoke-Expression $testCommand

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 整合測試通過" -ForegroundColor Green
    }
    else {
        Write-Host "❌ 整合測試失敗" -ForegroundColor Red
        exit 1
    }
}

# 執行覆蓋率測試
function Run-CoverageTests {
    Write-Host "`n📊 執行覆蓋率測試..." -ForegroundColor Cyan

    $coverageCommand = "pytest tests/ --cov=. --cov-report=html --cov-report=term"
    if ($Verbose) {
        $coverageCommand += " -v"
    }

    Invoke-Expression $coverageCommand

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ 覆蓋率測試完成" -ForegroundColor Green
        Write-Host "📄 HTML 報告已生成在 htmlcov/index.html" -ForegroundColor Yellow

        # 自動開啟報告（可選）
        $openReport = Read-Host "是否要開啟覆蓋率報告？(y/n)"
        if ($openReport -eq 'y') {
            Start-Process "htmlcov/index.html"
        }
    }
    else {
        Write-Host "❌ 覆蓋率測試失敗" -ForegroundColor Red
        exit 1
    }
}

# 主要執行邏輯
Check-Services

switch ($TestType) {
    "unit" {
        Run-UnitTests
    }
    "integration" {
        Run-IntegrationTests
    }
    "coverage" {
        Run-CoverageTests
    }
    "all" {
        Run-UnitTests
        Write-Host "`n" -NoNewline
        Run-IntegrationTests
        Write-Host "`n" -NoNewline
        Run-CoverageTests
    }
    default {
        Write-Host "❌ 無效的測試類型: $TestType" -ForegroundColor Red
        Write-Host "有效選項: all, unit, integration, coverage"
        exit 1
    }
}

Write-Host "`n✅ 測試執行完成！" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green

# 顯示測試摘要
Write-Host "`n📋 測試摘要:" -ForegroundColor Cyan
Write-Host "- Python 版本: $pythonVersion"
Write-Host "- 測試類型: $TestType"
Write-Host "- 詳細模式: $Verbose"
Write-Host "- 時間: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
