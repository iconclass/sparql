from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from rdflib import Graph
from fastapi.responses import JSONResponse
from io import StringIO
import json
from fastapi import FastAPI
from .store import IconclassStore

app = FastAPI()
G = Graph(store="IconclassStore")


@app.get(
    "/sparqlfts",
)
def sparqlfts(query: str):
    result = G.query(query)

    ser = JSONResultSerializer(result)
    buf = StringIO()
    ser.serialize(buf)

    return JSONResponse(json.loads(buf.getvalue()))
