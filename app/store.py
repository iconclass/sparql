from rdflib.plugins.sparql.evaluate import evalBGP, evalPart, _fillTemplate
from rdflib.plugins.sparql import CUSTOM_EVALS
from rdflib.plugins.sparql.sparql import AlreadyBound
from rdflib.store import Store
from rdflib import URIRef, Graph, Namespace, Literal
from rdflib.term import Variable
from rdflib.namespace import DC, SKOS, RDF
from rdflib.plugin import register
from urllib.parse import quote, unquote
import os, sqlite3, textbase, re, sys
import logging

IC = Namespace("http://iconclass.org/")
PREDICATE_FTS = IC.search
PREDICATE_FTS_NOKEYS = IC.searchnokeys
DATA_PATH = os.environ.get("IC_DATA_PATH", "../data/")

MAX_EMPTY_SUBJECTS_ITERATION = 99
FTS_QUERY_LIMIT = 99

TRIPLE_CACHE = set()


def get_cursor():
    db = sqlite3.connect(os.path.join(DATA_PATH, "iconclass_index.sqlite"))
    db.enable_load_extension(True)
    if sys.platform == "linux2":
        db.load_extension("/usr/local/lib/fts5stemmer")
    elif sys.platform == "darwin":
        db.load_extension("/usr/local/lib/fts5stemmer.dylib")
    db.create_function("regexp", 2, regexp)
    return db.cursor()


def regexp(pattern, value):
    matcher = re.compile(pattern)
    if matcher.match(value):
        return True
    else:
        return False


def read_n(DATA_PATH):
    d = {}

    KEYS = {}
    for x in textbase.parse(os.path.join(DATA_PATH, "keys.txt")):
        k = x.get("K")
        if k:
            KEYS[k[0]] = x

    for x in textbase.parse(os.path.join(DATA_PATH, "notations.txt")):
        n = x.get("N")
        if n:
            d[n[0]] = x
        k = x.get("K")
        if k:
            kk = KEYS.get(k[0])
            if kk:
                x["K"] = kk
            else:
                del x["K"]

    # set the broader based on the C of the parents
    # and set the reverse related as "RR"
    for n, obj in d.items():
        for c in obj.get("C", []):
            c_obj = d.get(c)
            if c_obj:
                c_obj["B"] = n
        for r in obj.get("R", []):
            r_obj = d.get(r)
            if r_obj:
                r_obj.setdefault("RR", []).append(n)

    return d


def do_search(q: str, lang: str, sort: str, keys: bool, r: str):
    if lang not in ("en", "de", "fr", "it"):
        raise Exception(
            detail=f"Language [{lang}] can not be searched in at the moment",
        )
    if keys:
        keys = ""
    else:
        keys = "is_key=0 AND "
    if q:
        SQL = f"SELECT notation FROM {lang} WHERE {keys}text MATCH ? order by {sort} LIMIT {FTS_QUERY_LIMIT}"
    else:
        SQL = f"SELECT notation FROM notations WHERE notation REGEXP ? LIMIT {FTS_QUERY_LIMIT}"
        q = r
    try:
        if len(r) > 0:
            rr = re.compile(r)
            results = [x[0] for x in get_cursor().execute(SQL, (q,)) if rr.match(x[0])]
        else:
            results = [x[0] for x in get_cursor().execute(SQL, (q,))]
    except sqlite3.OperationalError:
        results = []
    return results


def getq(ctx, vars):
    for var, qtipe, val in vars:
        if not isinstance(var, Variable):
            logging.error(f"{var} is not a Variable")
            continue
        if not qtipe in (PREDICATE_FTS, PREDICATE_FTS_NOKEYS):
            logging.error(f"{qtipe} is not a IC search predicate")
            continue
        if not isinstance(val, Literal):
            logging.error(f"{val} is not a Literal")
            continue

        lang = val.language or "en"
        lang = lang[:2]
        sort = "rank"
        val = str(val)

        search_results = do_search(
            q=val, r="", lang=lang, sort=sort, keys=(qtipe == PREDICATE_FTS)
        )
        logging.debug(f"Query {val} with {qtipe} gave {len(search_results)}")

        for notation in search_results:
            c = ctx.push()
            try:
                c[var] = IC[quote(notation)]
            except AlreadyBound:
                continue

            yield c.solution()


