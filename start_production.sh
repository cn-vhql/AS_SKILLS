#!/bin/bash
# 生产级技能化AI助手启动脚本

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 正在启动生产级技能化AI助手...${NC}"

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -Po '(?P)' | cut -d' ' ' -f2)
if [[ $(echo "$python_version" | cut -d'.' -f1) -lt 3 ]] || [[ $(echo "$python_version" | cut -d'.' -f2) -lt 7 ]]; then
    echo -e "${RED}❌ 错误: 需要Python 3.7或更高版本${NC}"
    echo -e "${YELLOW}当前版本: $python_version${NC}"
    exit 1
fi

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo -e "${GREEN}✅ 虚拟环境已激活: $VIRTUAL_ENV${NC}"
else
    echo -e "${YELLOW}⚠️  警告: 虚拟环境未激活${NC}"
    echo -e "${BLUE}💡 建议激活虚拟环境:${NC}"
    echo -e "   ${YELLOW}source h:/pythonwork/agentscope/.venv/bin/activate${NC}"
    echo ""
fi

# 检查API密钥
if [[ -z "$DASHSCOPE_API_KEY" ]]; then
    echo -e "${RED}❌ 错误: DASHSCOPE_API_KEY环境变量未设置${NC}"
    echo -e "${BLUE}💡 请设置API密钥:${NC}"
    echo -e "   ${YELLOW}export DASHSCOPE_API_KEY='your-api-key-here'${NC}"
    echo -e "   ${YELLOW}或创建 .env 文件并添加密钥${NC}"
    exit 1
else
    echo -e "${GREEN}✅ API密钥已配置${NC}"
fi

# 检查技能目录
if [[ ! -d "skills" ]]; then
    echo -e "${RED}❌ 错误: skills目录不存在${NC}"
    echo -e "${BLUE}💡 请确保在正确的目录运行此脚本${NC}"
    exit 1
else
    skill_count=$(find skills -maxdepth 1 -type d | wc -l)
    echo -e "${GREEN}✅ 发现 $skill_count 个技能目录${NC}"
fi

# 检查配置文件
if [[ -f "config.yaml" ]]; then
    echo -e "${GREEN}✅ 配置文件存在${NC}"
else
    echo -e "${YELLOW}⚠️  警告: config.yaml不存在，将使用默认配置${NC}"
fi

# 创建日志目录
mkdir -p logs 2>/dev/null

echo -e "${BLUE}🔧 环境检查完成，正在启动应用...${NC}"
echo ""

# 启动应用
if command -v uv &> /dev/null; then
    echo -e "${GREEN}🚀 使用uv启动应用...${NC}"
    uv run python main_production.py
else
    echo -e "${GREEN}🚀 使用python启动应用...${NC}"
    python3 main_production.py
fi

# 检查退出状态
exit_code=$?
if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}✅ 应用正常退出${NC}"
else
    echo -e "${RED}❌ 应用异常退出 (代码: $exit_code)${NC}"
fi