from typing_extensions import TypedDict
from globalvariables import CHATMODEL,MODELPROVIDER,DATABASEURL
from typing_extensions import Annotated
from langchain_core.prompts import PromptTemplate


class State(TypedDict):
    question: str
    query: str
    result: str
    answer: str




class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]


def SqlAgent(llm,db):

    from langchain import hub

    query_prompt_template = hub.pull("langchain-ai/sql-query-system-prompt")
    def write_query(state: State):
        """Generate SQL query to fetch information."""
        prompt = query_prompt_template.invoke(
            {
                "dialect": db.dialect,
                "top_k": 10,
                "table_info": db.get_table_info(),
                "input": state["question"],
            }
        )
        structured_llm = llm.with_structured_output(QueryOutput)
        result = structured_llm.invoke(prompt)
        # print("write_query result :  ", result)
        return {"query": result["query"]}

    from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool


    def execute_query(state: State):
        """Execute SQL query."""
        execute_query_tool = QuerySQLDatabaseTool(db=db)
        # print("Executing query:", state["query"])
        return {"result": execute_query_tool.invoke(state["query"])}

    def generate_answer(state: State):
        """Answer question using retrieved information as context."""
        prompt = (
            "Given the following user question, corresponding SQL query, "
            "and SQL result, answer the user question.\n\n"
            f'Question: {state["question"]}\n'
            f'SQL Query: {state["query"]}\n'
            f'SQL Result: {state["result"]}'
        )
        response = llm.invoke(prompt)
        return {"answer": response.content}

    from langgraph.graph import START, StateGraph

    graph_builder = StateGraph(State).add_sequence(
        [write_query, execute_query, generate_answer]
    )
    graph_builder.add_edge(START, "write_query")
    
    return graph_builder.compile()


def responsegenerator(llm,promptVariables,userquestion):

    rawprompt = """
generate answer in markdown format

Given the following user question, SQL query, and its resulting dataset 

userquestion : {question}
sql query : {query}

dataset : {dataset}

don't write anything else other than mention below

write the sql query in the block quote seperate in  line
sql query should be in blockquote markdown.

generate the table of dataset in seperate line.
heading and data of tables should align in center.

Write the answer according to the userquestion and dateset in seperate line

don't write anything else other than mention above


"""
    
    prompt = PromptTemplate(
        input_variables=["question", "query", "dataset"],  # Define placeholders
        template=rawprompt
    )

    prompt_text = prompt.format(
        question=userquestion,
        query=promptVariables[0]['write_query']['query'],
        dataset=promptVariables[1]['execute_query']['result']
    )
    try:
        response = llm.invoke(prompt_text)
    except Exception as e:
        return str(e)
        
    return response

if __name__ == "__main__":
    from langchain_community.utilities import SQLDatabase
    from langchain.chat_models import init_chat_model
    from langgraph.graph import START, StateGraph
    from fastapi import FastAPI
    from dotenv import load_dotenv
    load_dotenv()
    llm = init_chat_model(CHATMODEL, model_provider=MODELPROVIDER)
    databaseUrl = DATABASEURL
    db = SQLDatabase.from_uri(databaseUrl)
    graph = SqlAgent(llm=llm,db=db)
    for step in graph.stream(
        {"question": "what is total number of films."}, stream_mode="updates"
    ):
        print(step)