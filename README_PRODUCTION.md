# 生产级技能化AI助手

## 概述

这是一个基于AgentScope技能系统的生产级AI助手应用，支持自动技能发现、智能任务匹配和终端交互。兼容claudecode的skill文件，可以直接使用claudecode的skill文件。

## 特性

- ✅ **自动技能发现**: 自动扫描和加载skills目录中的所有技能
- 🧠 **智能技能匹配**: 根据用户输入自动推荐和激活相关技能
- 💬 **简洁终端界面**: 支持命令和对话两种交互模式
- 🛡️ **完整错误处理**: 优雅处理各种异常情况
- 📊 **实时状态监控**: 显示技能激活状态和使用统计
- 🔧 **生产环境配置**: 支持环境变量和配置文件

## 快速开始

### 1. 环境准备

```bash
# 激活虚拟环境
source h:/pythonwork/agentscope/.venv/bin/activate

# 或在Windows中
h:/pythonwork/agentscope/.venv/Scripts/activate

# 设置API密钥
export DASHSCOPE_API_KEY="your-api-key-here"
```

### 2. 运行应用

```bash
# 基本运行
python main_production.py

# 或使用uv运行
uv run python main_production.py
```

## 使用指南

### 基本对话

直接输入任何问题与AI助手对话：

```
👤 您: 请分析这个PDF文件中的表格数据
🔍 推荐技能: pdf
🤖 AI助手: 我可以帮您分析PDF文件中的表格数据。请提供PDF文件路径，我将使用PDF处理技能来提取和分析表格内容。
```

### 命令系统

应用支持以下命令：

- `/help` 或 `/h` - 显示帮助信息
- `/status` 或 `/s` - 显示技能状态
- `/skills` 或 `/k` - 列出所有可用技能
- `/clear` 或 `/c` - 清屏
- `/quit`、`/q` 或 `/exit` - 退出程序

### 技能使用示例

#### PDF处理技能
```
👤 您: 我需要提取PDF文档中的所有表格并导出为Excel
🔍 推荐技能: pdf
🤖 AI助手: 我将使用PDF处理技能来帮您提取表格数据。系统会自动激活PDF技能，使用pdfplumber库提取表格，并转换为Excel格式。
```

#### 算法艺术技能
```
👤 您: 创建一个基于流体动力学的算法艺术作品
🔍 推荐技能: algorithmic-art
🤖 AI助手: 我将使用算法艺术技能来创建基于流体动力学的生成艺术。系统会提供p5.js代码和交互式查看器。
```

#### 文档处理技能
```
👤 您: 请帮我生成一个专业的Word报告
🔍 推荐技能: document-skills
🤖 AI助手: 我将使用文档处理技能来帮您创建专业的Word文档，包括格式化、样式设置和内容组织。
```

## 配置说明

### 环境变量

```bash
# 必需
export DASHSCOPE_API_KEY="your-dashscope-api-key"

# 可选
export SKILL_DIRECTORY="./skills"
export SKILL_AUTO_DISCOVERY="true"
export LOG_LEVEL="INFO"
```

### 配置文件

修改 `config.yaml` 来自定义设置：

```yaml
model:
  provider: "dashscope"
  model_name: "qwen-max"
  api_key_env: "DASHSCOPE_API_KEY"

agent:
  name: "ProductionAgent"
  auto_skill_discovery: true
  skill_matching_threshold: 0.7
  max_iters: 15

skill_manager:
  skill_directory: "skills"
  cache_enabled: true
```

## 技能开发

### 添加新技能

1. 在 `skills/` 目录创建新文件夹
2. 添加 `SKILL.md` 文件
3. 添加工具脚本（可选）
4. 重启应用或使用 `/skills` 命令查看

### 技能目录结构

```
skills/
├── your-skill/
│   ├── SKILL.md          # 技能元数据和说明
│   ├── tools.py          # Python工具函数
│   ├── scripts/          # 辅助脚本
│   └── resources/        # 资源文件
```

## 部署

### Docker部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY . /app/
RUN pip install -e .

ENV DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}

CMD ["python", "main_production.py"]
```

### 系统服务

```bash
# 创建systemd服务文件
sudo nano /etc/systemd/system/ai-assistant.service

# 启用服务
sudo systemctl enable ai-assistant
sudo systemctl start ai-assistant
```

## 故障排除

### 常见问题

1. **API密钥未设置**
   ```
   错误: 未找到API密钥
   解决: export DASHSCOPE_API_KEY="your-key"
   ```

2. **技能未发现**
   ```
   错误: 发现0个技能
   解决: 检查skills目录路径和权限
   ```

3. **模块导入错误**
   ```
   错误: ModuleNotFoundError
   解决: 确保使用正确的虚拟环境
   ```

### 日志查看

```bash
# 查看应用日志
tail -f logs/agent_skills.log

# 调试模式
python main_production.py --debug
```

## 性能优化

### 技能缓存

应用自动缓存技能内容，提高响应速度：

```python
# 缓存统计
info = agent.get_active_skills_info()
print(f"缓存大小: {info['skill_context_cache_size']}")
```

### 内存管理

```python
# 监控内存使用
import psutil
memory_usage = psutil.virtual_memory()
print(f"内存使用: {memory_usage.percent}%")
```

## 安全考虑

- ✅ API密钥通过环境变量传递
- 🔒 技能加载验证和沙箱
- 📝 完整的日志记录
- 🚫 输入验证和清理

## 许可证

本项目遵循Apache-2.0许可证。详见LICENSE文件。

## 支持

如有问题或建议，请：
1. 查看应用内帮助 (`/help`)
2. 检查日志文件
3. 提交Issue到项目仓库

---

**🚀 现在就开始使用生产级技能化AI助手吧！**