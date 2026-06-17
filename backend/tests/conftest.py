"""Backend 测试共享配置。

环境前提：让 backend 测试用本地 framework（而非 venv site-packages 中
可能存在的旧 agent_framework copy）。pytest 自动加载本文件，
sys.path insert 在测试收集前生效。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "framework"))
