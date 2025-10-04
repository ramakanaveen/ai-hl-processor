"""
Configuration Management for Financial News Impact Analysis
Centralized configuration for POC and production deployments
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class Environment(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ModelProvider(Enum):
    GEMINI_FLASH = "gemini_flash"
    OPENAI_GPT4 = "openai_gpt4"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    MOCK_LLM = "mock_llm"


@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    provider: ModelProvider
    model_name: str
    api_key: Optional[str]
    project_id: Optional[str]
    region: str
    max_tokens: int
    temperature: float
    timeout_seconds: int
    rate_limit_rpm: int  # Requests per minute
    batch_size: int


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    username: str
    password: str
    database_name: str
    connection_pool_size: int
    ssl_mode: str


@dataclass
class CacheConfig:
    """Cache configuration"""
    redis_host: str
    redis_port: int
    redis_db: int
    cache_ttl_seconds: int
    max_memory_mb: int


@dataclass
class MessageQueueConfig:
    """Message queue configuration"""
    broker_type: str  # 'kafka', 'rabbitmq', 'redis'
    hosts: List[str]
    topic_prefix: str
    consumer_group: str
    batch_size: int
    timeout_ms: int


@dataclass
class MonitoringConfig:
    """Monitoring and alerting configuration"""
    prometheus_enabled: bool
    prometheus_port: int
    log_level: str
    sentry_dsn: Optional[str]
    alert_webhooks: List[str]


@dataclass
class PerformanceConfig:
    """Performance and scaling configuration"""
    max_concurrent_llm_calls: int
    max_entities_per_analysis: int
    feature_cache_enabled: bool
    async_processing_enabled: bool
    processing_timeout_seconds: int
    retry_attempts: int
    backoff_multiplier: float


@dataclass
class SecurityConfig:
    """Security configuration"""
    api_key_encryption_enabled: bool
    rate_limiting_enabled: bool
    request_validation_enabled: bool
    audit_logging_enabled: bool
    allowed_origins: List[str]
    jwt_secret_key: Optional[str]


class ConfigManager:
    """Centralized configuration management"""

    def __init__(self, environment: Environment = Environment.DEVELOPMENT):
        self.environment = environment
        self.config_dir = Path(__file__).parent / "configs"
        self.config_dir.mkdir(exist_ok=True)

        # Load configuration
        self._load_configuration()

    def _load_configuration(self):
        """Load configuration based on environment"""

        # Load base configuration
        base_config = self._get_base_config()

        # Load environment-specific overrides
        env_config = self._get_environment_config()

        # Merge configurations
        self.config = {**base_config, **env_config}

        # Initialize typed configuration objects
        self._initialize_typed_configs()

    def _get_base_config(self) -> Dict[str, Any]:
        """Get base configuration common to all environments"""
        return {
            "llm": {
                "provider": "gemini_flash",
                "model_name": "gemini-flash-lite-latest",
                "region": "us-central1",
                "max_tokens": 2048,
                "temperature": 0.3,
                "timeout_seconds": 30,
                "rate_limit_rpm": 60,
                "batch_size": 10
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "username": "finance_user",
                "database_name": "financial_news_db",
                "connection_pool_size": 10,
                "ssl_mode": "prefer"
            },
            "cache": {
                "redis_host": "localhost",
                "redis_port": 6379,
                "redis_db": 0,
                "cache_ttl_seconds": 300,
                "max_memory_mb": 512
            },
            "message_queue": {
                "broker_type": "redis",
                "hosts": ["localhost:6379"],
                "topic_prefix": "financial_news",
                "consumer_group": "impact_analyzer",
                "batch_size": 50,
                "timeout_ms": 10000
            },
            "monitoring": {
                "prometheus_enabled": True,
                "prometheus_port": 8000,
                "log_level": "INFO",
                "sentry_dsn": None,
                "alert_webhooks": []
            },
            "performance": {
                "max_concurrent_llm_calls": 5,
                "max_entities_per_analysis": 20,
                "feature_cache_enabled": True,
                "async_processing_enabled": True,
                "processing_timeout_seconds": 120,
                "retry_attempts": 3,
                "backoff_multiplier": 1.5
            },
            "security": {
                "api_key_encryption_enabled": True,
                "rate_limiting_enabled": True,
                "request_validation_enabled": True,
                "audit_logging_enabled": True,
                "allowed_origins": ["http://localhost:3000"],
                "jwt_secret_key": None
            },
            "business": {
                "supported_currencies": [
                    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
                    "USDCHF", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY"
                ],
                "supported_commodities": [
                    "XAUUSD", "XAGUSD", "WTI", "BRENT", "NATGAS"
                ],
                "impact_threshold_minor": 0.02,    # 2%
                "impact_threshold_moderate": 0.05,  # 5%
                "impact_threshold_major": 0.10,    # 10%
                "confidence_threshold": 0.7,
                "analysis_window_hours": 24
            }
        }

    def _get_environment_config(self) -> Dict[str, Any]:
        """Get environment-specific configuration overrides"""

        if self.environment == Environment.DEVELOPMENT:
            return self._get_development_config()
        elif self.environment == Environment.TESTING:
            return self._get_testing_config()
        elif self.environment == Environment.STAGING:
            return self._get_staging_config()
        elif self.environment == Environment.PRODUCTION:
            return self._get_production_config()
        else:
            return {}

    def _get_development_config(self) -> Dict[str, Any]:
        """Development environment configuration"""
        return {
            "llm": {
                "provider": "mock_llm",  # Use mock for development
                "rate_limit_rpm": 120
            },
            "monitoring": {
                "log_level": "DEBUG",
                "prometheus_enabled": False
            },
            "performance": {
                "max_concurrent_llm_calls": 2,
                "feature_cache_enabled": False,  # Disable for easier debugging
                "processing_timeout_seconds": 60
            },
            "security": {
                "rate_limiting_enabled": False,
                "request_validation_enabled": False
            }
        }

    def _get_testing_config(self) -> Dict[str, Any]:
        """Testing environment configuration"""
        return {
            "llm": {
                "provider": "mock_llm",
                "timeout_seconds": 10
            },
            "database": {
                "database_name": "financial_news_test_db"
            },
            "cache": {
                "redis_db": 1,  # Use different Redis DB for tests
                "cache_ttl_seconds": 30
            },
            "monitoring": {
                "log_level": "WARNING",
                "prometheus_enabled": False
            },
            "performance": {
                "max_concurrent_llm_calls": 1,
                "processing_timeout_seconds": 30,
                "retry_attempts": 1
            }
        }

    def _get_staging_config(self) -> Dict[str, Any]:
        """Staging environment configuration"""
        return {
            "llm": {
                "provider": "gemini_flash",
                "rate_limit_rpm": 100
            },
            "monitoring": {
                "log_level": "INFO",
                "prometheus_enabled": True
            },
            "performance": {
                "max_concurrent_llm_calls": 3,
                "processing_timeout_seconds": 90
            },
            "security": {
                "audit_logging_enabled": True
            }
        }

    def _get_production_config(self) -> Dict[str, Any]:
        """Production environment configuration"""
        return {
            "llm": {
                "provider": "gemini_flash",
                "rate_limit_rpm": 300,
                "timeout_seconds": 60
            },
            "database": {
                "connection_pool_size": 20,
                "ssl_mode": "require"
            },
            "cache": {
                "max_memory_mb": 2048
            },
            "message_queue": {
                "batch_size": 100
            },
            "monitoring": {
                "log_level": "WARNING",
                "prometheus_enabled": True,
                "alert_webhooks": [
                    os.getenv("SLACK_WEBHOOK_URL"),
                    os.getenv("PAGERDUTY_WEBHOOK_URL")
                ]
            },
            "performance": {
                "max_concurrent_llm_calls": 10,
                "max_entities_per_analysis": 50,
                "processing_timeout_seconds": 180
            },
            "security": {
                "api_key_encryption_enabled": True,
                "rate_limiting_enabled": True,
                "request_validation_enabled": True,
                "audit_logging_enabled": True
            }
        }

    def _initialize_typed_configs(self):
        """Initialize typed configuration objects"""

        self.llm_config = LLMConfig(
            provider=ModelProvider(self.config["llm"]["provider"]),
            model_name=self.config["llm"]["model_name"],
            api_key=os.getenv("VERTEX_AI_API_KEY") or os.getenv("OPENAI_API_KEY"),
            project_id=os.getenv("GOOGLE_CLOUD_PROJECT"),
            region=self.config["llm"]["region"],
            max_tokens=self.config["llm"]["max_tokens"],
            temperature=self.config["llm"]["temperature"],
            timeout_seconds=self.config["llm"]["timeout_seconds"],
            rate_limit_rpm=self.config["llm"]["rate_limit_rpm"],
            batch_size=self.config["llm"]["batch_size"]
        )

        self.database_config = DatabaseConfig(
            host=os.getenv("DB_HOST", self.config["database"]["host"]),
            port=int(os.getenv("DB_PORT", str(self.config["database"]["port"]))),
            username=os.getenv("DB_USERNAME", self.config["database"]["username"]),
            password=os.getenv("DB_PASSWORD", ""),
            database_name=os.getenv("DB_NAME", self.config["database"]["database_name"]),
            connection_pool_size=self.config["database"]["connection_pool_size"],
            ssl_mode=self.config["database"]["ssl_mode"]
        )

        self.cache_config = CacheConfig(
            redis_host=os.getenv("REDIS_HOST", self.config["cache"]["redis_host"]),
            redis_port=int(os.getenv("REDIS_PORT", str(self.config["cache"]["redis_port"]))),
            redis_db=self.config["cache"]["redis_db"],
            cache_ttl_seconds=self.config["cache"]["cache_ttl_seconds"],
            max_memory_mb=self.config["cache"]["max_memory_mb"]
        )

        self.message_queue_config = MessageQueueConfig(
            broker_type=self.config["message_queue"]["broker_type"],
            hosts=self.config["message_queue"]["hosts"],
            topic_prefix=self.config["message_queue"]["topic_prefix"],
            consumer_group=self.config["message_queue"]["consumer_group"],
            batch_size=self.config["message_queue"]["batch_size"],
            timeout_ms=self.config["message_queue"]["timeout_ms"]
        )

        self.monitoring_config = MonitoringConfig(
            prometheus_enabled=self.config["monitoring"]["prometheus_enabled"],
            prometheus_port=self.config["monitoring"]["prometheus_port"],
            log_level=self.config["monitoring"]["log_level"],
            sentry_dsn=os.getenv("SENTRY_DSN"),
            alert_webhooks=[url for url in self.config["monitoring"]["alert_webhooks"] if url]
        )

        self.performance_config = PerformanceConfig(
            max_concurrent_llm_calls=self.config["performance"]["max_concurrent_llm_calls"],
            max_entities_per_analysis=self.config["performance"]["max_entities_per_analysis"],
            feature_cache_enabled=self.config["performance"]["feature_cache_enabled"],
            async_processing_enabled=self.config["performance"]["async_processing_enabled"],
            processing_timeout_seconds=self.config["performance"]["processing_timeout_seconds"],
            retry_attempts=self.config["performance"]["retry_attempts"],
            backoff_multiplier=self.config["performance"]["backoff_multiplier"]
        )

        self.security_config = SecurityConfig(
            api_key_encryption_enabled=self.config["security"]["api_key_encryption_enabled"],
            rate_limiting_enabled=self.config["security"]["rate_limiting_enabled"],
            request_validation_enabled=self.config["security"]["request_validation_enabled"],
            audit_logging_enabled=self.config["security"]["audit_logging_enabled"],
            allowed_origins=self.config["security"]["allowed_origins"],
            jwt_secret_key=os.getenv("JWT_SECRET_KEY")
        )

    def get_connection_string(self) -> str:
        """Get database connection string"""
        return (
            f"postgresql://{self.database_config.username}:{self.database_config.password}"
            f"@{self.database_config.host}:{self.database_config.port}"
            f"/{self.database_config.database_name}?sslmode={self.database_config.ssl_mode}"
        )

    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        return f"redis://{self.cache_config.redis_host}:{self.cache_config.redis_port}/{self.cache_config.redis_db}"

    def save_config_to_file(self, filename: str = None):
        """Save current configuration to file"""
        if filename is None:
            filename = f"config_{self.environment.value}.json"

        config_file = self.config_dir / filename

        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2, default=str)

        return str(config_file)

    def load_config_from_file(self, filename: str):
        """Load configuration from file"""
        config_file = self.config_dir / filename

        if config_file.exists():
            with open(config_file, 'r') as f:
                file_config = json.load(f)

            # Merge with current config
            self.config = {**self.config, **file_config}
            self._initialize_typed_configs()

    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []

        # Validate LLM configuration
        if self.llm_config.provider == ModelProvider.GEMINI_FLASH:
            if not self.llm_config.project_id:
                issues.append("Google Cloud project ID is required for Gemini Flash")

        # Validate database configuration
        if not self.database_config.password and self.environment == Environment.PRODUCTION:
            issues.append("Database password is required in production")

        # Validate security configuration
        if self.environment == Environment.PRODUCTION:
            if not self.security_config.jwt_secret_key:
                issues.append("JWT secret key is required in production")

        # Validate monitoring configuration
        if self.monitoring_config.prometheus_enabled and not self.monitoring_config.prometheus_port:
            issues.append("Prometheus port must be specified when Prometheus is enabled")

        return issues

    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags for conditional functionality"""
        return {
            "semantic_analysis_enabled": True,
            "economic_graph_enabled": True,
            "real_time_processing": self.environment == Environment.PRODUCTION,
            "advanced_sentiment_analysis": self.environment in [Environment.STAGING, Environment.PRODUCTION],
            "model_ensemble_enabled": self.environment == Environment.PRODUCTION,
            "historical_backtesting": True,
            "api_rate_limiting": self.security_config.rate_limiting_enabled,
            "audit_logging": self.security_config.audit_logging_enabled
        }


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config(environment: Environment = None) -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager

    if _config_manager is None or (environment and _config_manager.environment != environment):
        if environment is None:
            # Determine environment from environment variable
            env_str = os.getenv("ENVIRONMENT", "development").lower()
            environment = Environment(env_str)

        _config_manager = ConfigManager(environment)

    return _config_manager


