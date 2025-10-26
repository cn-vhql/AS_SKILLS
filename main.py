#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AS_SKILLS - 技能化AI助手
专业的技能化AI助手项目
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main_production import main as production_main

def main():
    """主入口函数"""
    try:
        asyncio.run(production_main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 程序发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()