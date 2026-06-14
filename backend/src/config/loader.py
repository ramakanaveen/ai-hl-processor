"""
Configuration Loader for Financial News Impact Analysis
Loads environment-specific configuration from config.ini file
"""

import os
import configparser
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ModelConfig:
    """Model configuration parameters"""
    model_name: str
    provider: str
    use_mock_llm: bool
    google_cloud_region: str
    max_tokens: int
    temperature: float
    timeout_seconds: int
    rate_limit_rpm: int
    batch_size: int


@dataclass
class PerformanceConfig:
    """Performance configuration parameters"""
    max_concurrent_llm_calls: int
    max_entities_per_analysis: int
    processing_timeout_seconds: int
    retry_attempts: int
    feature_cache_enabled: bool


@dataclass
class MonitoringConfig:
    """Monitoring configuration parameters"""
    log_level: str
    prometheus_enabled: bool
    rate_limiting_enabled: bool
    request_validation_enabled: bool
    audit_logging_enabled: bool


@dataclass
class BusinessConfig:
    """Business logic configuration"""
    supported_currencies: List[str]
    supported_commodities: List[str]
    impact_threshold_minor: float
    impact_threshold_moderate: float
    impact_threshold_major: float
    confidence_threshold: float
    analysis_window_hours: int


@dataclass
class RelevanceFilterConfig:
    """Pre-LLM relevance gate configuration"""
    enabled: bool
    mode: str                 # "shadow" | "enforce"
    model_path: str
    encoder: str
    drop_threshold: float
    pass_threshold: float
    allowlist_terms: List[str]
    min_training_samples: int


