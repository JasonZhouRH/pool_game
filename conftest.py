"""让 pytest 能用 `from physics import ...` 形式导入本目录模块。"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
