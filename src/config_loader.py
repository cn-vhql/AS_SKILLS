# -*- coding: utf-8 -*-
"""Configuration loader for Agent Skills system."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from agentscope._logging import logger


@dataclass
class ModelConfig:
    """Model configuration."""
    provider: str
    model_name: str
    api_key_env: str
    api_key: Optional[str] = None  # Direct API key in config file
    parameters: Dict[str, Any] = None
    alternatives: Dict[str, Dict[str, Any]] = None


@dataclass
class AgentConfig:
    """Agent configuration."""
    name: str
    auto_skill_discovery: bool
    skill_matching_threshold: float
    max_iters: int
    print_hint_msg: bool
    system_prompt: str


@dataclass
class SkillManagerConfig:
    """Skill manager configuration."""
    skill_directory: str
    auto_reload: bool
    cache_enabled: bool
    progressive_disclosure: Dict[str, Any]
    matching: Dict[str, Any]


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str
    format: str
    file: Dict[str, Any]
    console: Dict[str, Any]


@dataclass
class SecurityConfig:
    """Security configuration."""
    skills: Dict[str, Any]
    data_protection: Dict[str, Any]
    sandbox: Dict[str, Any]


@dataclass
class PerformanceConfig:
    """Performance configuration."""
    cache: Dict[str, Any]
    concurrency: Dict[str, Any]
    resources: Dict[str, Any]


@dataclass
class DemoConfig:
    """Demo configuration."""
    scenarios: list
    settings: Dict[str, Any]


@dataclass
class Config:
    """Main configuration class."""
    model: ModelConfig
    agent: AgentConfig
    skill_manager: SkillManagerConfig
    logging: LoggingConfig
    security: SecurityConfig
    performance: PerformanceConfig
    demo: DemoConfig


class ConfigLoader:
    """Configuration loader and manager."""
    
    def __init__(self, config_path: str = "../config/config.yaml"):
        """Initialize config loader.
        
        Args:
            config_path (str): Path to configuration file
        """
        self.config_path = Path(config_path)
        self._config: Optional[Config] = None
    
    def load_config(self) -> Config:
        """Load configuration from file.
        
        Returns:
            Config: Loaded configuration
        """
        if not self.config_path.exists():
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            self._config = self._parse_config(config_data)
            return self._config
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            logger.warning("Using default configuration")
            return self._get_default_config()
    
    def _parse_config(self, config_data: Dict[str, Any]) -> Config:
        """Parse configuration data into Config object.
        
        Args:
            config_data (Dict[str, Any]): Raw configuration data
            
        Returns:
            Config: Parsed configuration
        """
        # Parse model config
        model_data = config_data.get('model', {})
        model_config = ModelConfig(
            provider=model_data.get('provider', 'dashscope'),
            model_name=model_data.get('model_name', 'qwen-max'),
            api_key_env=model_data.get('api_key_env', 'DASHSCOPE_API_KEY'),
            api_key=model_data.get('api_key'),  # Direct API key from config
            parameters=model_data.get('parameters', {}),
            alternatives=model_data.get('alternatives', {})
        )
        
        # Parse agent config
        agent_data = config_data.get('agent', {})
        agent_config = AgentConfig(
            name=agent_data.get('name', 'SkillMaster'),
            auto_skill_discovery=agent_data.get('auto_skill_discovery', True),
            skill_matching_threshold=agent_data.get('skill_matching_threshold', 0.7),
            max_iters=agent_data.get('max_iters', 10),
            print_hint_msg=agent_data.get('print_hint_msg', True),
            system_prompt=agent_data.get('system_prompt', self._get_default_system_prompt())
        )
        
        # Parse skill manager config
        skill_data = config_data.get('skill_manager', {})
        skill_config = SkillManagerConfig(
            skill_directory=skill_data.get('skill_directory', './skills'),
            auto_reload=skill_data.get('auto_reload', False),
            cache_enabled=skill_data.get('cache_enabled', True),
            progressive_disclosure=skill_data.get('progressive_disclosure', {}),
            matching=skill_data.get('matching', {})
        )
        
        # Parse logging config
        logging_data = config_data.get('logging', {})
        logging_config = LoggingConfig(
            level=logging_data.get('level', 'INFO'),
            format=logging_data.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file=logging_data.get('file', {}),
            console=logging_data.get('console', {})
        )
        
        # Parse security config
        security_data = config_data.get('security', {})
        security_config = SecurityConfig(
            skills=security_data.get('skills', {}),
            data_protection=security_data.get('data_protection', {}),
            sandbox=security_data.get('sandbox', {})
        )
        
        # Parse performance config
        perf_data = config_data.get('performance', {})
        perf_config = PerformanceConfig(
            cache=perf_data.get('cache', {}),
            concurrency=perf_data.get('concurrency', {}),
            resources=perf_data.get('resources', {})
        )
        
        # Parse demo config
        demo_data = config_data.get('demo', {})
        demo_config = DemoConfig(
            scenarios=demo_data.get('scenarios', []),
            settings=demo_data.get('settings', {})
        )
        
        return Config(
            model=model_config,
            agent=agent_config,
            skill_manager=skill_config,
            logging=logging_config,
            security=security_config,
            performance=perf_config,
            demo=demo_config
        )
    
    def _get_default_config(self) -> Config:
        """Get default configuration.
        
        Returns:
            Config: Default configuration
        """
        return Config(
            model=ModelConfig(
                provider='dashscope',
                model_name='qwen-max',
                api_key_env='DASHSCOPE_API_KEY',
                parameters={'temperature': 0.7, 'max_tokens': 2000, 'stream': True},
                alternatives={}
            ),
            agent=AgentConfig(
                name='SkillMaster',
                auto_skill_discovery=True,
                skill_matching_threshold=0.7,
                max_iters=10,
                print_hint_msg=True,
                system_prompt=self._get_default_system_prompt()
            ),
            skill_manager=SkillManagerConfig(
                skill_directory='./skills',
                auto_reload=False,
                cache_enabled=True,
                progressive_disclosure={},
                matching={}
            ),
            logging=LoggingConfig(
                level='INFO',
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                file={},
                console={}
            ),
            security=SecurityConfig(
                skills={},
                data_protection={},
                sandbox={}
            ),
            performance=PerformanceConfig(
                cache={},
                concurrency={},
                resources={}
            ),
            demo=DemoConfig(
                scenarios=[],
                settings={}
            )
        )
    
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt.
        
        Returns:
            str: Default system prompt
        """
        return """You are an intelligent assistant with access to specialized skills.
        
        You can automatically detect when tasks require specific expertise and activate relevant skills.
        Always consider which skills might be helpful for the current task.
        
        Available skills will be automatically discovered and loaded as needed.
        You can use skill management tools to manually activate/deactivate skills if needed."""
    
    def get_model_config(self, provider: Optional[str] = None) -> ModelConfig:
        """Get model configuration for specific provider.
        
        Args:
            provider (Optional[str]): Model provider name
            
        Returns:
            ModelConfig: Model configuration
        """
        if not self._config:
            self.load_config()
        
        if self._config is None:
            # If config is still None after loading, return default
            return self._get_default_config().model
        
        if provider and provider in self._config.model.alternatives:
            alt_data = self._config.model.alternatives[provider]
            return ModelConfig(
                provider=alt_data.get('provider', provider),
                model_name=alt_data.get('model_name', 'gpt-4'),
                api_key_env=alt_data.get('api_key_env', 'OPENAI_API_KEY'),
                parameters=alt_data.get('parameters', {}),
                alternatives={}
            )
        
        return self._config.model
    
    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key for specific provider.
        
        Args:
            provider (Optional[str]): Model provider name
            
        Returns:
            Optional[str]: API key from config or environment
        """
        model_config = self.get_model_config(provider)
        
        # First try to get API key directly from config
        if hasattr(model_config, 'api_key') and model_config.api_key:
            return model_config.api_key
        
        # Fallback to environment variable
        return os.environ.get(model_config.api_key_env)
    
    def validate_config(self) -> bool:
        """Validate configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            if not self._config:
                self.load_config()
            
            # Check if config was loaded successfully
            if not self._config:
                logger.error("Failed to load configuration")
                return False
            
            # Check required API keys
            if not self.get_api_key():
                logger.error(f"API key not found for {self._config.model.provider}")
                logger.error(f"Set environment variable: {self._config.model.api_key_env}")
                return False
            
            # Check skill directory
            skill_dir = Path(self._config.skill_manager.skill_directory)
            if not skill_dir.exists():
                # Try relative path from config file
                config_dir = self.config_path.parent
                skill_dir = config_dir / self._config.skill_manager.skill_directory
                if not skill_dir.exists():
                    logger.error(f"Skill directory not found: {skill_dir}")
                    return False
            
            # Validate model configuration
            if not self._config.model.model_name:
                logger.error("Model name is required")
                return False
            
            # Validate agent configuration
            if self._config.agent.skill_matching_threshold < 0 or self._config.agent.skill_matching_threshold > 1:
                logger.error("Skill matching threshold must be between 0 and 1")
                return False
            
            if self._config.agent.max_iters <= 0:
                logger.error("Max iterations must be positive")
                return False
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            return False
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """Save current configuration to file.
        
        Args:
            config_path (Optional[str]): Path to save configuration
            
        Returns:
            bool: True if saved successfully
        """
        if not self._config:
            logger.error("No configuration to save")
            return False
        
        save_path = Path(config_path) if config_path else self.config_path
        
        try:
            # Validate save path
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert config to dictionary
            config_dict = {
                'model': {
                    'provider': self._config.model.provider,
                    'model_name': self._config.model.model_name,
                    'api_key_env': self._config.model.api_key_env,
                    'parameters': self._config.model.parameters,
                    'alternatives': self._config.model.alternatives
                },
                'agent': {
                    'name': self._config.agent.name,
                    'auto_skill_discovery': self._config.agent.auto_skill_discovery,
                    'skill_matching_threshold': self._config.agent.skill_matching_threshold,
                    'max_iters': self._config.agent.max_iters,
                    'print_hint_msg': self._config.agent.print_hint_msg,
                    'system_prompt': self._config.agent.system_prompt
                },
                'skill_manager': {
                    'skill_directory': self._config.skill_manager.skill_directory,
                    'auto_reload': self._config.skill_manager.auto_reload,
                    'cache_enabled': self._config.skill_manager.cache_enabled,
                    'progressive_disclosure': self._config.skill_manager.progressive_disclosure,
                    'matching': self._config.skill_manager.matching
                },
                'logging': {
                    'level': self._config.logging.level,
                    'format': self._config.logging.format,
                    'file': self._config.logging.file,
                    'console': self._config.logging.console
                },
                'security': {
                    'skills': self._config.security.skills,
                    'data_protection': self._config.security.data_protection,
                    'sandbox': self._config.security.sandbox
                },
                'performance': {
                    'cache': self._config.performance.cache,
                    'concurrency': self._config.performance.concurrency,
                    'resources': self._config.performance.resources
                },
                'demo': {
                    'scenarios': self._config.demo.scenarios,
                    'settings': self._config.demo.settings
                }
            }
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configuration saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False


# Global config loader instance
_config_loader = None


def get_config_loader(config_path: str = "config.yaml") -> ConfigLoader:
    """Get global config loader instance.
    
    Args:
        config_path (str): Path to configuration file
        
    Returns:
        ConfigLoader: Config loader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from file.
    
    Args:
        config_path (str): Path to configuration file
        
    Returns:
        Config: Loaded configuration
    """
    return get_config_loader(config_path).load_config()
