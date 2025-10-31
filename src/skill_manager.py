# -*- coding: utf-8 -*-
"""Skill Manager for Agent Skills integration with AgentScope."""

import os
import yaml
import asyncio
import importlib.util
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock
from agentscope._logging import logger


@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    name: str
    description: str
    directory: str
    skill_file_path: str
    dependencies: List[str] = None
    version: str = "1.0.0"
    author: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []


class SkillManager:
    """Manager for discovering and loading Agent Skills."""
    
    def __init__(self, skill_directory: str = "./skills"):
        """Initialize the skill manager.
        
        Args:
            skill_directory (str): Directory containing skill folders
        """
        self.skill_directory = Path(skill_directory)
        self.discovered_skills: Dict[str, SkillMetadata] = {}
        self.loaded_skills: Dict[str, Dict[str, Any]] = {}
        self.toolkit = Toolkit()
        
        # Thread safety locks
        self._discovery_lock = threading.Lock()
        self._loading_lock = threading.Lock()
        self._registration_lock = threading.Lock()
        
    async def discover_skills(self) -> Dict[str, SkillMetadata]:
        """Discover all available skills in the skill directory.
        
        Returns:
            Dict[str, SkillMetadata]: Dictionary of discovered skills
        """
        with self._discovery_lock:
            if not self.skill_directory.exists():
                logger.warning(f"Skill directory {self.skill_directory} does not exist")
                return {}
                
            skills = {}
            
            for skill_dir in self.skill_directory.iterdir():
                if not skill_dir.is_dir():
                    continue
                    
                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    logger.warning(f"No SKILL.md found in {skill_dir}")
                    continue
                    
                try:
                    metadata = await self._parse_skill_metadata(skill_dir, skill_file)
                    skills[metadata.name] = metadata
                    logger.info(f"Discovered skill: {metadata.name}")
                except Exception as e:
                    logger.error(f"Failed to parse skill {skill_dir}: {e}")
                    
            self.discovered_skills = skills
            return skills
    
    async def _parse_skill_metadata(self, skill_dir: Path, skill_file: Path) -> SkillMetadata:
        """Parse skill metadata from SKILL.md file.
        
        Args:
            skill_dir (Path): Directory containing the skill
            skill_file (Path): Path to SKILL.md file
            
        Returns:
            SkillMetadata: Parsed metadata
        """
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse YAML frontmatter
        if content.startswith('---'):
            try:
                end_index = content.find('---', 3)
                if end_index == -1:
                    raise ValueError("Invalid YAML frontmatter format")
                    
                yaml_content = content[3:end_index].strip()
                frontmatter = yaml.safe_load(yaml_content)
                
                name = frontmatter.get('name')
                description = frontmatter.get('description')
                
                if not name or not description:
                    raise ValueError("Missing required fields 'name' or 'description'")
                    
                return SkillMetadata(
                    name=name,
                    description=description,
                    directory=str(skill_dir),
                    skill_file_path=str(skill_file),
                    dependencies=frontmatter.get('dependencies', []),
                    version=frontmatter.get('version', '1.0.0'),
                    author=frontmatter.get('author', '')
                )
                
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in frontmatter: {e}")
        else:
            raise ValueError("SKILL.md must start with YAML frontmatter")
    
    async def load_skill(self, skill_name: str) -> Dict[str, Any]:
        """Load a specific skill with progressive disclosure.
        
        Args:
            skill_name (str): Name of the skill to load
            
        Returns:
            Dict[str, Any]: Loaded skill data including content and tools
        """
        with self._loading_lock:
            if skill_name not in self.discovered_skills:
                raise ValueError(f"Skill '{skill_name}' not found in discovered skills")
                
            if skill_name in self.loaded_skills:
                return self.loaded_skills[skill_name]
                
            metadata = self.discovered_skills[skill_name]
            
            # Load the main skill content
            with open(metadata.skill_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract content after frontmatter
            if content.startswith('---'):
                end_index = content.find('---', 3)
                skill_content = content[end_index + 3:].strip()
            else:
                skill_content = content
                
            # Parse for file references and load additional resources
            additional_resources = await self._load_additional_resources(
                skill_content, metadata.directory
            )
            
            # Create tool group for this skill
            self.toolkit.create_tool_group(
                group_name=skill_name,
                description=metadata.description,
                active=False,
                notes=f"Skill: {metadata.name}\n{metadata.description}"
            )
            
            # Register any Python files as tools
            await self._register_skill_tools(skill_name, metadata.directory)
            
            skill_data = {
                'metadata': metadata,
                'content': skill_content,
                'additional_resources': additional_resources,
                'tools': self._get_skill_tools(skill_name)
            }
            
            self.loaded_skills[skill_name] = skill_data
            logger.info(f"Loaded skill: {skill_name}")
            
            return skill_data
    
    async def _load_additional_resources(self, content: str, skill_dir: str) -> Dict[str, str]:
        """Load additional resources referenced in skill content.
        
        Args:
            content (str): Skill content to parse for references
            skill_dir (str): Directory containing the skill
            
        Returns:
            Dict[str, str]: Additional resource contents
        """
        resources = {}
        
        # Simple pattern matching for file references
        # Look for patterns like [filename.md](filename.md) or @include(filename.md)
        import re
        
        # Markdown link pattern
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\.md\)'
        matches = re.findall(link_pattern, content)
        
        for link_text, filename in matches:
            file_path = Path(skill_dir) / f"{filename}.md"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    resources[filename] = f.read()
                    
        # Include directive pattern
        include_pattern = r'@include\(([^)]+)\)'
        matches = re.findall(include_pattern, content)
        
        for filename in matches:
            file_path = Path(skill_dir) / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    resources[filename] = f.read()
                    
        return resources
    
    async def _register_skill_tools(self, skill_name: str, skill_dir: str):
        """Register Python files from skill directory as tools with intelligent discovery.
        
        Args:
            skill_name (str): Name of the skill
            skill_dir (str): Directory containing the skill
        """
        with self._registration_lock:
            skill_path = Path(skill_dir)
            
            # Look for Python files in both root and scripts subdirectory
            py_files = list(skill_path.glob("*.py"))
            py_files.extend(skill_path.glob("scripts/*.py"))
            
            for py_file in py_files:
                if py_file.name == "__init__.py":
                    continue
                    
                try:
                    # Load the module and register its functions
                    module_name = f"skill_{skill_name}_{py_file.stem}"
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    logger.info(f"Loaded module {module_name} from {py_file}")
                    
                    # Intelligent tool registration with multiple strategies
                    tool_count = 0
                    
                    # Strategy 1: Explicit @skill_tool decorator (highest priority)
                    tool_count += self._register_explicit_tools(module, skill_name)
                    
                    # Strategy 2: Naming convention detection
                    tool_count += self._register_by_naming_convention(module, skill_name)
                    
                    # Strategy 3: Docstring analysis
                    tool_count += self._register_by_docstring_analysis(module, skill_name)
                    
                    # Strategy 4: Type hints analysis
                    tool_count += self._register_by_type_hints(module, skill_name)
                    
                    logger.info(f"Registered {tool_count} tools from {py_file}")
                            
                except Exception as e:
                    logger.warning(f"Failed to load tools from {py_file}: {e}")
                    import traceback
                    logger.warning(f"Traceback: {traceback.format_exc()}")
    
    def _register_explicit_tools(self, module, skill_name: str) -> int:
        """Register tools with explicit @skill_tool decorator."""
        count = 0
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (callable(attr) and 
                hasattr(attr, '__skill_tool__') and 
                attr.__skill_tool__):
                
                description = getattr(attr, '__skill_tool_description__', '')
                logger.info(f"Registering explicit tool: {attr_name}")
                
                # 检查工具是否已经注册
                if attr_name in self.toolkit.tools:
                    logger.warning(f"Tool {attr_name} already registered, skipping")
                    continue
                
                # 创建一个包装函数，确保工具可以被正确调用并返回ToolResponse
                # 使用默认参数来避免闭包问题
                def wrapped_tool(*args, attr_name=attr_name, attr=attr, **kwargs):
                    try:
                        result = attr(*args, **kwargs)
                        # Convert string result to ToolResponse format
                        if isinstance(result, str):
                            return ToolResponse(
                                content=[TextBlock(type="text", text=result)],
                                is_last=True
                            )
                        elif isinstance(result, ToolResponse):
                            return result
                        else:
                            # Convert other types to string
                            return ToolResponse(
                                content=[TextBlock(type="text", text=str(result))],
                                is_last=True
                            )
                    except Exception as e:
                        error_msg = f"Error executing {attr_name}: {str(e)}"
                        logger.error(error_msg)
                        return ToolResponse(
                            content=[TextBlock(type="text", text=error_msg)],
                            is_last=True
                        )
                
                # 保持原始函数的属性
                wrapped_tool.__name__ = attr_name
                wrapped_tool.__doc__ = getattr(attr, '__doc__', '')
                wrapped_tool.__skill_tool__ = True
                wrapped_tool.__skill_tool_description__ = description
                
                self.toolkit.register_tool_function(
                    tool_func=wrapped_tool,
                    group_name=skill_name
                )
                count += 1
        return count
    
    def _register_by_naming_convention(self, module, skill_name: str) -> int:
        """Register tools based on naming conventions."""
        # Tool function patterns
        tool_patterns = [
            'extract_', 'analyze_', 'process_', 'convert_', 
            'create_', 'generate_', 'check_', 'get_', 
            'parse_', 'transform_', 'validate_', 'search_'
        ]
        
        count = 0
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and not hasattr(attr, '__skill_tool__'):
                # Check if function name matches tool patterns
                if any(pattern in attr_name.lower() for pattern in tool_patterns):
                    logger.info(f"Registering tool by naming: {attr_name}")
                    
                    # 检查工具是否已经注册
                    if attr_name in self.toolkit.tools:
                        logger.warning(f"Tool {attr_name} already registered, skipping")
                        continue
                    
                    # 创建包装函数
                    # 使用默认参数来避免闭包问题
                    def wrapped_tool(*args, attr_name=attr_name, attr=attr, **kwargs):
                        try:
                            result = attr(*args, **kwargs)
                            # Convert string result to ToolResponse format
                            if isinstance(result, str):
                                return ToolResponse(
                                    content=[TextBlock(type="text", text=result)],
                                    is_last=True
                                )
                            elif isinstance(result, ToolResponse):
                                return result
                            else:
                                # Convert other types to string
                                return ToolResponse(
                                    content=[TextBlock(type="text", text=str(result))],
                                    is_last=True
                                )
                        except Exception as e:
                            error_msg = f"Error executing {attr_name}: {str(e)}"
                            logger.error(error_msg)
                            return ToolResponse(
                                content=[TextBlock(type="text", text=error_msg)],
                                is_last=True
                            )

                    wrapped_tool.__name__ = attr_name
                    wrapped_tool.__doc__ = getattr(attr, '__doc__', '')

                    self.toolkit.register_tool_function(
                        tool_func=wrapped_tool,
                        group_name=skill_name
                    )
                    count += 1
        return count
    
    def _register_by_docstring_analysis(self, module, skill_name: str) -> int:
        """Register tools based on docstring analysis."""
        count = 0
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            # Skip non-callable, private attributes, and common Python built-ins
            if (not callable(attr) or
                attr_name.startswith('_') or
                hasattr(attr, '__skill_tool__') or
                not attr.__doc__ or
                attr_name in ['Any', 'Dict', 'List', 'Optional', 'Tuple', 'Set', 'Union', 'Type', 'Optional']):
                continue

                doc = attr.__doc__
                if doc and self._is_tool_docstring(doc):
                    logger.info(f"Registering tool by docstring: {attr_name}")

                    # 检查工具是否已经注册
                    if attr_name in self.toolkit.tools:
                        logger.warning(f"Tool {attr_name} already registered, skipping")
                        continue

                    # 创建包装函数
                    # 使用默认参数来避免闭包问题
                    def wrapped_tool(*args, attr_name=attr_name, attr=attr, **kwargs):
                        try:
                            result = attr(*args, **kwargs)
                            # Convert string result to ToolResponse format
                            if isinstance(result, str):
                                return ToolResponse(
                                    content=[TextBlock(type="text", text=result)],
                                    is_last=True
                                )
                            elif isinstance(result, ToolResponse):
                                return result
                            else:
                                # Convert other types to string
                                return ToolResponse(
                                    content=[TextBlock(type="text", text=str(result))],
                                    is_last=True
                                )
                        except Exception as e:
                            error_msg = f"Error executing {attr_name}: {str(e)}"
                            logger.error(error_msg)
                            return ToolResponse(
                                content=[TextBlock(type="text", text=error_msg)],
                                is_last=True
                            )

                    wrapped_tool.__name__ = attr_name
                    wrapped_tool.__doc__ = doc

                    self.toolkit.register_tool_function(
                        tool_func=wrapped_tool,
                        group_name=skill_name
                    )
                    count += 1
        return count
    
    def _register_by_type_hints(self, module, skill_name: str) -> int:
        """Register tools based on type hints."""
        count = 0
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (callable(attr) and 
                not hasattr(attr, '__skill_tool__') and
                not attr.__doc__ and
                hasattr(attr, '__annotations__')):
                
                annotations = attr.__annotations__
                if annotations and 'return' in annotations:
                    return_type = annotations['return']
                    # Check if return type suggests a tool function
                    if return_type in [str, dict, list, bool, int, float]:
                        logger.info(f"Registering tool by type hints: {attr_name}")
                        
                        # 检查工具是否已经注册
                        if attr_name in self.toolkit.tools:
                            logger.warning(f"Tool {attr_name} already registered, skipping")
                            continue
                        
                        # 创建包装函数
                        # 使用默认参数来避免闭包问题
                        def wrapped_tool(*args, attr_name=attr_name, attr=attr, **kwargs):
                            try:
                                result = attr(*args, **kwargs)
                                # Convert string result to ToolResponse format
                                if isinstance(result, str):
                                    return ToolResponse(
                                        content=[TextBlock(type="text", text=result)],
                                        is_last=True
                                    )
                                elif isinstance(result, ToolResponse):
                                    return result
                                else:
                                    # Convert other types to string
                                    return ToolResponse(
                                        content=[TextBlock(type="text", text=str(result))],
                                        is_last=True
                                    )
                            except Exception as e:
                                error_msg = f"Error executing {attr_name}: {str(e)}"
                                logger.error(error_msg)
                                return ToolResponse(
                                    content=[TextBlock(type="text", text=error_msg)],
                                    is_last=True
                                )

                        wrapped_tool.__name__ = attr_name
                        wrapped_tool.__doc__ = f"Tool function with return type: {return_type}"

                        self.toolkit.register_tool_function(
                            tool_func=wrapped_tool,
                            group_name=skill_name
                        )
                        count += 1
        return count
    
    def _is_tool_docstring(self, doc: str) -> bool:
        """Check if docstring indicates a tool function."""
        if not doc:
            return False
        
        doc_lower = doc.lower()
        tool_indicators = [
            'tool:', 'extract', 'analyze', 'process', 'convert',
            'create', 'generate', 'check', 'parse', 'transform',
            'validate', 'search', 'function:', 'method:'
        ]
        
        return any(indicator in doc_lower for indicator in tool_indicators)
    
    def _generate_tool_description(self, attr_name: str, func) -> str:
        """Generate tool description from function name and signature."""
        # Convert snake_case to readable format
        name_parts = attr_name.split('_')
        if len(name_parts) >= 2:
            action = name_parts[0]
            object_name = '_'.join(name_parts[1:])
            
            descriptions = {
                'extract': f'Extract {object_name}',
                'analyze': f'Analyze {object_name}',
                'process': f'Process {object_name}',
                'convert': f'Convert {object_name}',
                'create': f'Create {object_name}',
                'generate': f'Generate {object_name}',
                'check': f'Check {object_name}',
                'get': f'Get {object_name}',
                'parse': f'Parse {object_name}',
                'transform': f'Transform {object_name}',
                'validate': f'Validate {object_name}',
                'search': f'Search {object_name}',
            }
            
            return descriptions.get(action, f'{attr_name.replace("_", " ").title()}')
        
        return attr_name.replace('_', ' ').title()
    
    def _generate_description_from_type_hints(self, attr_name: str, func, annotations: dict) -> str:
        """Generate description from type hints."""
        params = []
        for param_name, param_type in annotations.items():
            if param_name != 'return':
                params.append(f"{param_name}: {param_type.__name__ if hasattr(param_type, '__name__') else str(param_type)}")
        
        return_type = annotations.get('return', 'Any')
        return f'{attr_name.replace("_", " ").title()}({", ".join(params)}) -> {return_type}'
    
    def _get_skill_tools(self, skill_name: str) -> List[str]:
        """Get list of tool names for a specific skill.
        
        Args:
            skill_name (str): Name of the skill
            
        Returns:
            List[str]: List of tool names
        """
        tools = []
        for tool_name, tool_func in self.toolkit.tools.items():
            if tool_func.group == skill_name:
                tools.append(tool_name)
        return tools
    
    async def activate_skill(self, skill_name: str) -> bool:
        """Activate a skill's tool group.
        
        Args:
            skill_name (str): Name of the skill to activate
            
        Returns:
            bool: True if activation successful
        """
        if skill_name not in self.discovered_skills:
            logger.error(f"Skill '{skill_name}' not found")
            return False
            
        # Ensure skill is loaded
        if skill_name not in self.loaded_skills:
            await self.load_skill(skill_name)
            
        # Activate the tool group
        self.toolkit.update_tool_groups([skill_name], active=True)
        logger.info(f"Activated skill: {skill_name}")
        return True
    
    async def deactivate_skill(self, skill_name: str) -> bool:
        """Deactivate a skill's tool group.
        
        Args:
            skill_name (str): Name of the skill to deactivate
            
        Returns:
            bool: True if deactivation successful
        """
        if skill_name not in self.discovered_skills:
            logger.error(f"Skill '{skill_name}' not found")
            return False
            
        self.toolkit.update_tool_groups([skill_name], active=False)
        logger.info(f"Deactivated skill: {skill_name}")
        return True
    
    def get_skill_metadata_summary(self) -> str:
        """Get a summary of all discovered skills for agent context.
        
        Returns:
            str: Formatted summary of available skills
        """
        if not self.discovered_skills:
            return "No skills discovered."
            
        summary = "Available Skills:\n"
        for name, metadata in self.discovered_skills.items():
            summary += f"- {name}: {metadata.description}\n"
            
        return summary
    
    def get_skill_content(self, skill_name: str, include_resources: bool = False) -> str:
        """Get the content of a loaded skill.
        
        Args:
            skill_name (str): Name of the skill
            include_resources (bool): Whether to include additional resources
            
        Returns:
            str: Skill content
        """
        if skill_name not in self.loaded_skills:
            raise ValueError(f"Skill '{skill_name}' not loaded")
            
        skill_data = self.loaded_skills[skill_name]
        content = skill_data['content']
        
        if include_resources and skill_data['additional_resources']:
            content += "\n\nAdditional Resources:\n"
            for name, resource_content in skill_data['additional_resources'].items():
                content += f"\n## {name}\n{resource_content}\n"
                
        return content


def skill_tool(description: str = ""):
    """Decorator to mark a function as a skill tool.
    
    Args:
        description (str): Description of the tool
    """
    def decorator(func):
        func.__skill_tool__ = True
        func.__skill_tool_description__ = description
        return func
    return decorator