class ConfigLoader:
    """Loads configuration from config.ini file"""

    def __init__(self, config_file: str = "config.ini", environment: str = None):
        self.config_file = Path(config_file)
        self.environment = environment or os.getenv("ENV", "test")

        # Load configuration
        self.config = configparser.ConfigParser()
        self._load_config_file()

        # Initialize typed configurations
        self.model_config = self._load_model_config()
        self.performance_config = self._load_performance_config()
        self.monitoring_config = self._load_monitoring_config()
        self.business_config = self._load_business_config()

    def _load_config_file(self):
        """Load the configuration file"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")

        self.config.read(self.config_file)

    def _get_value(self, section: str, key: str, fallback: Any = None, value_type: type = str) -> Any:
        """Get configuration value with type conversion and fallback"""
        try:
            # Try environment-specific section first
            env_section = f"{section}:{self.environment}"
            if self.config.has_section(env_section) and self.config.has_option(env_section, key):
                value = self.config.get(env_section, key)
            elif self.config.has_option(self.environment, key):
                value = self.config.get(self.environment, key)
            elif self.config.has_option(section, key):
                value = self.config.get(section, key)
            else:
                return fallback

            # Type conversion
            if value_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif value_type == int:
                return int(value)
            elif value_type == float:
                return float(value)
            elif value_type == list:
                return [item.strip() for item in value.split(',')]
            else:
                return value

        except (ValueError, configparser.NoSectionError, configparser.NoOptionError):
            return fallback

    def _load_model_config(self) -> ModelConfig:
        """Load model configuration"""
        return ModelConfig(
            model_name=self._get_value("DEFAULT", "model_name", "gemini-flash-lite-latest"),
            provider=self._get_value("DEFAULT", "provider", "gemini_flash"),
            use_mock_llm=self._get_value("DEFAULT", "use_mock_llm", False, bool),
            google_cloud_region=self._get_value("DEFAULT", "google_cloud_region", "us-central1"),
            max_tokens=self._get_value("DEFAULT", "max_tokens", 2048, int),
            temperature=self._get_value("DEFAULT", "temperature", 0.3, float),
            timeout_seconds=self._get_value("DEFAULT", "timeout_seconds", 30, int),
            rate_limit_rpm=self._get_value("DEFAULT", "rate_limit_rpm", 60, int),
            batch_size=self._get_value("DEFAULT", "batch_size", 10, int)
        )

    def _load_performance_config(self) -> PerformanceConfig:
        """Load performance configuration"""
        return PerformanceConfig(
            max_concurrent_llm_calls=self._get_value("DEFAULT", "max_concurrent_llm_calls", 5, int),
            max_entities_per_analysis=self._get_value("DEFAULT", "max_entities_per_analysis", 20, int),
            processing_timeout_seconds=self._get_value("DEFAULT", "processing_timeout_seconds", 120, int),
            retry_attempts=self._get_value("DEFAULT", "retry_attempts", 3, int),
            feature_cache_enabled=self._get_value("DEFAULT", "feature_cache_enabled", True, bool)
        )

    def _load_monitoring_config(self) -> MonitoringConfig:
        """Load monitoring configuration"""
        return MonitoringConfig(
            log_level=self._get_value("DEFAULT", "log_level", "INFO"),
            prometheus_enabled=self._get_value("DEFAULT", "prometheus_enabled", True, bool),
            rate_limiting_enabled=self._get_value("DEFAULT", "rate_limiting_enabled", True, bool),
            request_validation_enabled=self._get_value("DEFAULT", "request_validation_enabled", True, bool),
            audit_logging_enabled=self._get_value("DEFAULT", "audit_logging_enabled", True, bool)
        )

    def _load_business_config(self) -> BusinessConfig:
        """Load business configuration"""
        return BusinessConfig(
            supported_currencies=self._get_value("business", "supported_currencies",
                                                ["EURUSD", "GBPUSD", "USDJPY"], list),
            supported_commodities=self._get_value("business", "supported_commodities",
                                                 ["XAUUSD", "WTI", "BRENT"], list),
            impact_threshold_minor=self._get_value("business", "impact_threshold_minor", 0.02, float),
            impact_threshold_moderate=self._get_value("business", "impact_threshold_moderate", 0.05, float),
            impact_threshold_major=self._get_value("business", "impact_threshold_major", 0.10, float),
            confidence_threshold=self._get_value("business", "confidence_threshold", 0.7, float),
            analysis_window_hours=self._get_value("business", "analysis_window_hours", 24, int)
        )

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'host': os.getenv("DB_HOST", self._get_value("database", "host", "localhost")),
            'port': int(os.getenv("DB_PORT", str(self._get_value("database", "port", 5432, int)))),
            'username': os.getenv("DB_USERNAME", self._get_value("database", "username", "finance_user")),
            'password': os.getenv("DB_PASSWORD", ""),
            'database_name': os.getenv("DB_NAME", self._get_value("database", "database_name", "financial_news_db")),
            'connection_pool_size': self._get_value("database", "connection_pool_size", 10, int),
            'ssl_mode': self._get_value("database", "ssl_mode", "prefer")
        }

    def get_cache_config(self) -> Dict[str, Any]:
        """Get Redis connection configuration."""
        return {
            'redis_host': os.getenv("REDIS_HOST", self._get_value("cache", "redis_host", "localhost")),
            'redis_port': int(os.getenv("REDIS_PORT", str(self._get_value("cache", "redis_port", 6379, int)))),
            'redis_db': self._get_value("cache", "redis_db", 0, int),
            'cache_ttl_seconds': self._get_value("cache", "cache_ttl_seconds", 86400, int),
        }

    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis behaviour and enterprise settings."""
        return {
            'active_impact_window_minutes': self._get_value("cache", "active_impact_window_minutes", 60, int),
            'password': os.getenv("REDIS_PASSWORD", self._get_value("cache", "redis_password", None)) or None,
            'ssl': os.getenv("REDIS_SSL", self._get_value("cache", "redis_ssl", "false")).lower() == "true",
            'ssl_cert_reqs': os.getenv("REDIS_SSL_CERT_REQS", self._get_value("cache", "redis_ssl_cert_reqs", "required")),
            'socket_timeout': int(os.getenv("REDIS_SOCKET_TIMEOUT", str(self._get_value("cache", "redis_socket_timeout", 5, int)))),
            'socket_connect_timeout': int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", str(self._get_value("cache", "redis_socket_connect_timeout", 5, int)))),
            'max_connections': int(os.getenv("REDIS_MAX_CONNECTIONS", str(self._get_value("cache", "redis_max_connections", 10, int)))),
        }

    def get_relevance_filter_config(self) -> RelevanceFilterConfig:
        """Get the pre-LLM relevance gate configuration."""
        return RelevanceFilterConfig(
            enabled=self._get_value("relevance_filter", "enabled", False, bool),
            mode=self._get_value("relevance_filter", "mode", "shadow"),
            model_path=self._get_value(
                "relevance_filter", "model_path", "models/relevance/model.joblib"
            ),
            encoder=self._get_value("relevance_filter", "encoder", "tfidf_domain_v1"),
            drop_threshold=self._get_value("relevance_filter", "drop_threshold", 0.05, float),
            pass_threshold=self._get_value("relevance_filter", "pass_threshold", 0.5, float),
            allowlist_terms=self._get_value(
                "relevance_filter", "allowlist_terms",
                ["fed", "ecb", "boj", "boe", "powell", "lagarde", "ueda"], list,
            ),
            min_training_samples=self._get_value(
                "relevance_filter", "min_training_samples", 60, int
            ),
        )

    def get_google_cloud_config(self) -> Dict[str, Any]:
        """Get Google Cloud configuration"""
        return {
            'project_id': os.getenv("GOOGLE_CLOUD_PROJECT"),
            'credentials_path': os.getenv("GOOGLE_CREDENTIALS_PATH"),
            'region': self.model_config.google_cloud_region,
            'model_name': self.model_config.model_name
        }

    def get_feed_config(self) -> Dict[str, Any]:
        """Get Kafka and file-source feed configuration."""
        return {
            'kafka_bootstrap_servers': self._get_value(
                "feeds", "kafka_bootstrap_servers", "localhost:9092"
            ),
            'kafka_input_topic': self._get_value(
                "feeds", "kafka_input_topic", "raw-headlines"
            ),
            'kafka_output_topic': self._get_value(
                "feeds", "kafka_output_topic", "headline-impacts"
            ),
            'kafka_consumer_group': self._get_value(
                "feeds", "kafka_consumer_group", "hl-analyzer"
            ),
            'kafka_sse_consumer_group': self._get_value(
                "feeds", "kafka_sse_consumer_group", "sse-server"
            ),
            'file_source_rate_per_second': self._get_value(
                "feeds", "file_source_rate_per_second", 1.0, float
            ),
        }

    def get_kdb_config(self) -> Dict[str, Any]:
        """Get KDB+ source configuration."""
        return {
            'host': os.getenv("KDB_HOST", self._get_value("kdb", "host", "localhost")),
            'port': int(os.getenv("KDB_PORT", str(self._get_value("kdb", "port", 5000, int)))),
            'query': self._get_value("kdb", "query", "select text, source, time from headlines where date=.z.d"),
            'poll_interval_seconds': self._get_value("kdb", "poll_interval_seconds", 60, int),
            'username': os.getenv("KDB_USERNAME", self._get_value("kdb", "username", None)) or None,
            'password': os.getenv("KDB_PASSWORD", self._get_value("kdb", "password", None)) or None,
        }

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {
            'environment': self.environment,
            'model': self.model_config.__dict__,
            'performance': self.performance_config.__dict__,
            'monitoring': self.monitoring_config.__dict__,
            'business': self.business_config.__dict__,
            'database': self.get_database_config(),
            'cache': self.get_cache_config(),
            'google_cloud': self.get_google_cloud_config()
        }

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []

        # Validate Google Cloud configuration
        gc_config = self.get_google_cloud_config()
        if not self.model_config.use_mock_llm:
            if not gc_config['project_id']:
                issues.append("GOOGLE_CLOUD_PROJECT environment variable is required when not using mock LLM")
            if not gc_config['credentials_path']:
                issues.append("GOOGLE_CREDENTIALS_PATH environment variable is required when not using mock LLM")

        # Validate business thresholds
        if self.business_config.impact_threshold_minor >= self.business_config.impact_threshold_moderate:
            issues.append("Minor impact threshold must be less than moderate threshold")
        if self.business_config.impact_threshold_moderate >= self.business_config.impact_threshold_major:
            issues.append("Moderate impact threshold must be less than major threshold")

        # Validate performance settings
        if self.performance_config.max_concurrent_llm_calls < 1:
            issues.append("max_concurrent_llm_calls must be at least 1")
        if self.performance_config.max_entities_per_analysis < 1:
            issues.append("max_entities_per_analysis must be at least 1")

        return issues

    def print_config_summary(self):
        """Print a summary of the current configuration"""
        print(f"=== Configuration Summary ({self.environment.upper()}) ===")
        print(f"Model: {self.model_config.model_name}")
        print(f"Provider: {self.model_config.provider}")
        print(f"Use Mock LLM: {self.model_config.use_mock_llm}")
        print(f"Region: {self.model_config.google_cloud_region}")
        print(f"Max Concurrent Calls: {self.performance_config.max_concurrent_llm_calls}")
        print(f"Max Entities: {self.performance_config.max_entities_per_analysis}")
        print(f"Log Level: {self.monitoring_config.log_level}")

        # Show validation issues
        issues = self.validate_config()
        if issues:
            print("⚠️  Configuration Issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ Configuration is valid")


# Global configuration instance
_config_loader: Optional[ConfigLoader] = None


def get_config(environment: str = None, config_file: str = "config.ini") -> ConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader

    if _config_loader is None or (environment and _config_loader.environment != environment):
        _config_loader = ConfigLoader(config_file, environment)

    return _config_loader


def load_config(environment: str = None, config_file: str = "config.ini") -> ConfigLoader:
    """Load and return configuration"""
    return get_config(environment, config_file)


# Example usage and testing
if __name__ == "__main__":
    def test_config_loader():
        """Test the configuration loader"""
        print("=== Configuration Loader Test ===\n")

        # Test different environments
        environments = ["test", "dev", "uat", "prod"]

        for env in environments:
            print(f"--- {env.upper()} Environment ---")

            config = ConfigLoader(environment=env)
            config.print_config_summary()
            print()

        # Test configuration validation
        print("--- Configuration Validation ---")
        config = ConfigLoader(environment="prod")
        issues = config.validate_config()
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("All configurations are valid")

    test_config_loader()