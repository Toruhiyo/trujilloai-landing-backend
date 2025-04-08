#!/usr/bin/env python3.13
"""
Utilities for Office Supplies Demo Database Scripts
Contains shared functionality for database connections and error handling.
"""
import json
import os
import sys
import logging
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add the parent directory to sys.path to import custom utilities
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

# Import after adjusting sys.path
from src.config.vars_grabber import VariablesGrabber

DEMO_AIBI_CREDENTIALS_SECRET_ARN = VariablesGrabber().get("DEMO_AIBI_DB_SECRET_ARN")


def get_db_credentials():
    """Get database credentials from VariablesGrabber"""
    try:
        vars_grabber = VariablesGrabber()
        credentials = vars_grabber.get(
            DEMO_AIBI_CREDENTIALS_SECRET_ARN, skip_full_path=True
        )
        creds_dict = json.loads(credentials)

        # Get host, port, and dbname
        host = vars_grabber.get("DEMO_AIBI_DB_HOST")
        port = vars_grabber.get("DEMO_AIBI_DB_PORT")
        dbname = vars_grabber.get("DEMO_AIBI_DB_NAME")
        if port is None:
            port = "5432"

        # Add host, port, and dbname to credentials
        creds_dict["host"] = host
        creds_dict["port"] = int(port)
        creds_dict["dbname"] = dbname
        return creds_dict
    except Exception as e:
        logger.error(f"Error retrieving database credentials: {e}")
        raise e


def connect_to_db(credentials):
    """Connect to the PostgreSQL database"""
    if credentials is None:
        raise ValueError("Credentials are None")
    if credentials.get("host") is None:
        raise ValueError("Host is None")
    if credentials.get("port") is None:
        raise ValueError("Port is None")
    if credentials.get("dbname") is None:
        raise ValueError("DB Name is None")
    if credentials.get("username") is None:
        raise ValueError("Username is None")
    if credentials.get("password") is None:
        raise ValueError("Password is None")

    try:
        conn = psycopg2.connect(
            host=credentials.get("host", ""),
            port=credentials.get("port", 5432),
            dbname=credentials.get("dbname", "postgres"),
            user=credentials.get("username", ""),
            password=credentials.get("password", ""),
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise e


def load_data(filepath):
    """Load data from JSON files"""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading data from {filepath}: {e}")
        raise e


def insert_data(conn, table_name, data, columns):
    """Insert data into a table"""
    if not data:
        logger.info(f"No data to insert into {table_name}")
        return []

    cursor = conn.cursor()
    try:
        values = [tuple(item[col] for col in columns) for item in data]
        insert_query = f"""
        INSERT INTO {table_name} ({', '.join(columns)})
        VALUES %s
        RETURNING {compute_id_column(table_name)}
        """

        ids = execute_values(cursor, insert_query, values, fetch=True)
        conn.commit()
        logger.info(f"Successfully inserted {len(values)} records into {table_name}")
        return [id[0] for id in ids]
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting data into {table_name}: {e}")
        raise e
    finally:
        cursor.close()


def compute_id_column(table_name):
    """Compute the ID column for a table"""
    # Special cases for tables where the ID column is simply 'id'
    if table_name in ["colors", "materials"]:
        return "id"

    # Standard case: tablename_id
    stem = table_name.rstrip("s")
    if stem.endswith("ie"):
        stem = stem.rstrip("ie") + "y"
    return f"{stem}_id"
