# SPARQL query server

To integrate ICONCLASS with services like the [Termen­netwerk](https://termennetwerk.netwerkdigitaalerfgoed.nl/) we would like to have a [SPARQL](https://en.wikipedia.org/wiki/SPARQL) query service.

Easy! You might say. Let's just dump all the terms to a file on disk, and then load them into a triplestore, and be done.
We tried that. It has some issues. Namely fulltext searches, and secondly, the exploding size of the number of nodes when taking IC "keys" into account.

Firstly, you would like to do some fulltext searches over the data that includes more than just the literals in each triple. For a hierarchical system like ICONCLASS, when you index an item lower down in the tree, you would also like to include the texts and keywords for all "parents" in the tree, to give better recall. There are ways to integrate a search index with the most well known triplestores, but it is not logistically trivial, nor cheap. (if you use commercial triplestore providers)

A first version of the IC sparql service used the Blazegraph store. While blazingly fast, freely available, and widely used, it has very much become "abandoware" after it's authors were hired by AWS. I do not consider it wise to invest more time in a product with no future.

Then the issue of the "exploding numbers" 🤯 when using IC keys. This is explained [here in more detail](https://test.iconclass.org/help/skos_sparql). It boils down to the fact that the core IC system has around 40K terms, but when using keys this count increases to more than 1.2 million. We can't just ignore this feature, it is integral to the system and has been used in databases around the world for more than 40 years to catalog their collections in detail. So we have to support it. And actually, it _is_ very usefiul from an Art Historians perspective...😉

This repository contains a custom [Python RDFlib](https://rdflib.readthedocs.io/en/stable/) based sparql query engine, that integrates searching using the most excellent [SQLITE FTS5](https://www.sqlite.org/fts5.html) (the same index that is used in the ICONCLASS web service).

## This is a work in progress and not Done yet! 🍴

A tested endpoint is available at [https://test.iconclass.org/sparql](https://test.iconclass.org/sparql)
DISCLAIMER: it may go down, it may be unresponsive, there is no crack super devops team that has made it foolproof. (yet)

But we are hard at work crossing the t's and dotting the i's, if you encounter bugs, [please let me know](https://forms.gle/twPq7swQZXmSX46G8) or you can mail me on info@iconclass.org or file some issues in this repo. Or ideally, contribute fixes... ;-)
