from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from rdflib import ConjunctiveGraph, Graph
from fastapi.responses import JSONResponse
from io import StringIO
import json
from fastapi import FastAPI, Form, Query, Request, Response
from .store import IconclassStore
import random, time
from typing import Optional

app = FastAPI()
G = ConjunctiveGraph(store="IconclassStore")
QUERY_STATS = {"total": 0}

SERVICE_DESCRIPTION = """@prefix sd: <http://www.w3.org/ns/sparql-service-description#> .
        @prefix ent: <http://www.w3.org/ns/entailment/> .
        @prefix prof: <http://www.w3.org/ns/owl-profile/> .
        @prefix void: <http://rdfs.org/ns/void#> .
        @prefix dc: <http://purl.org/dc/elements/1.1/> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        <http://test.iconclass.org/sparql> a sd:Service ;
            rdfs:label "ICONCLASS SPARQL" ;
            dc:description "A sparql query service with fulltextsearch over the ICONCLASS subject classification system" ;
            sd:endpoint <http://test.iconclass.org/sparql> ;
            sd:supportedLanguage sd:SPARQL11Query ;
            sd:resultFormat <http://www.w3.org/ns/formats/SPARQL_Results_JSON>, <http://www.w3.org/ns/formats/SPARQL_Results_CSV> ;
            sd:feature sd:DereferencesURIs ;
            sd:defaultEntailmentRegime ent:RDFS ;
            sd:defaultDataset [
                a sd:Dataset ;
                sd:defaultGraph [
                    a sd:Graph ;
                ] 
            ] ."""


@app.get("/sparql")
def sparql_get(request: Request, query: Optional[str] = Query(None)):
    nonce = "".join([random.choice("0123456789abcdef") for x in range(20)])
    QUERY_STATS[nonce] = {"start": time.time()}

    if not query:
        tmp_graph = Graph()
        tmp_graph.parse(data=SERVICE_DESCRIPTION, format="ttl")
        if request.headers["accept"] == "text/turtle":
            return Response(
                tmp_graph.serialize(format="turtle"), media_type="text/turtle"
            )
        else:
            return Response(
                tmp_graph.serialize(format="xml"), media_type="application/xml"
            )

    result = G.query(query)

    total = QUERY_STATS["total"]
    del QUERY_STATS[nonce]
    QUERY_STATS["total"] = total + 1

    if result.type == "CONSTRUCT":
        buf = result.graph.serialize(format="json-ld")
        r = JSONResponse(json.loads(buf))
        r.headers["content-type"] = "application/ld+json"
    else:
        ser = JSONResultSerializer(result)
        buf = StringIO()
        ser.serialize(buf)
        r = JSONResponse(json.loads(buf.getvalue()))
        r.headers["content-type"] = "application/sparql-results+json"

    return r


@app.post("/sparql")
def sparql_post(request: Request, query: str = Form(...)):
    return sparql_get(request, query)


@app.get("/")
def homepage():
    return {"status": "OK", "stats": QUERY_STATS}
