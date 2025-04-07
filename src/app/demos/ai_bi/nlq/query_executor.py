import json
import logging
import re
from time import perf_counter
from typing import Dict, Optional

import psycopg2
from psycopg2 import pool

from src.app.demos.ai_bi.nlq.dtos import SqlResultDTO
from src.app.demos.ai_bi.nlq.llm_nlq.errors import SqlExecutionError, UnsafeQueryError
from src.config.vars_grabber import VariablesGrabber
from src.utils.metaclasses import DynamicSingleton

logger = logging.getLogger(__name__)

DEMO_AIBI_CREDENTIALS_SECRET_ARN = VariablesGrabber().get("DEMO_AIBI_DB_SECRET_ARN")

# Connection pool settings
MIN_CONNECTIONS = 1
MAX_CONNECTIONS = 10
POOL_KEEPALIVE_SECONDS = 300  # 5 minutes

UNSAFE_OPERATIONS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bEXECUTE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
]


class AibiQueryExecutor(metaclass=DynamicSingleton):
    # Public:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dbname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_timeout: int = 10,
    ):
        self.__host = host or VariablesGrabber().get("DEMO_AIBI_DB_HOST")
        self.__port = port or int(VariablesGrabber().get("DEMO_AIBI_DB_PORT") or "5432")
        self.__dbname = dbname or VariablesGrabber().get("DEMO_AIBI_DB_NAME")

        # Get credentials from AWS Secrets Manager if not provided
        if not (username and password):
            credentials = self.__get_credentials_from_secrets_manager()
            self.__username = username or credentials.get("username")
            self.__password = password or credentials.get("password")
        else:
            self.__username = username
            self.__password = password

        self.__connection_timeout = connection_timeout
        self.__validate_connection_params()

        # Initialize connection pool
        self.__connection_pool = self.__create_connection_pool()

    def execute(self, query: str) -> SqlResultDTO:
        self.__validate_query(query)

        connection = None
        cursor = None
        start_time = perf_counter()

        try:
            connection = self.__get_pooled_connection()
            cursor = connection.cursor()

            cursor.execute(query)

            # Get column names
            columns = (
                [desc[0] for desc in cursor.description] if cursor.description else []
            )

            # Fetch all results
            rows = cursor.fetchall()

            # Convert tuples to lists for compatibility with SqlResultDTO
            row_lists = [list(row) for row in rows]

            # Calculate execution time
            execution_time_ms = (perf_counter() - start_time) * 1000

            return SqlResultDTO(
                columns=columns,
                rows=row_lists,
                query=query,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise SqlExecutionError(f"Error executing query: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if connection:
                # Return connection to the pool instead of closing
                connection.reset()
                self.__connection_pool.putconn(connection)

    # Private:
    def __create_connection_pool(self):
        """Create a connection pool to the database"""
        try:
            connection_pool = pool.ThreadedConnectionPool(
                minconn=MIN_CONNECTIONS,
                maxconn=MAX_CONNECTIONS,
                host=self.__host,
                port=self.__port,
                dbname=self.__dbname,
                user=self.__username,
                password=self.__password,
                connect_timeout=self.__connection_timeout,
                keepalives=1,
                keepalives_idle=POOL_KEEPALIVE_SECONDS,
                keepalives_interval=60,
                keepalives_count=5,
            )
            logger.info(
                f"Successfully created database connection pool with {MIN_CONNECTIONS}-{MAX_CONNECTIONS} connections"
            )
            return connection_pool
        except Exception as e:
            logger.error(f"Error creating connection pool: {str(e)}")
            raise SqlExecutionError(f"Error creating connection pool: {str(e)}")

    def __get_pooled_connection(self):
        """Get a connection from the pool"""
        try:
            connection = self.__connection_pool.getconn()
            return connection
        except Exception as e:
            logger.error(f"Error getting connection from pool: {str(e)}")
            # Attempt to recreate the pool if it's unavailable
            self.__connection_pool = self.__create_connection_pool()
            raise SqlExecutionError(f"Error getting connection from pool: {str(e)}")

    def __get_connection(self):
        """Get a direct connection to the database (fallback method)"""
        try:
            connection = psycopg2.connect(
                host=self.__host,
                port=self.__port,
                dbname=self.__dbname,
                user=self.__username,
                password=self.__password,
                connect_timeout=self.__connection_timeout,
                keepalives=1,
                keepalives_idle=POOL_KEEPALIVE_SECONDS,
                keepalives_interval=60,
                keepalives_count=5,
            )
            return connection
        except Exception as e:
            logger.error(f"Error connecting to database: {str(e)}")
            raise SqlExecutionError(f"Error connecting to database: {str(e)}")

    def __validate_query(self, query: str) -> None:
        """Validate that the query is safe to execute"""
        # Check for unsafe SQL operations
        for pattern in UNSAFE_OPERATIONS:
            if re.search(pattern, query, re.IGNORECASE):
                raise UnsafeQueryError(
                    f"Query contains unsafe operation matching pattern: {pattern}"
                )

    def __validate_connection_params(self) -> None:
        """Validate that all required connection parameters are present"""
        if not self.__host:
            raise ValueError("Database host is required")
        if not self.__port:
            raise ValueError("Database port is required")
        if not self.__dbname:
            raise ValueError("Database name is required")
        if not self.__username:
            raise ValueError("Database username is required")
        if not self.__password:
            raise ValueError("Database password is required")

    def __get_credentials_from_secrets_manager(self) -> Dict[str, str]:
        """Get database credentials from AWS Secrets Manager"""
        try:
            vars_grabber = VariablesGrabber()
            credentials = vars_grabber.get(
                DEMO_AIBI_CREDENTIALS_SECRET_ARN, skip_full_path=True
            )
            return json.loads(credentials)
        except Exception as e:
            logger.error(f"Error retrieving database credentials: {e}")
            raise SqlExecutionError(f"Error retrieving database credentials: {e}")
