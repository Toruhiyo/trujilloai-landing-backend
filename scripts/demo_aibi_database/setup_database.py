#!/usr/bin/env python3.13
"""
Setup Database Script for Office Supplies Demo
This script deletes existing tables if they exist, recreates them, and populates them with data.
"""
import sys
import time
import glob
import logging
from pathlib import Path


# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def import_utils():
    """Import utils module dynamically after adjusting path"""
    # Add current directory to path for local imports
    sys.path.append(str(Path(__file__).parent))

    # Import modules
    global get_db_credentials, connect_to_db, load_data, insert_data
    from utils import get_db_credentials, connect_to_db, load_data, insert_data


# Import utility functions
import_utils()


def drop_tables(conn):
    """Drop tables if they exist, in the correct order to avoid constraint violations"""
    cursor = conn.cursor()

    # Tables need to be dropped in reverse order of their dependencies
    drop_tables_sql = [
        "DROP TABLE IF EXISTS sale_items CASCADE;",
        "DROP TABLE IF EXISTS sales CASCADE;",
        "DROP TABLE IF EXISTS products CASCADE;",
        "DROP TABLE IF EXISTS categories CASCADE;",
        "DROP TABLE IF EXISTS customers CASCADE;",
    ]

    # Also explicitly drop sequences
    drop_sequences_sql = [
        "DROP SEQUENCE IF EXISTS customers_customer_id_seq CASCADE;",
        "DROP SEQUENCE IF EXISTS categories_category_id_seq CASCADE;",
        "DROP SEQUENCE IF EXISTS products_product_id_seq CASCADE;",
        "DROP SEQUENCE IF EXISTS sales_sale_id_seq CASCADE;",
        "DROP SEQUENCE IF EXISTS sale_items_sale_item_id_seq CASCADE;",
    ]

    try:
        # Drop tables
        for sql in drop_tables_sql:
            cursor.execute(sql)

        # Drop sequences
        for sql in drop_sequences_sql:
            cursor.execute(sql)

        conn.commit()
        logger.info("Successfully dropped existing tables and sequences")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error dropping tables and sequences: {e}")
        sys.exit(1)
    finally:
        cursor.close()


def create_tables(conn):
    """Create tables in the database"""
    cursor = conn.cursor()

    # SQL for creating tables
    create_tables_sql = [
        """
        CREATE TABLE customers (
            customer_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            sector VARCHAR(100),
            region VARCHAR(100),
            signup_date DATE
        )
        """,
        """
        CREATE TABLE categories (
            category_id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
        """,
        """
        CREATE TABLE products (
            product_id SERIAL PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            description TEXT,
            category_id INTEGER REFERENCES categories(category_id),
            brand VARCHAR(50),
            color VARCHAR(50),
            format VARCHAR(50),
            size VARCHAR(50),
            material VARCHAR(50),
            price DECIMAL(10, 2) NOT NULL
        )
        """,
        """
        CREATE TABLE sales (
            sale_id SERIAL PRIMARY KEY,
            customer_id INTEGER REFERENCES customers(customer_id),
            sale_date DATE NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL
        )
        """,
        """
        CREATE TABLE sale_items (
            sale_item_id SERIAL PRIMARY KEY,
            sale_id INTEGER REFERENCES sales(sale_id),
            product_id INTEGER REFERENCES products(product_id),
            quantity INTEGER NOT NULL,
            unit_price DECIMAL(10, 2) NOT NULL
        )
        """,
    ]

    try:
        for sql in create_tables_sql:
            cursor.execute(sql)

        # Force reset all sequences to ensure autoincremental IDs start from 1
        reset_sequences_sql = [
            "SELECT setval('customers_customer_id_seq', 1, false);",
            "SELECT setval('categories_category_id_seq', 1, false);",
            "SELECT setval('products_product_id_seq', 1, false);",
            "SELECT setval('sales_sale_id_seq', 1, false);",
            "SELECT setval('sale_items_sale_item_id_seq', 1, false);",
        ]

        for sql in reset_sequences_sql:
            cursor.execute(sql)

        # Verify sequences were reset by checking current values in pg_sequences
        cursor.execute(
            "SELECT sequencename, last_value FROM pg_sequences WHERE schemaname='public';"
        )
        sequence_values = cursor.fetchall()
        for seq_name, last_value in sequence_values:
            logger.info(f"Sequence {seq_name} reset to value: {last_value}")

        conn.commit()
        logger.info("Successfully created new tables and forcefully reset sequences")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating tables or resetting sequences: {e}")
        sys.exit(1)
    finally:
        cursor.close()


def load_all_data_by_type(data_dir, file_pattern):
    """Load and combine data from all files matching a pattern"""
    all_data = []
    for filepath in glob.glob(str(data_dir / file_pattern)):
        logger.info(f"Loading data from {filepath}")
        data = load_data(filepath)
        if isinstance(data, list):
            all_data.extend(data)
        else:
            all_data.append(data)
    return all_data


def populate_tables(conn):
    """Load data from files and insert into tables"""
    try:
        # Get the path to the data directory
        current_dir = Path(__file__).parent
        data_dir = current_dir / "data"

        # Load and insert categories
        categories = load_all_data_by_type(data_dir, "categories*.json")
        category_columns = ["name"]
        insert_data(conn, "categories", categories, category_columns)

        # Load and insert customers
        customers = load_all_data_by_type(data_dir, "customers*.json")
        customer_columns = ["name", "sector", "region", "signup_date"]
        insert_data(conn, "customers", customers, customer_columns)

        # Load and insert products
        products = load_all_data_by_type(data_dir, "products*.json")
        product_columns = [
            "name",
            "description",
            "category_id",
            "brand",
            "color",
            "format",
            "size",
            "material",
            "price",
        ]
        insert_data(conn, "products", products, product_columns)

        # Load and insert sales
        sales = load_all_data_by_type(data_dir, "sales*.json")
        sale_columns = ["customer_id", "sale_date", "total_amount"]
        insert_data(conn, "sales", sales, sale_columns)

        # Load and insert sale_items
        sale_items = load_all_data_by_type(data_dir, "sale_items*.json")
        sale_item_columns = ["sale_id", "product_id", "quantity", "unit_price"]
        insert_data(conn, "sale_items", sale_items, sale_item_columns)

        logger.info("Successfully populated all tables")
    except Exception as e:
        logger.error(f"Error populating tables: {e}")
        raise e


def main():
    """Main function to setup the database"""
    start_time = time.time()

    try:
        # Get credentials and connect to database
        credentials = get_db_credentials()
        conn = connect_to_db(credentials)

        # Drop existing tables
        drop_tables(conn)

        # Create tables
        create_tables(conn)

        # Populate tables
        populate_tables(conn)

        # Close database connection
        conn.close()

        end_time = time.time()
        logger.info(f"Database setup completed in {end_time - start_time:.2f} seconds")
    except Exception as e:
        logger.error(f"Error in main process: {e}")
        raise e


if __name__ == "__main__":
    main()
