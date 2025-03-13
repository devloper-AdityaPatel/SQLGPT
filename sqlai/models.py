from typing import Union
from pydantic import BaseModel

class Database(BaseModel):
    user :str
    password :str
    host :str
    port :int
    database:str
    databasetype : str