from rdflib.plugins.sparql.evaluate import evalBGP
from rdflib.plugins.sparql import CUSTOM_EVALS
from rdflib.plugins.sparql.sparql import AlreadyBound
from rdflib.store import Store
from rdflib import URIRef, Graph, Namespace, Literal
from rdflib.term import Variable
from rdflib.namespace import DC, SKOS, RDF
from rdflib.plugin import register
from urllib.parse import quote, unquote
import os, sqlite3, textbase, re, sys

IC = Namespace("http://iconclass.org/")
PREDICATE_FTS = IC.search
PREDICATE_FTS_NOKEYS = IC.searchnokeys
DATA_PATH = os.environ.get("IC_DATA_PATH", "../data/")


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
    for n, obj in d.items():
        for c in obj.get("C", []):
            c_obj = d.get(c)
            if c_obj:
                c_obj["B"] = n

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
        SQL = f"SELECT notation FROM {lang} WHERE {keys}text MATCH ? order by {sort}"
    else:
        SQL = f"SELECT notation FROM notations WHERE notation REGEXP ?"
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
        lang = val.language or "en"
        lang = lang[:2]
        sort = "rank"
        val = str(val)

        search_results = do_search(
            q=val, r="", lang=lang, sort=sort, keys=(qtipe == PREDICATE_FTS)
        )

        for notation in search_results:
            c = ctx.push()
            try:
                c[var] = IC[quote(notation)]
            except AlreadyBound:
                continue

            yield c.solution()


def fts_eval(ctx, part):
    if part.name != "BGP":
        raise NotImplementedError()
    vars = []
    for t in part.triples:
        if not isinstance(t[0], Variable):
            continue
        if t[1] in (PREDICATE_FTS, PREDICATE_FTS_NOKEYS):
            vars.append(t)
    if len(vars) > 0:
        return getq(ctx, vars)
    return evalBGP(ctx, part.triples)


CUSTOM_EVALS["fts_eval"] = fts_eval


class IconclassStore(Store):
    def __init__(self, configuration=None, identifier=None):

        self.NOTATIONS = read_n(DATA_PATH)
        super().__init__(configuration, identifier)

    def triple_notation(self, notation, p):
        def p_(tipe):
            if (p is None) or (p == tipe):
                return True

        if notation not in self.NOTATIONS:
            return

        obj = self.NOTATIONS[notation]

        N = IC[quote(notation)]
        if p_(RDF.type):
            yield (N, RDF.type, SKOS.Concept), None
        if p_(SKOS.notation):
            yield (N, SKOS.notation, Literal(notation)), None
        if p_(SKOS.inScheme):
            yield (N, SKOS.inScheme, URIRef("http://iconclass.org/rdf/2011/09/")), None
        if p_(SKOS.related) and "R" in obj:
            for related in obj.get("R"):
                yield (N, SKOS.related, IC[quote(related)]), None
        if p_(SKOS.broader) and "B" in obj:
            yield (N, SKOS.broader, obj["B"]), None
        if p_(SKOS.narrower) and "C" in obj:
            for child in obj.get("C", []):
                yield (N, SKOS.narrower, IC[quote(child)]), None

        cursor = get_cursor()
        if p_(SKOS.prefLabel):
            for t in cursor.execute(
                "SELECT * FROM txts WHERE notation = ?", (notation,)
            ):
                _, lang, txt = t
                yield (N, SKOS.prefLabel, Literal(txt, lang=lang)), None
        if p_(DC.subject):
            for t in cursor.execute(
                "SELECT * FROM kwds WHERE notation = ?", (notation,)
            ):
                _, lang, kws = t
                for kw in kws.split("\n"):
                    yield (N, DC.subject, Literal(kw, lang=lang)), None

    def triples(self, triple_pattern, context=None):
        s, p, o = triple_pattern

        if s is None:
            for n in self.NOTATIONS:
                for x in self.triple_notation(n, p):
                    yield x
        else:
            # Is this is an ICONCLASS URI?
            tmp = s.split("http://iconclass.org/")
            if len(tmp) != 2:
                return
            n = tmp[-1]
            if not n[0] in "0123456789":
                return
            n = unquote(n)
            for x in self.triple_notation(n, p):
                yield x


register("IconclassStore", Store, "app.store", "IconclassStore")


if __name__ == "__main__":
    g = Graph(store="IconclassStore")
    g.bind("ic", IC)
    g.bind("rdf", RDF)
    g.bind("skos", SKOS)
    for x in g.query("""SELECT ?s ?p ?o WHERE {?s ?p ?o} LIMIT 50"""):
        print(x)
