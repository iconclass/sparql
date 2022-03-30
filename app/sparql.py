from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from rdflib import ConjunctiveGraph
from fastapi.responses import JSONResponse
from io import StringIO
import json
from fastapi import FastAPI, Form
from .store import IconclassStore
import random, time

app = FastAPI()
G = ConjunctiveGraph(store="IconclassStore")
QUERY_STATS = {"total": 0}


@app.get("/sparql")
def sparql_get(query: str):
    nonce = "".join([random.choice("0123456789abcdef") for x in range(20)])
    QUERY_STATS[nonce] = {"start": time.time()}
    result = G.query(query)

    ser = JSONResultSerializer(result)
    buf = StringIO()
    ser.serialize(buf)

    total = QUERY_STATS["total"]
    del QUERY_STATS[nonce]
    QUERY_STATS["total"] = total + 1

    r = JSONResponse(json.loads(buf.getvalue()))
    r.headers["content-type"] = "application/sparql-results+json"

    return r


@app.post("/sparql")
def sparql_post(query: str = Form(...)):
    return sparql_get(query)


@app.get("/")
def homepage():
    return {"status": "OK", "stats": QUERY_STATS}
