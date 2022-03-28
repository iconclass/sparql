from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from rdflib import Graph
from fastapi.responses import JSONResponse
from io import StringIO
import json
from fastapi import FastAPI, Form
from .store import IconclassStore

app = FastAPI()
G = Graph(store="IconclassStore")


@app.get("/sparql")
def sparql_get(query: str):
    result = G.query(query)

    ser = JSONResultSerializer(result)
    buf = StringIO()
    ser.serialize(buf)

    return JSONResponse(json.loads(buf.getvalue()))


@app.post("/sparql")
def sparql_post(query: str = Form(...)):
    return sparql_get(query)
