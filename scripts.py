#!/usr/bin/env python3
"""
統一的預提交檢查腳本
確保手動執行、Git hook 和 CI 的一致性
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], cwd: Path = None) -> int:
    """執行命令並返回退出碼"""
    try:
        result = subprocess.run(cmd, cwd=cwd, check=False)
        return result.returncode
    except Exception as e:
        print(f"Error running command {' '.join(cmd)}: {e}")
        return 1


def run_precommit():
    """執行預提交檢查，與 .pre-commit-config.yaml 和 CI 保持一致"""
    root_dir = Path.cwd()
    query_service_dir = root_dir / "query-service"

    # 確保在正確的目錄中
    if not query_service_dir.exists():
        print("Error: query-service directory not found")
        return 1

    print("🔍 Running pre-commit checks...")
    print("=" * 50)

    exit_code = 0

    # 1. Black 格式化檢查
    print("1. Running Black formatter check...")
    cmd = ["poetry", "run", "black", "--check", "--line-length=100", "query-service/"]
    if run_command(cmd, root_dir) != 0:
        print("❌ Black formatting check failed")
        exit_code = 1
    else:
        print("✅ Black formatting check passed")

    # 2. isort import 排序檢查
    print("\n2. Running isort import checker...")
    cmd = ["poetry", "run", "isort", "--check-only", "--profile=black", "--line-length=100", "query-service/"]
    if run_command(cmd, root_dir) != 0:
        print("❌ isort import check failed")
        exit_code = 1
    else:
        print("✅ isort import check passed")

    # 3. Flake8 檢查
    print("\n3. Running Flake8 linter...")
    cmd = ["poetry", "run", "flake8", "query-service/", "--max-line-length=100", "--extend-ignore=E203,W503"]
    if run_command(cmd, root_dir) != 0:
        print("❌ Flake8 linting failed")
        exit_code = 1
    else:
        print("✅ Flake8 linting passed")

    # 4. MyPy 類型檢查
    print("\n4. Running MyPy type checker...")
    cmd = ["poetry", "run", "mypy", "query-service/", "--ignore-missing-imports", "--disable-error-code=misc"]
    if run_command(cmd, root_dir) != 0:
        print("❌ MyPy type check failed")
        exit_code = 1
    else:
        print("✅ MyPy type check passed")

    # 5. Bandit 安全檢查
    print("\n5. Running Bandit security checker...")
    cmd = ["poetry", "run", "bandit", "-ll", "query-service/", "--recursive"]
    if run_command(cmd, root_dir) != 0:
        print("❌ Bandit security check failed")
        exit_code = 1
    else:
        print("✅ Bandit security check passed")

    # 6. YAML 檢查
    print("\n6. Checking YAML files...")
    yaml_files = list(root_dir.glob("*.yml")) + list(root_dir.glob("*.yaml"))
    yaml_files = [f for f in yaml_files if '.mypy_cache' not in str(f)]

    if yaml_files:
        import yaml
        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    yaml.safe_load(f)
                print(f"✅ {yaml_file}")
            except Exception as e:
                print(f"❌ {yaml_file}: {e}")
                exit_code = 1

    # 7. JSON 檢查
    print("\n7. Checking JSON files...")
    json_files = list(root_dir.glob("*.json"))
    json_files = [f for f in json_files if '.mypy_cache' not in str(f)][:20]  # 限制數量

    if json_files:
        import json
        for json_file in json_files:
            try:
                with open(json_file) as f:
                    json.load(f)
                print(f"✅ {json_file}")
            except Exception as e:
                print(f"❌ {json_file}: {e}")
                exit_code = 1

    # 8. TOML 檢查
    print("\n8. Checking TOML files...")
    toml_files = list(root_dir.glob("*.toml"))

    if toml_files:
        try:
            import tomllib
            for toml_file in toml_files:
                try:
                    with open(toml_file, 'rb') as f:
                        tomllib.load(f)
                    print(f"✅ {toml_file}")
                except Exception as e:
                    print(f"❌ {toml_file}: {e}")
                    exit_code = 1
        except ImportError:
            # Python < 3.11
            try:
                import tomli as tomllib
                for toml_file in toml_files:
                    try:
                        with open(toml_file, 'rb') as f:
                            tomllib.load(f)
                        print(f"✅ {toml_file}")
                    except Exception as e:
                        print(f"❌ {toml_file}: {e}")
                        exit_code = 1
            except ImportError:
                print("⚠️  TOML check skipped (tomllib/tomli not available)")

    # 9. detect-secrets 檢查
    print("\n9. Running detect-secrets...")
    if (root_dir / ".secrets.baseline").exists():
        cmd = ["poetry", "run", "detect-secrets", "scan", "--baseline", ".secrets.baseline", "--force-use-all-plugins"]
        if run_command(cmd, root_dir) != 0:
            print("❌ detect-secrets check failed")
            exit_code = 1
        else:
            print("✅ detect-secrets check passed")
    else:
        print("⚠️  .secrets.baseline not found, skipping detect-secrets check")

    print("\n" + "=" * 50)
    if exit_code == 0:
        print("🎉 All pre-commit checks passed!")
    else:
        print("💥 Some pre-commit checks failed!")

    return exit_code


if __name__ == "__main__":
    sys.exit(run_precommit())
