import os
import psycopg2
import aiosql
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# This will search up the directory tree for a .env file
load_dotenv(find_dotenv())

# Get database connection details from environment variables
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB_NAME = os.getenv("POSTGRES_DB_NAME", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))


def connect_to_db():
    """
    This function provides a db connection object that can be called when 
    executing queries against the timescale DB.
    """
    
    try:
        # Connect to PostgreSQL database
        db_connection = psycopg2.connect(
            host=POSTGRES_HOST,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            dbname=POSTGRES_DB_NAME,
            port=POSTGRES_PORT
        )
    
        return db_connection
    
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")

def get_queries():
    """
    Loads SQL queries from files using aiosql and returns the queries object.
    """
    sql_path = Path(__file__).parent.parent.parent / "sql"
    queries = aiosql.from_path(sql_path, psycopg2)
    return queries
