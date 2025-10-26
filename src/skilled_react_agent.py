# -*- coding: utf-8 -*-
"""Skilled ReAct Agent with Agent Skills integration."""

import asyncio
import re
from typing import Dict, List, Optional, Any, Type
from pathlib import Path
from collections import OrderedDict
import time

from agentscope.agent import ReActAgent
from agentscope.message import Msg, TextBlock
from agentscope.memory import MemoryBase, LongTermMemoryBase, InMemoryMemory
from agentscope.model import ChatModelBase
from agentscope.formatter import FormatterBase
from agentscope.tool import Toolkit, ToolResponse
from agentscope._logging import logger

from skill_manager import SkillManager, SkillMetadata


class SkilledReActAgent(ReActAgent):
    """ReAct Agent with integrated Agent Skills capabilities.
    
    This agent extends the base ReActAgent to support:
    - Automatic skill discovery and loading
    - Progressive disclosure of skill content
    - Dynamic skill activation based on task requirements
    - Skill-based tool management
    """
    
    def __init__(
        self,
        name: str,
        sys_prompt: str,
        model: ChatModelBase,
        formatter: FormatterBase,
        skill_directory: str = "./skills",
        memory: MemoryBase | None = None,
        long_term_memory: LongTermMemoryBase | None = None,
        long_term_memory_mode: str = "both",
        enable_meta_tool: bool = True,
        parallel_tool_calls: bool = False,
        knowledge=None,
        enable_rewrite_query: bool = True,
        plan_notebook=None,
        print_hint_msg: bool = True,
        max_iters: int = 10,
        auto_skill_discovery: bool = True,
        skill_matching_threshold: float = 0.7,
    ):
        """Initialize the Skilled ReAct Agent.
        
        Args:
            name (str): Name of the agent
            sys_prompt (str): System prompt
            model (ChatModelBase): Chat model
            formatter (FormatterBase): Message formatter
            skill_directory (str): Directory containing skills
            memory (MemoryBase): Memory system
            long_term_memory (LongTermMemoryBase): Long-term memory
            long_term_memory_mode (str): Memory mode
            enable_meta_tool (bool): Enable meta tool for skill management
            parallel_tool_calls (bool): Enable parallel tool calls
            knowledge: Knowledge base
            enable_rewrite_query (bool): Enable query rewriting
            plan_notebook: Plan notebook
            print_hint_msg (bool): Print hint messages
            max_iters (int): Maximum iterations
            auto_skill_discovery (bool): Auto-discover skills on init
            skill_matching_threshold (float): Threshold for skill matching
        """
        
        # Initialize skill manager
        self.skill_manager = SkillManager(skill_directory)
        self.auto_skill_discovery = auto_skill_discovery
        self.skill_matching_threshold = skill_matching_threshold
        self.active_skills: List[str] = []
        
        # LRU cache for skill context with size limit
        self._max_cache_size = 50
        self._skill_context_cache: OrderedDict[str, tuple] = OrderedDict()  # (content, timestamp)
        
        # Create toolkit with skill management
        toolkit = Toolkit()
        
        # Initialize parent class
        super().__init__(
            name=name,
            sys_prompt=sys_prompt,
            model=model,
            formatter=formatter,
            toolkit=toolkit,
            memory=memory,
            long_term_memory=long_term_memory,
            long_term_memory_mode=long_term_memory_mode,
            enable_meta_tool=enable_meta_tool,
            parallel_tool_calls=parallel_tool_calls,
            knowledge=knowledge,
            enable_rewrite_query=enable_rewrite_query,
            plan_notebook=plan_notebook,
            print_hint_msg=print_hint_msg,
            max_iters=max_iters,
        )
        
        # Register skill management tools
        self._register_skill_management_tools()
        
        # Discover skills if enabled
        if self.auto_skill_discovery:
            self._skill_discovery_task = asyncio.create_task(self._initialize_skills())
    
    def _add_to_cache(self, skill_name: str, content: str):
        """Add skill content to LRU cache with size management."""
        # Remove if already exists (to update position)
        if skill_name in self._skill_context_cache:
            del self._skill_context_cache[skill_name]
        
        # Add to end (most recently used)
        self._skill_context_cache[skill_name] = (content, time.time())
        
        # Remove oldest if cache is full
        while len(self._skill_context_cache) > self._max_cache_size:
            oldest_key = next(iter(self._skill_context_cache))
            del self._skill_context_cache[oldest_key]
            logger.debug(f"Removed skill '{oldest_key}' from cache due to size limit")
    
    def _get_from_cache(self, skill_name: str) -> Optional[str]:
        """Get skill content from LRU cache and update its position."""
        if skill_name in self._skill_context_cache:
            content, timestamp = self._skill_context_cache[skill_name]
            # Move to end (mark as recently used)
            del self._skill_context_cache[skill_name]
            self._skill_context_cache[skill_name] = (content, timestamp)
            return content
        return None
    
    def _remove_from_cache(self, skill_name: str):
        """Remove skill content from cache."""
        if skill_name in self._skill_context_cache:
            del self._skill_context_cache[skill_name]
    
    def _cleanup_old_cache(self, max_age_seconds: int = 3600):
        """Remove cache entries older than max_age_seconds."""
        current_time = time.time()
        keys_to_remove = []
        
        for skill_name, (_, timestamp) in self._skill_context_cache.items():
            if current_time - timestamp > max_age_seconds:
                keys_to_remove.append(skill_name)
        
        for skill_name in keys_to_remove:
            del self._skill_context_cache[skill_name]
            logger.debug(f"Removed skill '{skill_name}' from cache due to age")
    
    @property
    def skill_context_cache(self) -> Dict[str, str]:
        """Get skill context cache as a simple dict for compatibility."""
        return {k: v[0] for k, v in self._skill_context_cache.items()}
    
    async def _initialize_skills(self):
        """Initialize skills on agent creation."""
        try:
            await self.skill_manager.discover_skills()
            logger.info(f"Discovered {len(self.skill_manager.discovered_skills)} skills")
        except Exception as e:
            logger.error(f"Failed to discover skills: {e}")
    
    def _register_skill_management_tools(self):
        """Register tools for skill management."""
        
        async def list_skills() -> ToolResponse:
            """List all available skills with their descriptions."""
            summary = self.skill_manager.get_skill_metadata_summary()
            return ToolResponse(
                content=[TextBlock(type="text", text=summary)],
                is_last=True
            )
        
        async def activate_skill(skill_name: str) -> ToolResponse:
            """Activate a specific skill and its tools.
            
            Args:
                skill_name (str): Name of the skill to activate
            """
            success = await self.skill_manager.activate_skill(skill_name)
            if success:
                if skill_name not in self.active_skills:
                    self.active_skills.append(skill_name)
                
                # Get skill content for context
                try:
                    skill_content = self.skill_manager.get_skill_content(skill_name)
                    self._add_to_cache(skill_name, skill_content)
                except Exception as e:
                    logger.warning(f"Failed to load skill content: {e}")
                
                return ToolResponse(
                    content=[TextBlock(
                        type="text", 
                        text=f"Successfully activated skill: {skill_name}"
                    )],
                    is_last=True
                )
            else:
                return ToolResponse(
                    content=[TextBlock(
                        type="text",
                        text=f"Failed to activate skill: {skill_name}"
                    )],
                    is_last=True
                )
        
        async def deactivate_skill(skill_name: str) -> ToolResponse:
            """Deactivate a specific skill.
            
            Args:
                skill_name (str): Name of the skill to deactivate
            """
            success = await self.skill_manager.deactivate_skill(skill_name)
            if success:
                if skill_name in self.active_skills:
                    self.active_skills.remove(skill_name)
                self._remove_from_cache(skill_name)
                
                return ToolResponse(
                    content=[TextBlock(
                        type="text",
                        text=f"Successfully deactivated skill: {skill_name}"
                    )],
                    is_last=True
                )
            else:
                return ToolResponse(
                    content=[TextBlock(
                        type="text",
                        text=f"Failed to deactivate skill: {skill_name}"
                    )],
                    is_last=True
                )
        
        async def get_skill_content(skill_name: str, include_resources: bool = False) -> ToolResponse:
            """Get the content of a specific skill.
            
            Args:
                skill_name (str): Name of the skill
                include_resources (bool): Whether to include additional resources
            """
            try:
                content = self.skill_manager.get_skill_content(
                    skill_name, include_resources
                )
                return ToolResponse(
                    content=[TextBlock(type="text", text=content)],
                    is_last=True
                )
            except Exception as e:
                return ToolResponse(
                    content=[TextBlock(
                        type="text",
                        text=f"Error getting skill content: {e}"
                    )],
                    is_last=True
                )
        
        # Register the tools
        self.toolkit.register_tool_function(list_skills)
        self.toolkit.register_tool_function(activate_skill)
        self.toolkit.register_tool_function(deactivate_skill)
        self.toolkit.register_tool_function(get_skill_content)
    
    async def _match_skills_to_task(self, user_message: str) -> List[str]:
        """Match skills to the current task based on user message.
        
        Args:
            user_message (str): User's message/task description
            
        Returns:
            List[str]: List of relevant skill names
        """
        if not self.skill_manager.discovered_skills:
            return []
        
        relevant_skills = []
        user_message_lower = user_message.lower()
        
        # Simple keyword-based matching
        for skill_name, metadata in self.skill_manager.discovered_skills.items():
            # Check skill name
            if skill_name.lower() in user_message_lower:
                relevant_skills.append(skill_name)
                continue
            
            # Check description keywords
            description_words = metadata.description.lower().split()
            message_words = user_message_lower.split()
            
            # Calculate simple overlap ratio with safety checks
            description_set = set(description_words)
            message_set = set(message_words)
            
            # Skip if description is empty to avoid division by zero
            if not description_set:
                continue
                
            overlap = len(description_set & message_set)
            if overlap > 0:
                ratio = overlap / len(description_set)
                if ratio >= self.skill_matching_threshold:
                    relevant_skills.append(skill_name)
        
        return relevant_skills
    
    async def _auto_activate_skills(self, user_message: str):
        """Automatically activate relevant skills based on user message.
        
        Args:
            user_message (str): User's message
        """
        relevant_skills = await self._match_skills_to_task(user_message)
        
        for skill_name in relevant_skills:
            if skill_name not in self.active_skills:
                await self.skill_manager.activate_skill(skill_name)
                self.active_skills.append(skill_name)
                
                # Load skill content
                try:
                    skill_content = self.skill_manager.get_skill_content(skill_name)
                    self._add_to_cache(skill_name, skill_content)
                    logger.info(f"Auto-activated skill: {skill_name}")
                except Exception as e:
                    logger.warning(f"Failed to load skill content for {skill_name}: {e}")
    
    @property
    def sys_prompt(self) -> str:
        """Dynamic system prompt with skill context."""
        base_prompt = self._sys_prompt
        
        # Add skill context
        if self.skill_manager.discovered_skills:
            skill_summary = self.skill_manager.get_skill_metadata_summary()
            skill_context = f"\n\n{skill_summary}\n"
            skill_context += "You can use the skill management tools (list_skills, activate_skill, "
            skill_context += "deactivate_skill, get_skill_content) to manage these skills. "
            skill_context += "When a task requires specific expertise, consider activating relevant skills."
            
            base_prompt += skill_context
        
        # Add active skills context
        if self.active_skills and self.skill_context_cache:
            active_context = "\n\nCurrently Active Skills:\n"
            for skill_name in self.active_skills:
                if skill_name in self.skill_context_cache:
                    content = self.skill_context_cache[skill_name]
                    # Truncate very long content
                    if len(content) > 2000:
                        content = content[:2000] + "...\n[Content truncated]"
                    active_context += f"\n--- {skill_name} ---\n{content}\n"
            
            base_prompt += active_context
        
        return base_prompt
    
    async def reply(
        self,
        msg: Msg | list[Msg] | None = None,
        structured_model: Type[Any] | None = None,
    ) -> Msg:
        """Generate a reply with automatic skill activation.
        
        Args:
            msg: Input message(s)
            structured_model: Required structured output model
            
        Returns:
            Msg: Generated reply
        """
        # Extract user message text for skill matching
        user_text = ""
        if msg:
            if isinstance(msg, Msg):
                user_text = msg.get_text_content() or ""
            elif isinstance(msg, list):
                user_text = " ".join(m.get_text_content() or "" for m in msg)
        
        # Auto-activate relevant skills
        if user_text:
            await self._auto_activate_skills(user_text)
        
        # Call parent reply method
        return await super().reply(msg, structured_model)
    
    async def get_skill_recommendations(self, task_description: str) -> List[str]:
        """Get skill recommendations for a specific task.
        
        Args:
            task_description (str): Description of the task
            
        Returns:
            List[str]: Recommended skill names
        """
        return await self._match_skills_to_task(task_description)
    
    def get_active_skills_info(self) -> Dict[str, Any]:
        """Get information about currently active skills.
        
        Returns:
            Dict[str, Any]: Active skills information
        """
        info = {
            "active_skills": self.active_skills.copy(),
            "total_discovered": len(self.skill_manager.discovered_skills),
            "skill_context_cache_size": len(self.skill_context_cache)
        }
        
        # Add skill details
        skill_details = {}
        for skill_name in self.active_skills:
            if skill_name in self.skill_manager.discovered_skills:
                metadata = self.skill_manager.discovered_skills[skill_name]
                skill_details[skill_name] = {
                    "description": metadata.description,
                    "version": metadata.version,
                    "author": metadata.author
                }
        
        info["skill_details"] = skill_details
        return info
