#!/usr/bin/env python3
"""
檢查 pre-commit 和 CI 配置一致性的腳本
"""
import sys
from pathlib import Path

import yaml


def check_consistency():
    """檢查 pre-commit 和 CI 配置的一致性"""
    project_root = Path(__file__).parent.parent

    # 讀取 pre-commit 配置
    precommit_config = project_root / ".pre-commit-config.yaml"
    ci_config = project_root / ".github/workflows/ci.yml"

    if not precommit_config.exists():
        print("❌ .pre-commit-config.yaml 文件不存在")
        return False

    if not ci_config.exists():
        print("❌ CI 配置文件不存在")
        return False

    with open(precommit_config, "r", encoding="utf-8") as f:
        precommit_data = yaml.safe_load(f)

    with open(ci_config, "r", encoding="utf-8") as f:
        ci_data = yaml.safe_load(f)

    print("🔍 檢查 pre-commit 和 CI 配置一致性...")

    errors = []

    # 檢查 black 配置
    black_config = find_hook_config(precommit_data, "black")
    if black_config:
        line_length = extract_line_length(black_config.get("args", []))
        if line_length != "100":
            errors.append(f"❌ Black line-length 不一致: pre-commit={line_length}, 期望=100")
        else:
            print("✅ Black line-length 配置一致")

    # 檢查 isort 配置
    isort_config = find_hook_config(precommit_data, "isort")
    if isort_config:
        line_length = extract_line_length(isort_config.get("args", []))
        if line_length != "100":
            errors.append(f"❌ isort line-length 不一致: pre-commit={line_length}, 期望=100")
        else:
            print("✅ isort line-length 配置一致")

    # 檢查 flake8 配置
    flake8_config = find_hook_config(precommit_data, "flake8")
    if flake8_config:
        line_length = extract_max_line_length(flake8_config.get("args", []))
        if line_length != "100":
            errors.append(f"❌ flake8 max-line-length 不一致: pre-commit={line_length}, 期望=100")
        else:
            print("✅ flake8 max-line-length 配置一致")

    # 檢查 mypy 配置
    mypy_config = find_hook_config(precommit_data, "mypy")
    if mypy_config:
        args = mypy_config.get("args", [])
        if "--ignore-missing-imports" in args and "--disable-error-code=misc" in args:
            print("✅ MyPy 參數配置一致")
        else:
            errors.append("❌ MyPy 參數配置不一致")

    if errors:
        print("\n❌ 發現配置不一致:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✅ 所有配置檢查通過！pre-commit 和 CI 配置一致")
        return True


def find_hook_config(precommit_data, hook_name):
    """在 pre-commit 配置中找到指定的 hook 配置"""
    for repo in precommit_data.get("repos", []):
        for hook in repo.get("hooks", []):
            if hook.get("id") == hook_name:
                return hook
    return None


def extract_line_length(args):
    """從參數列表中提取 line-length 值"""
    for arg in args:
        if arg.startswith("--line-length="):
            return arg.split("=")[1]
    return None


def extract_max_line_length(args):
    """從參數列表中提取 max-line-length 值"""
    for arg in args:
        if arg.startswith("--max-line-length="):
            return arg.split("=")[1]
    return None


if __name__ == "__main__":
    success = check_consistency()
    sys.exit(0 if success else 1)
