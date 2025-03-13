from typing_extensions import TypedDict
from globalvariables import CHATMODEL,MODELPROVIDER,DATABASEURL
from typing_extensions import Annotated
from langchain_core.prompts import PromptTemplate
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool




class State(TypedDict):
    question: str
    query: str
    # result: str
    # answer: str




class QueryOutput(TypedDict):
    """Generated SQL query."""

    query: Annotated[str, ..., "Syntactically valid SQL query."]
class AnswerOutput(TypedDict):
    """Generated Answer"""
    answer: Annotated[str, ..., "well formed answer in markdown format"]


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



    # def execute_query(state: State):
    #     """Execute SQL query."""
    #     execute_query_tool = QuerySQLDatabaseTool(db=db)
    #     # print("Executing query:", state["query"])
    #     return {"result": execute_query_tool.invoke(state["query"])}

    # def generate_answer(state: State):
    #     """Answer question using retrieved information as context."""
    #     prompt = (
    #         "Given the following user question, corresponding SQL query, "
    #         "and SQL result, answer the user question.\n\n"
    #         f'Question: {state["question"]}\n'
    #         f'SQL Query: {state["query"]}\n'
    #         f'SQL Result: {state["result"]}'
    #     )
    #     response = llm.invoke(prompt)
    #     return {"answer": response.content}

    from langgraph.graph import START, StateGraph,END

    graph_builder = StateGraph(State)
    """ .add_sequence(
        # write_query
        # [write_query , execute_query, generate_answer]
    ) """
    graph_builder.add_node("write_query", write_query)
    graph_builder.add_edge(START, "write_query")
    graph_builder.add_edge("write_query", END)
    
    return graph_builder.compile()

# response generator
def responsegenerator(llm,query,userquestion,databaseResult):

    rawprompt = """
Given the following user question, SQL query, and its resulting dataset 

userquestion : {question}
sql query : {query}
dataset : {dataset}

analyse the question and generate answer according to the user question,sql query and dataset

"""
    
    prompt = PromptTemplate(
        input_variables=["question", "query", "dataset"],  # Define placeholders
        template=rawprompt
    )

    prompt_text = prompt.format(
        question=userquestion,
        query=query,
        dataset= databaseResult
    )
    try:
        structured_llm = llm.with_structured_output(AnswerOutput)
        response = structured_llm.invoke(prompt_text)
    except Exception as e:
        return str(e)
        
    return response



if __name__ == "__main__":
    from langchain_community.utilities import SQLDatabase
    from langchain.chat_models import init_chat_model
    from database import execute_query,make_json_from_result
    from dotenv import load_dotenv
    load_dotenv()
    llm = init_chat_model(CHATMODEL, model_provider=MODELPROVIDER)
    databaseUrl = DATABASEURL
    db = SQLDatabase.from_uri(databaseUrl)
    graph = SqlAgent(llm=llm,db=db)
    query = list()
    for step in graph.stream(
        {"question": "give post with id 3"}, stream_mode="updates"
    ):
        query.append(step)
    # print("query : ",query)


    from sqlalchemy import create_engine,text
    engine = create_engine(databaseUrl)
    dbconnection = engine.connect()
    print("query : ",text(query[0]['write_query']['query']))
    dbresult = execute_query(query[0]['write_query']['query'],dbconnection)
    print("dbresult : ",dbresult)
    dbkeys = [col for col in dbresult.keys()]
    dbresultrows = [tuple(item) for item in dbresult.fetchall()]
    # print("answer : ",responsegenerator(llm=llm,query=query[0]['write_query']['query'],userquestion="give post with id 3",databaseResult=dbresultrows))
    dbconnection.close()