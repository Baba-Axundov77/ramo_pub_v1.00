# config/settings.py - Modern Pydantic Settings Configuration
from __future__ import annotations
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from pydantic import field_validator
except ImportError:
    from pydantic import validator as field_validator

class DatabaseSettings(BaseSettings):
    """Database configuration with Pydantic validation"""
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'  # Allow extra fields from .env
    )
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    database: str = Field(default="ramo_pub", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="password", description="Database password")
    
    # Connection pool settings (SQLAlchemy Engine Configuration)
    pool_size: int = Field(default=20, description="Size of the connection pool")
    max_overflow: int = Field(default=10, description="Maximum overflow size of the pool")
    pool_timeout: int = Field(default=30, description="Timeout for getting a connection from the pool")
    pool_recycle: int = Field(default=3600, description="Recycle connections after N seconds (prevents stale connections)")
    pool_pre_ping: bool = Field(default=True, description="Ping connections before use")
    echo: bool = Field(default=False, description="Log all SQL statements")
    
    # Advanced pool settings
    pool_reset_on_return: str = Field(default="commit", description="What to do with connections when returned to pool")
    connect_args: dict = Field(default_factory=dict, description="Additional connection arguments")
    
    @property
    def url(self) -> str:
        """Generate database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def engine_kwargs(self) -> dict:
        """Generate SQLAlchemy engine configuration with pool settings"""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "pool_reset_on_return": self.pool_reset_on_return,
            "echo": self.echo,
            "connect_args": {
                **self.connect_args,
                "application_name": "ramo_pub_erp",
                "connect_timeout": 10,
            }
        }
    
    def get_pool_stats(self) -> dict:
        """Get pool configuration summary for monitoring"""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "total_connections": self.pool_size + self.max_overflow,
            "pool_recycle_seconds": self.pool_recycle,
            "pool_timeout_seconds": self.pool_timeout,
            "pre_ping_enabled": self.pool_pre_ping,
            "reset_on_return": self.pool_reset_on_return
        }
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @field_validator('pool_size')
    @classmethod
    def validate_pool_size(cls, v):
        if v < 1:
            raise ValueError('Pool size must be at least 1')
        if v > 100:
            raise ValueError('Pool size should not exceed 100 for optimal performance')
        return v
    
    @field_validator('max_overflow')
    @classmethod
    def validate_max_overflow(cls, v):
        if v < 0:
            raise ValueError('Max overflow cannot be negative')
        if v > 50:
            raise ValueError('Max overflow should not exceed 50')
        return v
    
    @field_validator('pool_recycle')
    @classmethod
    def validate_pool_recycle(cls, v):
        if v < 300:  # 5 minutes minimum
            raise ValueError('Pool recycle should be at least 300 seconds (5 minutes)')
        if v > 86400:  # 24 hours maximum
            raise ValueError('Pool recycle should not exceed 86400 seconds (24 hours)')
        return v
    
    @field_validator('pool_reset_on_return')
    @classmethod
    def validate_pool_reset_on_return(cls, v):
        valid_values = ['commit', 'rollback', None]
        if v not in valid_values:
            raise ValueError(f'pool_reset_on_return must be one of: {valid_values}')
        return v

class RedisSettings(BaseSettings):
    """Redis configuration with Pydantic validation"""
    
    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'  # Allow extra fields from .env
    )
    
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, description="Redis database number")
    password: Optional[str] = Field(default=None, description="Redis password")
    
    # Connection settings
    max_connections: int = Field(default=10, description="Maximum Redis connections")
    socket_timeout: int = Field(default=5, description="Socket timeout in seconds")
    
    @property
    def url(self) -> str:
        """Generate Redis URL"""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"

class FlaskSettings(BaseSettings):
    """Flask application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'  # Allow extra fields from .env
    )
    
    secret_key: str = Field(description="Flask secret key")
    debug: bool = Field(default=False, description="Debug mode")
    testing: bool = Field(default=False, description="Testing mode")
    
    # CORS settings
    cors_origins: str = Field(default="*", description="CORS allowed origins (comma-separated)")
    
    # Rate limiting
    rate_limit: str = Field(default="100/hour", description="Rate limit string")
    
    # Session settings
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")

class LoggingSettings(BaseSettings):
    """Logging configuration"""
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'  # Allow extra fields from .env
    )
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    file_path: Optional[str] = Field(default=None, description="Log file path")
    max_bytes: int = Field(default=10485760, description="Max log file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup files")

class Settings(BaseSettings):
    """Main application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore'  # Allow extra fields from .env
    )
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    flask: FlaskSettings = Field(default_factory=FlaskSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    
    # Application settings
    app_name: str = Field(default="Ramo Pub", description="Application name")
    version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment")
    
    # Business settings
    currency: str = Field(default="AZN", description="Currency code")
    timezone: str = Field(default="Asia/Baku", description="Timezone")
    
    # Security settings
    jwt_secret_key: str = Field(description="JWT secret key")
    jwt_expiration_hours: int = Field(default=24, description="JWT expiration in hours")
    
    # File upload settings
    max_file_size: int = Field(default=10485760, description="Max file size in bytes")
    upload_folder: str = Field(default="uploads", description="Upload folder")
    
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        valid_envs = ['development', 'testing', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v

# Global settings instance
settings = Settings()

# Convenience properties
db_settings = settings.database
redis_settings = settings.redis
flask_settings = settings.flask
log_settings = settings.logging