def fts_eval(ctx, part):
    if part.name == "ConstructQuery":
        return evalConstructQuery(ctx, part)
    if part.name != "BGP":
        raise NotImplementedError()
    vars = []
    for t in part.triples:
        if not isinstance(t[0], Variable):
            continue
        if t[1] in (PREDICATE_FTS, PREDICATE_FTS_NOKEYS):
            if isinstance(t[2], Literal):
                vars.append(t)
            else:
                logging.error(f"Trying to do {t[1]} with non-Literal")
    if len(vars) > 0:
        return getq(ctx, vars)
    return evalBGP(ctx, part.triples)


# This is copied verbatim from https://github.com/RDFLib/rdflib/blob/master/rdflib/plugins/sparql/evaluate.py#L537
# To fix what seems like a bug, in the original for an empty template is done:
# query.p.p.triples <- so this is possibly a temporary fix
def evalConstructQuery(ctx, query):
    template = query.template

    if not template:
        # a construct-where query
        template = query.p.p.p.triples  # query->project->bgp ...

    graph = Graph()

    for c in evalPart(ctx, query.p):
        graph += _fillTemplate(template, c)

    res = {}
    res["type_"] = "CONSTRUCT"
    res["graph"] = graph

    return res


CUSTOM_EVALS["fts_eval"] = fts_eval


