#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生产级技能化AI助手
- 自动技能发现和激活
- 智能任务匹配
- 简洁的终端界面
- 完整的错误处理
- 生产环境配置
"""

import asyncio
import sys
import os
import signal
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try to load .env file from the current directory
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
        print("✅ 已加载 .env 文件中的环境变量")
    else:
        print("⚠️  未找到 .env 文件")
except ImportError:
    print("⚠️  未安装 python-dotenv，请运行: pip install python-dotenv")
except Exception as e:
    print(f"⚠️  加载 .env 文件时出错: {e}")

# 导入AgentScope组件
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel
from agentscope.formatter import DashScopeChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope._logging import logger

# 导入项目组件
from skilled_react_agent import SkilledReActAgent
from config_loader import load_config, get_config_loader


class ProductionAgent:
    """生产级技能化AI助手"""
    
    def __init__(self):
        """初始化生产代理"""
        self.agent: Optional[SkilledReActAgent] = None
        self.config = None
        self.config_loader = None
        self.running = False
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        print("\n👋 正在安全关闭...")
        self.running = False
    
    async def initialize(self) -> bool:
        """初始化代理和配置"""
        try:
            print("🚀 正在初始化AI助手...")
            
            # 加载配置
            self.config = load_config()
            self.config_loader = get_config_loader()
            
            # 验证配置
            if not self.config_loader.validate_config():
                print("❌ 配置验证失败")
                return False
            
            # 获取API密钥
            api_key = self.config_loader.get_api_key()
            if not api_key:
                print(f"❌ 未找到API密钥: {self.config.model.api_key_env}")
                print(f"请设置环境变量: {self.config.model.api_key_env}")
                return False
            
            # 创建模型
            model_config = self.config.model
            model = DashScopeChatModel(
                model_name=model_config.model_name,
                api_key=api_key,
                **model_config.parameters
            )
            
            # 创建技能化代理
            self.agent = SkilledReActAgent(
                name=self.config.agent.name,
                sys_prompt=self.config.agent.system_prompt,
                model=model,
                formatter=DashScopeChatFormatter(),
                skill_directory=self.config.skill_manager.skill_directory,
                memory=InMemoryMemory(),
                auto_skill_discovery=self.config.agent.auto_skill_discovery,
                skill_matching_threshold=self.config.agent.skill_matching_threshold,
                print_hint_msg=self.config.agent.print_hint_msg,
                max_iters=self.config.agent.max_iters,
            )
            
            # 等待技能发现完成
            print("🔍 正在发现技能...")
            await asyncio.sleep(2)  # 给技能发现一些时间
            
            # 显示初始化信息
            self._show_startup_info()
            self.running = True
            
            return True
            
        except Exception as e:
            print(f"❌ 初始化失败: {str(e)}")
            return False
    
    def _show_startup_info(self):
        """显示启动信息"""
        if not self.agent:
            return
            
        # 获取技能信息
        skill_info = self.agent.get_active_skills_info()
        
        print("\n" + "="*60)
        print("🤖 生产级技能化AI助手已启动")
        print(f"📋 模型: {self.config.model.provider}/{self.config.model.model_name}")
        print(f"📁 技能目录: {self.config.skill_manager.skill_directory}")
        print(f"🔑 API密钥: {'已配置' if self.config_loader.get_api_key() else '未配置'}")
        print(f"📚 发现技能: {skill_info['total_discovered']}个")
        print(f"⚡ 活跃技能: {len(skill_info['active_skills'])}个")
        print("="*60)
    
    def _show_skill_status(self):
        """显示技能状态"""
        if not self.agent:
            return
            
        skill_info = self.agent.get_active_skills_info()
        
        print(f"\n📊 技能状态:")
        print(f"   发现总数: {skill_info['total_discovered']}")
        print(f"   活跃技能: {len(skill_info['active_skills'])}")
        
        if skill_info['active_skills']:
            print("   当前活跃:")
            for skill in skill_info['active_skills']:
                if skill in skill_info.get('skill_details', {}):
                    details = skill_info['skill_details'][skill]
                    print(f"     ✅ {skill}: {details.get('description', '无描述')}")
                else:
                    print(f"     ✅ {skill}")
        else:
            print("   当前无活跃技能")
    
    async def get_skill_recommendations(self, user_input: str) -> list:
        """获取技能推荐"""
        if not self.agent:
            return []
            
        try:
            recommendations = await self.agent.get_skill_recommendations(user_input)
            return recommendations
        except Exception as e:
            logger.warning(f"获取技能推荐失败: {e}")
            return []
    
    async def process_input(self, user_input: str) -> str:
        """处理用户输入"""
        try:
            # 获取技能推荐
            recommendations = await self.agent.get_skill_recommendations(user_input)
            if recommendations:
                print(f"🔍 推荐技能: {', '.join(recommendations)}")
            
            # 处理消息
            print("🤔 正在思考...")
            response = await self.agent(Msg("user", user_input, "user"))
            
            return response.get_text_content()
            
        except Exception as e:
            error_msg = f"处理请求时发生错误: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg)
            return error_msg
    
    def show_help(self):
        """显示帮助信息"""
        print("\n📖 可用命令:")
        print("   /help, /h     - 显示此帮助信息")
        print("   /status, /s    - 显示技能状态")
        print("   /skills, /k    - 列出所有可用技能")
        print("   /clear, /c     - 清屏")
        print("   /quit, /q, /exit - 退出程序")
        print("\n💡 提示: 直接输入任何问题与AI助手对话")
    
    async def show_all_skills(self):
        """显示所有可用技能"""
        if not self.agent:
            print("❌ 代理未初始化")
            return
            
        try:
            # 获取技能摘要
            summary = self.agent.skill_manager.get_skill_metadata_summary()
            print(f"\n📚 所有可用技能:")
            print(summary)
        except Exception as e:
            print(f"❌ 获取技能列表失败: {e}")
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    async def run(self):
        """运行主循环"""
        if not await self.initialize():
            return
        
        print("\n💬 输入您的问题或命令 (输入 /help 查看帮助):")
        
        while self.running:
            try:
                # 获取用户输入
                user_input = input("\n👤 您: ").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.lower() in ['/quit', '/q', '/exit']:
                    break
                elif user_input.lower() in ['/help', '/h']:
                    self.show_help()
                elif user_input.lower() in ['/status', '/s']:
                    self._show_skill_status()
                elif user_input.lower() in ['/skills', '/k']:
                    await self.show_all_skills()
                elif user_input.lower() in ['/clear', '/c']:
                    self.clear_screen()
                else:
                    # 处理普通对话
                    print("🤖 AI助手: ", end="", flush=True)
                    response = await self.process_input(user_input)
                    print(response)
                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ 发生未预期的错误: {e}")
                logger.error(f"主循环错误: {e}")
        
        print("\n👋 感谢使用，再见！")


async def main():
    """主函数"""
    try:
        # 创建生产代理
        agent = ProductionAgent()
        
        # 运行主循环
        await agent.run()
        
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序发生致命错误: {e}")
        logger.error(f"致命错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("❌ 需要Python 3.7或更高版本")
        sys.exit(1)
    
    # 运行主程序
    asyncio.run(main())