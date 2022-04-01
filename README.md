# SPARQL query server

To integrate ICONCLASS with services like the [Termen­netwerk](https://termennetwerk.netwerkdigitaalerfgoed.nl/) we would like to have a [SPARQL](https://en.wikipedia.org/wiki/SPARQL) query service.

Easy! You might say. Let's just dump all the terms to a file on disk, and then load them into a triplestore, and be done.
We tried that. It has some issues. Namely fulltext searches, and secondly, the exploding size of the number of nodes when taking IC "keys" into account.

Firstly, you would like to do some fulltext searches over the data that includes more than just the literals in each triple. For a hierarchical system like ICONCLASS, when you index an item lower down in the tree, you would also like to include the texts and keywords for all "parents" in the tree, to give better recall. There are ways to integrate a search index with the most well known triplestores, but it is not logistically trivial, nor cheap. (if you use commercial triplestore providers)

A first version of the IC sparql service used the Blazegraph store. While blazingly fast, freely available, and widely used, it has very much become "abandoware" after it's authors were hired by AWS. I do not consider it wise to invest more time in a product with no future.

Then the issue of the "exploding numbers" 🤯 when using IC keys. This is explained [here in more detail](https://test.iconclass.org/help/skos_sparql). It boils down to the fact that the core IC system has around 40K terms, but when using keys this count increases to more than 1.2 million. We can't just ignore this feature, it is integral to the system and has been used in databases around the world for more than 40 years to catalog their collections in detail. So we have to support it. And actually, it _is_ very useful from an Art Historians perspective...😉

This repository contains a custom [Python RDFlib](https://rdflib.readthedocs.io/en/stable/) based sparql query engine, that integrates searching using the most excellent [SQLITE FTS5](https://www.sqlite.org/fts5.html) (the same index that is used in the ICONCLASS web service).

## This is a work in progress and not Done yet! 🍴

An endpoint is available at [https://test.iconclass.org/sparql](https://test.iconclass.org/sparql)
DISCLAIMER: it may go down, it may be unresponsive, there is no crack super devops team that has made it foolproof. (yet)

**<a href="https://yasgui.triply.cc/#query=PREFIX%20ic%3A%20%3Chttp%3A//iconclass.org/%3E%0ASELECT%20%3Fs%20%3Fp%20%3Fo%20%0AWHERE%20%7B%3Fs%20%3Fp%20%3Fo%7D&endpoint=https%3A//test.iconclass.org/sparql&requestMethod=GET&tabTitle=Query%209&headers=%7B%7D&contentTypeConstruct=application%2Fn-triples%2C*%2F*%3Bq%3D0.9&contentTypeSelect=application%2Fsparql-results%2Bjson%2C*%2F*%3Bq%3D0.9&outputFormat=table">Some test can be done with YASGUI</a>**

But we are hard at work crossing the t's and dotting the i's, if you encounter bugs, [please let me know](https://forms.gle/twPq7swQZXmSX46G8) or you can mail me on info@iconclass.org or file some issues in this repo.

Or ideally, contribute some fixes in a pull request... 🎯

# Credit

Work on this service has been done with support from [FIZ Karlsruhe Information Service Engineering](https://www.fiz-karlsruhe.de/de/forschung/information-service-engineering) and [NFDI4Culture](https://nfdi4culture.de/)

### Related Work

[rdflib-endpoint](https://github.com/vemonet/rdflib-endpoint) ✨️ SPARQL endpoint built with RDFLib to serve RDF files, machine learning models, or any other logic implemented in Python

[SPARQL endpoint for Translator services](https://github.com/vemonet/translator-sparql-service) A SPARQL endpoint to serve NCATS Translator services as SPARQL custom functions. Built with rdflib-endpoint

[Hydra library for Python](https://github.com/pchampin/hydra-py) The primary goal is to provide a lib for easily writing Hydra-enabled clients

[Python Linked Data Fragment Server.](https://github.com/jermnelson/linked-data-fragments) Python Linked Data Fragment server using asyncio and Redis

[ODTMP-TPF](https://github.com/benj-moreau/odmtp-tpf) Triple pattern matching over non-RDF datasources with inference
