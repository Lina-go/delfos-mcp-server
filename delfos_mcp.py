"""
Delfos MCP Server Configuration
This module sets up the FastMCP server for Delfos SQL database interactions.
"""

import os
import pyodbc
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import logging
import uuid
from datetime import datetime
from typing import List, Dict

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("delfos-sql", stateless_http=True)

# Constants
CONNECTION_STRING = os.getenv("DB_CONNECTION_STRING")

################################
# DATABASE CONNECTION
################################

def get_db_connection() -> pyodbc.Connection:
    """Establish and return a connection to the Azure SQL Database."""
    return pyodbc.connect(CONNECTION_STRING)

################################
# MCP TOOLS
################################

@mcp.tool()
async def execute_sql_query(query: str) -> str:
    """
    Execute a SQL query against the Delfos database and return the results.
    
    Args:
        query (str): The SQL query to execute.
    Returns:
        str: The results of the SQL query.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    result_str = "\n".join([str(row) for row in results])
    return result_str if result_str else "No results found."


@mcp.tool() 
async def get_table_schema(table_name: str) -> str:
    """
    Retrieve the schema of a specified table in the Delfos database.
    
    Args:
        table_name (str): The name of the table to get the schema for.
    Returns:
        str: The schema of the specified table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
    columns = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not columns:
        return f"No schema found for table '{table_name}'."
    
    schema_str = "\n".join([f"{col.COLUMN_NAME}: {col.DATA_TYPE}" for col in columns])
    return schema_str

@mcp.tool()
async def list_tables() -> str:
    """
    List all tables in the Delfos database.
    
    Returns:
        str: A list of all table names in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    
    table_list = [table.TABLE_NAME for table in tables]
    return "\n".join(table_list) if table_list else "No tables found in the database."

@mcp.tool()
async def get_database_info() -> str:
    """
    Retrieve general information about the Delfos database.
    
    Returns:
        str: General information about the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DB_NAME() AS DatabaseName, SERVERPROPERTY('ProductVersion') AS Version")
    info = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return f"Database Name: {info.DatabaseName}\nVersion: {info.Version}"

@mcp.tool()
async def get_table_row_count(table_name: str) -> str:
    """
    Get the number of rows in a specified table.
    
    Args:
        table_name (str): The name of the table to count rows for.
    Returns:
        str: The number of rows in the specified table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) AS TotalRows FROM [SalesLT].[{table_name}]")
    row_count = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return f"Table '{table_name}' has {row_count.TotalRows} rows."

@mcp.tool()
async def get_primary_keys(table_name: str) -> str:
    """
    Retrieve the primary keys of a specified table.
    
    Args:
        table_name (str): The name of the table to get primary keys for.
    Returns:
        str: The primary keys of the specified table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
        WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1 
        AND TABLE_NAME = '{table_name}'
    """)
    keys = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not keys:
        return f"No primary keys found for table '{table_name}'."
    
    key_list = [key.COLUMN_NAME for key in keys]
    return ", ".join(key_list)

@mcp.tool()
async def get_distinct_values(table_name: str, column_name: str) -> str:
    """
    Retrieve distinct values from a specified column in a table.
    
    Args:
        table_name (str): The name of the table.
        column_name (str): The name of the column.
    Returns:
        str: Distinct values from the specified column.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT DISTINCT [{column_name}] FROM [SalesLT].[{table_name}]")
    values = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not values:
        return f"No distinct values found in column '{column_name}' of table '{table_name}'."
    
    value_list = [str(value[0]) for value in values]
    return "\n".join(value_list)

@mcp.tool()
async def get_table_relationships() -> str:
    """
    Retrieve foreign key relationships between tables.
    
    Returns:
        str: List of foreign key relationships in the database.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            fk.name AS ForeignKey,
            tp.name AS ParentTable,
            cp.name AS ParentColumn,
            tr.name AS ReferencedTable,
            cr.name AS ReferencedColumn
        FROM 
            sys.foreign_keys AS fk
        INNER JOIN 
            sys.foreign_key_columns AS fkc ON fk.object_id = fkc.constraint_object_id
        INNER JOIN 
            sys.tables AS tp ON fkc.parent_object_id = tp.object_id
        INNER JOIN 
            sys.columns AS cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
        INNER JOIN 
            sys.tables AS tr ON fkc.referenced_object_id = tr.object_id
        INNER JOIN 
            sys.columns AS cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
    """)
    relationships = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not relationships:
        return "No foreign key relationships found in the database."
    
    rel_list = [
        f"Foreign Key: {rel.ForeignKey}, {rel.ParentTable}({rel.ParentColumn}) -> {rel.ReferencedTable}({rel.ReferencedColumn})"
        for rel in relationships
    ]
    return "\n".join(rel_list)





@mcp.tool()
async def insert_agent_output_batch(
    user_id: str,
    question: str,
    results: List[Dict],
    metric_name: str,
    visual_hint: str
) -> str:
    """
    Insert multiple rows of query results into agent_output table
    
    Args:
        user_id (str): User identifier/email.
        question (str): The natural language question asked by the user.
        results (List[Dict]): List of result rows, each with keys:
            - x_value (str): X-axis value
            - y_value (float): Y-axis numeric value
            - series (str, optional): Series name for grouping
            - category (str, optional): Category name
        metric_name (str): Name of the metric being measured.
        visual_hint (str): Visualization type ('pie', 'bar', 'line', 'table').
    
    Returns:
        str: Confirmation message with run_id and row count.
    
    Example:
        results = [
            {"x_value": "United States", "y_value": 123456.78, "category": "United States"},
            {"x_value": "Canada", "y_value": 45678.90, "category": "Canada"}
        ]
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    run_id = str(uuid.uuid4())
    created_at = datetime.now()
    
    query = """
        INSERT INTO [dbo].[agent_output]
            ([run_id], [user_id], [question], [x_value], [y_value],
             [series], [category], [metric_name], [visual_hint], [created_at])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    rows_inserted = 0
    for row in results:
        cursor.execute(query, (
            run_id,
            user_id,
            question,
            row.get("x_value"),
            row.get("y_value"),
            row.get("series"),
            row.get("category"),
            metric_name,
            visual_hint,
            created_at
        ))
        rows_inserted += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return f"Inserted {rows_inserted} rows successfully. run_id: {run_id}"

@mcp.tool()
async def generate_powerbi_url(run_id: str, visual_hint: str) -> str:
    """
    Generate a Power BI report URL filtered by run_id and visual type.
    Args:
        run_id (str): The run identifier to filter the report.
        visual_hint (str): The type of visualization ('linea', 'barras', 'barras_agrupadas', 'pie').
    Returns:
        str: The generated Power BI report URL.
    """
    WORKSPACE_ID = os.getenv("WORKSPACE_ID")
    REPORT_ID    = os.getenv("REPORT_ID")
 
    VISUAL_PAGE_MAP = {
        "linea": "Line",
        "barras": "Bar",
        "barras_agrupadas": "StackedBar",
        "pie": "PieChart",
    }
 
    page_name = VISUAL_PAGE_MAP.get(visual_hint, "ReportSectionBarras")
 
    url = (
        f"https://app.powerbi.com/groups/{WORKSPACE_ID}/reports/{REPORT_ID}"
        f"?pageName={page_name}"
        f"&filter=agent_output/run_id%20eq%20'{run_id}'"
    )
 
    return url

def main():
    try:
        logging.info("Starting MCP server...")
        mcp.run(transport="streamable-http")
    except Exception as e:
        logging.error(f"Error while running MCP server: {e}")

if __name__ == "__main__":
    main()