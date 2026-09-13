# Design Journal directory

Active Design Journals are local, ignored convergence state. They support
explore → evaluate → decide → lock readiness → prepare promotion while intent
is still changing.

Design Journals are not durable architecture authority or a second versioned
history of intent. Promotion moves resolved intent into accepted ADRs,
contracts, schemas, or other governed artifacts. Those promoted substrates and
their Git history are the durable record.

Prepared Promotion Contracts and review handoffs are local mechanical state.
Keep them under ignored operational paths such as `.adr-kit/`; do not commit
them as architecture history.

Historical journals are recovered from Git history when needed. This directory
exists only to explain the local workflow and must remain ignored apart from
this README.