def initialize_config(environment: Environment = None, config_file: str = None) -> ConfigManager:
    """Initialize configuration manager"""
    config_manager = get_config(environment)

    if config_file:
        config_manager.load_config_from_file(config_file)

    # Validate configuration
    issues = config_manager.validate_configuration()
    if issues:
        import warnings
        for issue in issues:
            warnings.warn(f"Configuration issue: {issue}")

    return config_manager


# Example usage and testing
if __name__ == "__main__":
    def test_configuration():
        """Test configuration management"""

        print("=== Configuration Management Test ===\n")

        # Test different environments
        environments = [Environment.DEVELOPMENT, Environment.TESTING, Environment.PRODUCTION]

        for env in environments:
            print(f"--- {env.value.upper()} Environment ---")

            config = ConfigManager(env)

            print(f"LLM Provider: {config.llm_config.provider.value}")
            print(f"Model Name: {config.llm_config.model_name}")
            print(f"Max Concurrent Calls: {config.performance_config.max_concurrent_llm_calls}")
            print(f"Cache Enabled: {config.performance_config.feature_cache_enabled}")
            print(f"Log Level: {config.monitoring_config.log_level}")

            # Validate configuration
            issues = config.validate_configuration()
            if issues:
                print(f"Configuration Issues: {issues}")
            else:
                print("Configuration is valid")

            # Test feature flags
            flags = config.get_feature_flags()
            print(f"Feature Flags: {list(flags.keys())}")

            print()

        # Test configuration file save/load
        print("--- Configuration File Operations ---")
        dev_config = ConfigManager(Environment.DEVELOPMENT)
        saved_file = dev_config.save_config_to_file()
        print(f"Configuration saved to: {saved_file}")

    test_configuration()