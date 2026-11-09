# Topic-specific collaboration demo regression

The question “Who has TNO collaborated with on Horizon Europe projects about
hydrogen? Show me the organisations and the projects connecting them.” exhausted
the five-request agent loop on 9 November. The network tool returned only general
partner counts, forcing repeated organisation/project lookups to establish the
requested topic and connecting projects.

`get_collaboration_network` now accepts an optional `topic` keyword, applied to
shared project titles, objectives and acronyms in the parameterized graph query.
Each partner includes up to five shared project examples with IDs and CORDIS
links. Existing requests without a topic still retrieve the general network.
The keyword filter is not an exhaustive thematic classification. Results remain
limited to the local project snapshot and the tool's partner/example limits.

The exact English demo question completed against the live production agent core
and real tools in 27.8 seconds, using one topic-filtered network tool call and
returning linked projects without an execution-limit error. This check used no
conversation persistence and did not exercise browser authentication. Twenty-two
focused graph/tool-schema/runtime regression tests passed. The execution limits
were not increased.