class IconclassStore(Store):
    context_aware = True

    def __init__(self, configuration=None, identifier=None):
        self.triple_call_count = 0
        self.NOTATIONS = read_n(DATA_PATH)
        self.sorted_notations = sorted(self.NOTATIONS, key=lambda x: len(x))
        super().__init__(configuration, identifier)

    def n_from_uri(self, u):
        if u is None:
            return
        tmp = u.split(IC)
        if len(tmp) != 2:
            return
        n = tmp[-1]
        if not n[0] in "0123456789":
            return
        # TODO, need to handle keys and with names in here
        return self.NOTATIONS.get(unquote(n))

    def triple_notation(self, uriref, p, o):
        if uriref is None and p is None and isinstance(o, URIRef):
            obj = self.n_from_uri(o)
            if not obj:
                return
            yield (IC[quote(obj["B"])], SKOS.narrower, o), None
            for child in obj.get("C", []):
                yield (IC[quote(child)], SKOS.broader, o), None
            for rr in obj.get("RR", []):
                yield (IC[quote(rr)], SKOS.related, o), None
            return

        obj = self.n_from_uri(uriref)
        if not obj:
            return
        notation = obj["N"][0]

        if o and p == RDF.type and o != SKOS.Concept:
            return
        if o and p == SKOS.notation and o != notation:
            return

        def p_(tipe):
            if (p is None) or (p == tipe):
                return True

        triples = []

        N = IC[quote(notation)]
        if p_(RDF.type):
            triples.append((N, RDF.type, SKOS.Concept))
        if p_(SKOS.notation):
            triples.append((N, SKOS.notation, Literal(notation)))
        if p_(SKOS.inScheme):
            triples.append(
                (N, SKOS.inScheme, URIRef("http://iconclass.org/rdf/2011/09/"))
            )
        if p_(SKOS.related) and "R" in obj:
            for related in obj.get("R"):
                if o is None or o == IC[quote(related)]:
                    triples.append((N, SKOS.related, IC[quote(related)]))
        if p_(SKOS.broader) and "B" in obj:
            if o is None or o == IC[quote(obj["B"])]:
                triples.append((N, SKOS.broader, IC[quote(obj["B"])]))
        if p_(SKOS.narrower) and "C" in obj:
            for child in obj.get("C", []):
                if os is None or o == IC[quote(child)]:
                    triples.append((N, SKOS.narrower, IC[quote(child)]))

        cursor = get_cursor()
        if p_(SKOS.prefLabel):
            for t in cursor.execute(
                "SELECT * FROM txts WHERE notation = ?", (notation,)
            ):
                _, lang, txt = t
                triples.append((N, SKOS.prefLabel, Literal(txt, lang=lang)))
        if p_(DC.subject):
            for t in cursor.execute(
                "SELECT * FROM kwds WHERE notation = ?", (notation,)
            ):
                _, lang, kws = t
                for kw in kws.split("\n"):
                    triples.append((N, DC.subject, Literal(kw, lang=lang)))

        for t in triples:
            if p is None and o is None:
                yield t, None
            elif p is None and o == t[2]:
                yield t, None
            elif p == t[1] and o == t[2]:
                yield t, None
            elif p == t[1] and o is None:
                yield t, None

    def triple_predicate_object(self, p, o):
        obj = self.n_from_uri(o)
        if not obj:
            return
        if p == SKOS.broader:
            for child in obj.get("C", []):
                yield (IC[quote(child)], SKOS.broader, o), None
        if p == SKOS.narrower:
            yield (IC[quote(obj["B"])], SKOS.narrower, o), None

        cursor = get_cursor()
        if p == SKOS.prefLabel and isinstance(o, Literal):
            if o.language:
                res = cursor.execute(
                    "SELECT * FROM txts WHERE txt = ? AND lang = ?", (o, o.language)
                )
            else:
                res = cursor.execute("SELECT * FROM txts WHERE txt = ?", (o,))
            for t in res:
                notation, lang, _ = t
                yield (IC[quote(notation)], SKOS.prefLabel, o), None
        if p == DC.subject and isinstance(o, Literal):
            if o.language:
                res = cursor.execute(
                    "SELECT * FROM kwds WHERE kw = ? AND lang = ?", (o, o.language)
                )
            else:
                res = cursor.execute("SELECT * FROM kwds WHERE kw = ?", (o,))
            for t in res:
                notation, lang, _ = t
                yield (IC[quote(notation)], DC.subject, o), None

    def notations_iterator(self, p, o):
        for n in self.sorted_notations[:MAX_EMPTY_SUBJECTS_ITERATION]:
            for x in self.triple_notation(IC[quote(n)], p, o):
                yield x

    def triples(self, triple_pattern, context=None):
        s, p, o = triple_pattern
        if s is None and o is None:
            for ss, pp, oo in TRIPLE_CACHE.copy():
                if pp == p:
                    yield (ss, pp, oo), None
            return
        for x in self.triples_(triple_pattern, context):
            TRIPLE_CACHE.add(x[0])
            logging.debug(f"want: {s}, {p}, {o}")
            logging.debug(f"got: {x[0][0]}, {x[0][1]}, {x[0][2]}")
            yield x

    def triples_(self, triple_pattern, context=None):
        self.triple_call_count += 1
        s, p, o = triple_pattern

        if s is None:
            if p == RDF.type and o == SKOS.Concept:
                for x in self.notations_iterator(p, None):
                    yield x
            elif not p is None and not o is None:
                for x in self.triple_predicate_object(p, o):
                    yield x
            elif p is None and not o is None:
                for x in self.triple_notation(s, p, o):
                    yield x
            else:
                for x in self.notations_iterator(p, None):
                    yield x
        else:
            for x in self.triple_notation(s, p, o):
                yield x


register("IconclassStore", Store, "app.store", "IconclassStore")


if __name__ == "__main__":
    g = Graph(store="IconclassStore")
    g.bind("ic", IC)
    g.bind("rdf", RDF)
    g.bind("skos", SKOS)
    for x in g.query("""SELECT ?s ?p ?o WHERE {?s ?p ?o} LIMIT 50"""):
        print(x)
