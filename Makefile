# AWS CQRS Test - 開發工具統一介面
# 確保所有環境的代碼品質檢查一致性

.PHONY: help install precommit format lint test test-unit test-integration clean

# 預設目標
help: ## 顯示可用的命令
	@echo "AWS CQRS Test - 開發工具"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安裝所有依賴並設置 pre-commit hooks
	poetry install
	poetry run pre-commit install
	@echo "✅ 環境設置完成！"

precommit: ## 執行完整的 pre-commit 檢查 (與 CI 一致)
	poetry run python scripts.py
	@echo "🎉 Pre-commit 檢查完成！"

format: ## 自動格式化程式碼
	poetry run black --line-length=100 query-service/
	poetry run isort --profile=black --line-length=100 query-service/
	@echo "✨ 程式碼格式化完成！"

lint: ## 執行程式碼檢查 (不修改程式碼)
	poetry run black --check --line-length=100 query-service/
	poetry run isort --check-only --profile=black --line-length=100 query-service/
	poetry run flake8 query-service/ --max-line-length=100 --extend-ignore=E203,W503
	poetry run mypy query-service/ --ignore-missing-imports --disable-error-code=misc
	poetry run bandit -ll query-service/ --recursive
	@echo "✅ 程式碼檢查完成！"

test: ## 執行所有測試
	poetry run pytest query-service/tests/ -v

test-unit: ## 執行單元測試
	poetry run pytest -m unit --cov=query-service/eks_handler --cov-report=term --cov-report=html -v

test-integration: ## 執行整合測試 (需要 LocalStack)
	poetry run pytest -m integration -v

clean: ## 清理暫存檔案
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml 2>/dev/null || true
	@echo "🧹 清理完成！"

# CI 模擬
ci-lint: ## 模擬 CI 環境的 lint 檢查
	@echo "🔍 模擬 CI Lint 檢查..."
	poetry run black --check --line-length=100 query-service/
	poetry run isort --check-only --profile=black --line-length=100 query-service/
	poetry run flake8 query-service/ --max-line-length=100 --extend-ignore=E203,W503
	poetry run mypy query-service/ --ignore-missing-imports --disable-error-code=misc
	poetry run bandit -ll query-service/ --recursive --format json --output bandit-report.json || (cat bandit-report.json && exit 1)
	poetry run detect-secrets scan --baseline .secrets.baseline --force-use-all-plugins
	@echo "✅ CI Lint 檢查完成！"

ci-test: ## 模擬 CI 環境的測試
	@echo "🧪 模擬 CI 測試..."
	poetry run pytest -m unit --cov=query-service/eks_handler --cov-report=xml --cov-report=term -v
	@echo "✅ CI 測試完成！"

# 開發流程
dev-setup: install ## 完整的開發環境設置
	@echo "🚀 開發環境設置完成！現在可以開始編碼了。"
	@echo "💡 常用命令："
	@echo "   make precommit  # 提交前檢查"
	@echo "   make format     # 格式化程式碼"
	@echo "   make test       # 執行測試"

# 更新依賴
update: ## 更新所有依賴
	poetry update
	poetry run pre-commit autoupdate
	@echo "📦 依賴更新完成！"
