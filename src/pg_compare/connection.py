"""Database connection management for PostgreSQL comparison."""

from dataclasses import dataclass
from typing import Optional
from contextlib import contextmanager
import psycopg2
from psycopg2.extensions import connection as PgConnection


@dataclass
class ConnectionConfig:
    """Configuration for a PostgreSQL database connection."""
    host: str
    port: int
    database: str
    user: str
    password: str
    
    @classmethod
    def from_url(cls, url: str) -> "ConnectionConfig":
        """Parse a PostgreSQL connection URL."""
        # postgresql://user:password@host:port/database
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/") if parsed.path else "postgres",
            user=parsed.username or "postgres",
            password=parsed.password or "",
        )
    
    @classmethod
    def from_dict(cls, config: dict) -> "ConnectionConfig":
        """Create config from dictionary."""
        return cls(
            host=config.get("host", "localhost"),
            port=int(config.get("port", 5432)),
            database=config.get("database", "postgres"),
            user=config.get("user", "postgres"),
            password=config.get("password", ""),
        )
    
    def to_dsn(self) -> str:
        """Convert to DSN string."""
        return f"host={self.host} port={self.port} dbname={self.database} user={self.user} password={self.password}"


class DatabaseConnection:
    """Manages a PostgreSQL database connection."""
    
    def __init__(self, config: ConnectionConfig, name: Optional[str] = None):
        self.config = config
        self.name = name or f"{config.database}@{config.host}"
        self._connection: Optional[PgConnection] = None
    
    def connect(self) -> PgConnection:
        """Establish database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                dbname=self.config.database,
                user=self.config.user,
                password=self.config.password,
            )
        return self._connection
    
    def close(self):
        """Close the database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
    
    @property
    def connection(self) -> PgConnection:
        """Get or create the database connection."""
        return self.connect()
    
    def execute(self, query: str, params: Optional[tuple] = None) -> list:
        """Execute a query and return all results."""
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_one(self, query: str, params: Optional[tuple] = None):
        """Execute a query and return a single result."""
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else None
    
    def execute_dict(self, query: str, params: Optional[tuple] = None) -> list[dict]:
        """Execute a query and return results as list of dictionaries."""
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


@contextmanager
def dual_connection(source_config: ConnectionConfig, target_config: ConnectionConfig):
    """Context manager for connecting to two databases simultaneously."""
    source = DatabaseConnection(source_config, name="source")
    target = DatabaseConnection(target_config, name="target")
    try:
        source.connect()
        target.connect()
        yield source, target
    finally:
        source.close()
        target.close()
