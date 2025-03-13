from sqlalchemy import create_engine,text
from agent import State
# DEFINE THE DATABASE CREDENTIALS
# user = ''
# password = ''
# host = ''
# port = 
# database = ''


dbtypes = ['mysql+pymysql','postgresql','sqlite']


#Dependencies:
"""
postgres : psycopg2
sqlite : sqlite
mysql : pymysql
"""
# CREATE THE DATABASE CONNECTION
# URL = “dialect+driver://username:password@host:port/

# Common Database URLs
# Replace <username>, <password>, <host>, <port>, and <dbname> accordingly.

# Database	Connection URL
# SQLite	sqlite:///example.db
# PostgreSQL	postgresql://username:password@localhost/dbname
# MySQL	mysql+pymysql://username:password@localhost/dbname
# SQL Server	mssql+pyodbc://username:password@server/dbname?driver=ODBC+Driver+17+for+SQL+Server

def getDatabaseUrl(user:str,password:str,host:str,port:int,database:str,dbtype:str):
    return f"{dbtype}://{user}:{password}@{host}:{port}/{database}"

def create_connection(user:str,password:str,host:str,port:int,database:str,dbtype:str):
    engine = create_engine(f"{dbtype}://{user}:{password}@{host}:{port}/{database}")
    
    return engine.connect()

# execute query
def execute_query(query:str,dbconnection):
    """Execute SQL query."""
    try:

        result = dbconnection.execute(text(query))

    except Exception as e:
        return {"error": str(e)}

    return result # return the object which can be used to fetch keys and rows

def make_json_from_result(resultkeys, resultrows):
    return [dict(zip(resultkeys, row)) for row in resultrows]



if __name__ == '__main__':
    # CREATE A CONNECTION TO THE DATABASE
    user = 'postgres'
    password = 'postgres'
    host = 'localhost'
    port = 5432
    database = 'dvdrental'
    try:
        connection = create_connection(user,password,host,port,database,dbtypes[1])
        print("Connection to the database was successful")
        # state = State()
        # state["query"] = text("select * from actor")
        execute_query(text("select * from actor"),connection)

    except Exception as e:
        print("error : ",e)
