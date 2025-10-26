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
        """Register Python files from skill directory as tools.
        
        Args:
            skill_name (str): Name of the skill
            skill_dir (str): Directory containing the skill
        """
        with self._registration_lock:
            skill_path = Path(skill_dir)
            
            for py_file in skill_path.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                    
                try:
                    # Load the module and register its functions
                    module_name = f"skill_{skill_name}_{py_file.stem}"
                    spec = importlib.util.spec_from_file_location(module_name, py_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Register functions that are marked as tools
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (callable(attr) and 
                            hasattr(attr, '__skill_tool__') and 
                            attr.__skill_tool__):
                            
                            self.toolkit.register_tool_function(
                                tool_func=attr,
                                group_name=skill_name
                            )
                            
                except Exception as e:
                    logger.warning(f"Failed to load tools from {py_file}: {e}")
    
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
