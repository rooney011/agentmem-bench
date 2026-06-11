"""S5 — Cross-workflow isolation. DESIGN §4 S5.

Two workflows, three agents each, 50 writes per workflow. A reader in workflow A
searches for content known to live in workflow B. Any non-global leak is a bug.
"""

from __future__ import annotations

import random

from ..adapter import SUTAdapter
from ..types import Capability
from .base import Scenario, MetricResult

WF_A = "s5-wf-a"
WF_B = "s5-wf-b"
N = 50


class S5Isolation(Scenario):
    id = "S5"
    slug = "s5_isolation"
    title = "Cross-workflow isolation"
    requires = frozenset({Capability.SCOPES})

    def run(self, sut: SUTAdapter) -> list[MetricResult]:
        if not sut.supports(Capability.SCOPES):
            return [self.na("S5.leakage_rate", "no scope capability")]

        rng = random.Random(5)
        agents_a = ["a1", "a2", "a3"]
        agents_b = ["b1", "b2", "b3"]
        b_tokens: list[str] = []
        for i in range(N):
            sut.write(f"AlphaEntity{i} is value-{rng.randint(0, 9999)}.",
                      agent_id=rng.choice(agents_a), scope="team", workflow_id=WF_A)
            tok = f"BetaSecret{i}"
            sut.write(f"{tok} is value-{rng.randint(0, 9999)}.",
                      agent_id=rng.choice(agents_b), scope="team", workflow_id=WF_B)
            b_tokens.append(tok)

        # Reader in workflow A searches for each workflow-B token.
        leaks = 0
        for tok in b_tokens:
            hits = sut.search(tok, agent_id="a1", workflow_id=WF_A)
            if hits:
                leaks += 1
        rate = leaks / len(b_tokens)
        return [self.check("S5.leakage_rate", rate == 0.0, value=f"{rate:.1%}",
                           detail=f"{leaks}/{len(b_tokens)} workflow-A searches surfaced workflow-B content")]
