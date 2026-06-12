# agentmem-bench

A reproducible benchmark for **multi-agent memory systems** — the gap LoCoMo, LongMemEval, and ConvoMem don't cover.

This repo is the methodology + harness + datasets, not a product. Read [`DESIGN.md`](./DESIGN.md) before running anything.

## Why another benchmark

LoCoMo (Maharana et al., ACL 2024) and LongMemEval (ICLR 2025) measure **single-agent long-term memory** — does the model recall what was said earlier? Useful, but Letta has publicly argued these measure retrieval, not agent memory ([Letta blog, 2025](https://www.letta.com/blog/long-conversation-locomo)). And **no existing benchmark stresses multi-agent coordination on memory**: contradictory writes, scope leakage, CRDT convergence, policy enforcement.

`agentmem-bench` fills that gap. We test scenarios with **multiple agents writing and reading shared memory**, and score whether the system:

1. Surfaces or auto-resolves contradictions according to the user's policy
2. Enforces visibility scopes (private / team / global)
3. Converges to a consistent state under concurrent writes (CRDT property)
4. Returns the right answer at the right time (temporal validity)
5. Doesn't leak across workflows / orgs

We run the same scenarios against every shipped memory system (Mem0, Zep, Cognee, Supermemory, LangMem, raw pgvector, AgentMem) on the same hardware with the same LLM, and publish reproducible numbers.

## Status

**Harness skeleton landed (v0.1, Week-1 scope).** The adapter interface, a
reference `FakeSUT`, all seven scenarios (S1–S7) with the metric names from
[`DESIGN.md`](./DESIGN.md), the run loop, and the output format are implemented
and validated end-to-end. Real SUT adapters (pgvector, AgentMem, Mem0, …) are
next. See [`DESIGN.md`](./DESIGN.md) for the methodology.

## Running

No third-party deps for the core + the reference SUT — stdlib only:

```bash
python3 -m agentmem_bench --sut fake --scenarios all   # full run
python3 -m agentmem_bench --sut fake --scenarios s1,s4 # a subset
python3 -m agentmem_bench --list                        # SUTs + scenarios
python3 tests/test_smoke.py                             # smoke tests (no pytest needed)
```

A run writes a self-contained `runs/<run_id>/` directory: `manifest.json`,
`scenarios/<slug>.jsonl` (one line per metric), `timing.json`, `cost.json`, and
a human-readable `summary.md` scorecard. `runs/` is gitignored (published as
release assets, per the design).

### Real SUT adapters

```bash
# pgvector floor — needs Postgres+pgvector + OpenAI embeddings
docker run -d --name amb-pg -e POSTGRES_PASSWORD=bench -e POSTGRES_DB=bench -p 5433:5432 pgvector/pgvector:pg16
DATABASE_URL=postgresql://postgres:bench@localhost:5433/bench OPENAI_API_KEY=... \
  python -m agentmem_bench --sut pgvector --scenarios all      # extra: psycopg[binary], openai

MEM0_API_KEY=...      python -m agentmem_bench --sut mem0 --scenarios all     # extra: mem0ai
AGENTMEM_API_KEY=...  python -m agentmem_bench --sut agentmem --scenarios all # extra: httpx
```

Hosted SUTs with rate/quota limits can scale S7 down with `AMBENCH_S7_WRITES` /
`AMBENCH_S7_SEARCHES` (default stays the design's 1000/500); latency percentiles
are size-robust.

### Comparison matrix

```bash
python -m agentmem_bench.compare      # reads runs/ -> results/COMPARISON.md
```

`compare.py` merges multiple (incl. partial / re-run) `runs/` into one matrix:
for each (SUT, scenario) it uses the most recent run with real metrics and prints
provenance. **The current matrix is committed at [`results/COMPARISON.md`](./results/COMPARISON.md).**

Headline so far (pgvector floor vs mem0 vs agentmem): on multi-agent
coordination, **only AgentMem fills S1** (conflict detection + resolution) — the
one metric that needs a real memory system. **Mem0 ties the raw vector floor**
(no conflict/policy/temporal/CRDT API) and *loses* `S3.team_visible` to it
(content-dedup ignores scope changes). S3/S5 don't separate anyone; S4 is N/A for
every hosted system (no replica API). AgentMem's S5/S6/S7 await a Gemini-quota
reset; its S2 temporal has a gap.

### Adding a system under test

Implement `agentmem_bench.adapter.SUTAdapter` (the small `write` / `search` /
`check_conflicts` / `set_policy` / replica surface), declare its
`capabilities`, and register it in `agentmem_bench/suts/__init__.py`. Methods a
system can't support raise `Unsupported` → the affected metrics score `N/A`, not
a failure. `FakeSUT` (`agentmem_bench/suts/fake.py`) is the worked reference.

## License

[Apache-2.0](./LICENSE) (TBD)
