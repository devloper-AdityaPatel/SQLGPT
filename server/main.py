from fastapi import FastAPI
from typing import Union
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from sqlalchemy import create_engine,text
from sqlalchemy.exc import ArgumentError

# importing production utilities
from models import Database
from database import getDatabaseUrl,dbtypes
from globalvariables import CHATMODEL,MODELPROVIDER
from agent import SqlAgent,responsegenerator
from database import execute_query,make_json_from_result

# importing langchain utilities
from langchain_community.utilities import SQLDatabase
from langchain.chat_models import init_chat_model
from langgraph.graph import START, StateGraph

# Initializing Global variables
load_dotenv()

import orjson
from decimal import Decimal
from datetime import datetime, date
from uuid import UUID

def custom_serializer(obj):
    """Custom serializer for non-serializable types"""
    if isinstance(obj, Decimal):
        return float(obj)  # Convert Decimal to float
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()  # Convert datetime to string
    elif isinstance(obj, UUID):
        return str(obj)  # Convert UUID to string
    elif isinstance(obj, set):
        return list(obj)  # Convert set to list
    elif isinstance(obj, bytes):
        return obj.decode("utf-8")  # Convert bytes to string
    else:
        return str(obj)  # Convert unknown types to string
    raise TypeError(f"Type {type(obj)} is not serializable")
# Load the model
llm = init_chat_model(CHATMODEL, model_provider=MODELPROVIDER)
databaseUrl = str()


# API workflow
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Replace "" with the specific origin(s) of your frontend for better security
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)

# agents end here


@app.get("/database/databasetypes")
def read_root():
    return {
        "statuscode": 200,
        "status": "success",
        "message": "Request processed successfully.",
        "data": {
            "databasetypes": dbtypes
        }
    }


@app.get("/query/{question}")
def read_item(question: str):
    result = list()
    try:
        db = SQLDatabase.from_uri(databaseUrl)
        graph = SqlAgent(llm=llm,db=db)


        for step in graph.stream(
            {"question": question}, stream_mode="updates"
        ):
            
            result.append(step)

        connection = create_engine(databaseUrl).connect()
        query = text(result[0]['write_query']['query'])


        try : 
            dbresult = execute_query(result[0]['write_query']['query'],connection)
        except ArgumentError as e:
            return ORJSONResponse(content={"error": str(e)}, status_code=400)
        except Exception as e:
            return ORJSONResponse(content={"error" : e }, status_code=400)
        if(dbresult == None or type(dbresult)== type(dict()) ):
            return ORJSONResponse(content={"error" : "No data found" }, status_code=400)
        dbkeys = [col for col in dbresult.keys()]
        dbresultrows = [tuple(item) for item in dbresult.fetchall()]
        table = {"columns": [col for col in dbkeys], "rows":[item for item in dbresultrows] }
        answer = responsegenerator(llm,result[0]['write_query']['query'],question,dbresultrows)
        
    except Exception as e:

        return ORJSONResponse(content={"error" : e }, status_code=400)
    response = {

        "statuscode": 200,
        "status": "success",
        "query": result[0]['write_query']['query'],
        "table": table,
        "answer": answer['answer']
    }
    # return ORJSONResponse(content=orjson.dumps(response, default=custom_serializer), status_code=200)
    return response
@app.post("/database/createconnection")
def create_database(database: Database):
    try:
        global databaseUrl
        databaseUrl = getDatabaseUrl(
            user=database.user,
            password=database.password,
            host=database.host,
            port=database.port,
            database=database.database,
            dbtype=database.databasetype)
        global db 
        db = SQLDatabase.from_uri(databaseUrl)
        global graph
        graph = SqlAgent(llm=llm,db=db)
    except Exception as e:
        return {
            "statuscode": 400,
            "status": "error",
            "message": "Something went wrong while intitializing the connection",
            "errors": [
                {
                "field": "graph",
                "message": str(e)
                }
            ]
        }

    return {
        "statuscode": 200,
        "status": "success",
        "message": "Request processed successfully.",
        "data": {
            "databaseurl": databaseUrl
        }
    }







"""
    1. Success Response (200 OK, 201 Created, etc.)
    {   
        "statuscode": "200"
        "status": "success",
        "message": "Request processed successfully.",
        "data": {
        }
    }

    2. Error Response (400 Bad Request, 404 Not Found, 500 Internal Server Error, etc.)

    {
        "statuscode": "400"
        "status": "error",
        "message": "Invalid request parameters.",
        "errors": [
            {
            "field": "name",
            "message": "Name is required."
            }
        ]
    }

"""