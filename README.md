# AS_SKILLS - 技能化AI助手

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![uv](https://img.shields.io/badge/uv-0.8+-purple.svg)](https://github.com/astral-sh/uv)

这是一个基于AgentScope框架AI助手应用，支持自动技能发现、智能任务匹配和终端交互，可以直接使用claudecode的skill文件。

## 🚀 特性

- **🤖 智能代理**: 基于AgentScope框架的ReAct代理
- **🔧 技能系统**: 自动技能发现和激活，兼容claudecode的skill文件
- **📊 多模态支持**: 支持文档处理、数据分析、Web测试等
- **⚡ 高性能**: 异步处理和并发执行
- **🛡️ 生产就绪**: 完整的错误处理和日志记录

## 📁 项目结构

```
AS_SKILLS/
├── src/                    # 核心源代码
│   ├── __init__.py
│   ├── config_loader.py
│   ├── skill_manager.py
│   ├── skilled_react_agent.py
│   └── main_production.py
├── config/                 # 配置文件
│   └── config.yaml
├── skills/                 # 技能模块
│   ├── algorithmic-art/
│   ├── artifacts-builder/
│   ├── brand-guidelines/
│   ├── canvas-design/
│   ├── document-skills/
│   ├── internal-comms/
│   ├── mcp-builder/
│   ├── skill-creator/
│   ├── slack-gif-creator/
│   ├── template-skill/
│   ├── theme-factory/
│   └── webapp-testing/
├── docs/                   # 文档
├── tests/                  # 测试
├── scripts/                # 工具脚本
├── logs/                   # 日志文件
├── data/                   # 数据文件
├── .venv/                  # 虚拟环境
├── .env                     # 环境变量
├── pyproject.toml           # 项目配置
├── requirements.txt          # 依赖列表
└── main.py                  # 主入口
```

## 🛠️ 环境要求

- Python 3.7+ (推荐 3.11)
- uv 包管理器
- DASHSCOPE_API_KEY 环境变量

## 📦 安装和运行

### 1. 克隆项目
```bash
git clone <repository-url>
cd AS_SKILLS
```

### 2. 设置环境
```bash
# 创建虚拟环境
uv venv

# 安装依赖
uv pip install -r requirements.txt

# 激活虚拟环境
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

### 3. 配置环境变量
创建 `.env` 文件：
```env
DASHSCOPE_API_KEY=your-api-key-here
```

### 4. 运行项目
```bash
# 开发模式
python main.py

# 或使用uv
uv run python main.py
```

## 🔧 技能模块（claudecode兼容）

项目包含14个专业技能模块(来自claudecode的skill文件)：

### 📊 数据分析
- **algorithmic-art**: 算法艺术生成
- **artifacts-builder**: 构建工具

### 🎨 设计工具
- **brand-guidelines**: 品牌指南
- **canvas-design**: 画布设计
- **theme-factory**: 主题工厂

### 📄 文档处理
- **document-skills**: 文档处理 (PDF/DOCX/PPTX/Excel)

### 🌐 Web技术
- **webapp-testing**: Web应用测试
- **mcp-builder**: MCP构建器

### 📢 通信工具
- **internal-comms**: 内部通信
- **slack-gif-creator**: Slack GIF创建器

### 🔧 开发工具
- **skill-creator**: 技能创建器
- **template-skill**: 模板技能

## 🎯 使用方法

### 基本对话
```bash
python main.py
```

### 技能操作
```bash
# 查看可用技能
/help

# 查看技能状态
/status

# 激活特定技能
/activate_skill <skill_name>
```

## 🧪 开发

### 运行测试
```bash
uv run pytest tests/
```

### 代码格式化
```bash
uv run black src/
```

### 类型检查
```bash
uv run mypy src/
```

## 📚 API文档

详细的API文档请参考：
- [AgentScope文档](https://agentscope.readthedocs.io/)
- [技能开发指南](skills/README.md)

## 🤝 贡献

欢迎提交Issue和Pull Request！

### 开发流程
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者！

---

**AS_SKILLS** - 让AI更智能，让工作更高效 🚀