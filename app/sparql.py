from rdflib.plugins.sparql.results.jsonresults import JSONResultSerializer
from rdflib import ConjunctiveGraph, Graph, URIRef, Namespace, Literal
from fastapi.responses import JSONResponse
from io import StringIO
import json, httpx
from fastapi import FastAPI, Form, Query, Request, Response, BackgroundTasks
from .store import IconclassStore
import random, time
from typing import Optional
import logging

app = FastAPI()
G = ConjunctiveGraph(store="IconclassStore")
QUERY_STATS = {}
IC = Namespace("http://iconclass.org/")

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
async def sparql_get(
    request: Request,
    background_tasks: BackgroundTasks,
    query: Optional[str] = Query(None),
):
    background_tasks.add_task(rec_usage, request)

    accept_header = request.headers.get("accept", "")

    if not query:
        tmp_graph = Graph()
        tmp_graph.bind("ic", IC)
        tmp_graph.parse(data=SERVICE_DESCRIPTION, format="ttl")
        for k, v in QUERY_STATS.items():
            tmp_graph.add(
                (IC[k], IC["querystart"], Literal(time.ctime(v.get("start", ""))))
            )
            tmp_graph.add(
                (IC[k], IC["queryend"], Literal(time.ctime(v.get("end", ""))))
            )
            tmp_graph.add((IC[k], IC["queryduration"], Literal(v.get("duration", ""))))
        if accept_header == "application/xml":
            return Response(
                tmp_graph.serialize(format="xml"), media_type="application/xml"
            )
        else:
            return Response(
                tmp_graph.serialize(format="turtle"), media_type="text/turtle"
            )

    nonce = "".join([random.choice("0123456789abcdef") for x in range(20)])
    start_time = time.time()
    QUERY_STATS[nonce] = {"start": time.time()}

    result = G.query(query)
    end_time = time.time()

    QUERY_STATS[nonce]["end"] = end_time
    QUERY_STATS[nonce]["duration"] = end_time - start_time

    if result.type == "CONSTRUCT":
        if accept_header == "application/ld+json":
            buf = result.graph.serialize(format="json-ld")
            r = JSONResponse(json.loads(buf))
            r.headers["content-type"] = "application/ld+json"
        elif accept_header == "application/xml":
            buf = result.graph.serialize(format="xml")
            r = Response(buf)
            r.headers["content-type"] = "application/xml"
        else:
            buf = result.graph.serialize(format="ttl")
            r = Response(buf)
            r.headers["content-type"] = "text/turtle"
    else:
        ser = JSONResultSerializer(result)
        buf = StringIO()
        ser.serialize(buf)
        r = JSONResponse(json.loads(buf.getvalue()))
        r.headers["content-type"] = "application/sparql-results+json"

    return r


@app.post("/sparql")
async def sparql_post(
    request: Request, background_tasks: BackgroundTasks, query: str = Form(...)
):
    return await sparql_get(request, background_tasks, query)


@app.get("/")
def homepage():
    return {"status": "OK", "stats": QUERY_STATS}


def rec_usage(request: Request):
    xff = request.headers.get("x-forwarded-for")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": request.headers.get("user-agent", "unknown"),
        "X-Forwarded-For": "127.0.0.1",
    }
    if xff:
        logging.debug(f"Query from {xff}")
        headers["X-Forwarded-For"] = xff
    r = httpx.post(
        "https://plausible.io/api/event",
        headers=headers,
        data=json.dumps(
            {
                "name": "pageview",
                "url": "https://test.iconclass.org/sparql",
                "domain": "test.iconclass.org",
            }
        ),
    )
