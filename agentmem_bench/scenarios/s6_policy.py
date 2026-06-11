"""S6 — Policy fidelity. DESIGN §4 S6.

Run the S1 conflict under each resolution policy and assert the read matches the
policy's documented semantics.
"""

from __future__ import annotations

from ..adapter import SUTAdapter, Unsupported
from ..types import Capability
from .base import Scenario, MetricResult

WF = "s6-wf"


class S6Policy(Scenario):
    id = "S6"
    slug = "s6_policy"
    title = "Policy fidelity"
    requires = frozenset({Capability.POLICIES})

    def _conflict(self, sut: SUTAdapter) -> None:
        sut.setup()
        sut.write("Deadline is Friday.", agent_id="planner", scope="team", role="planner", workflow_id=WF)
        sut.write("Deadline is Monday.", agent_id="executor", scope="team", role="executor", workflow_id=WF)

    def run(self, sut: SUTAdapter) -> list[MetricResult]:
        out: list[MetricResult] = []
        if not sut.supports(Capability.POLICIES):
            for p in ("ignore", "timestamp_wins", "planner_wins", "human_in_loop"):
                out.append(self.na(f"P.{p}.correct", "no policy capability"))
            out.append(self.na("P.human_in_loop.surfaced", "no policy capability"))
            return out

        def read(policy: str) -> list[str]:
            self._conflict(sut)
            sut.set_policy(policy, workflow_id=WF)
            return [h.content.lower() for h in sut.search("Deadline", agent_id="reader", workflow_id=WF)]

        try:
            ig = read("ignore")
            out.append(self.check("P.ignore.correct",
                                  any("friday" in v for v in ig) and any("monday" in v for v in ig),
                                  detail=f"ignore -> {ig} (expect both)"))

            tw = read("timestamp_wins")
            out.append(self.check("P.timestamp_wins.correct",
                                  any("monday" in v for v in tw) and not any("friday" in v for v in tw),
                                  detail=f"timestamp_wins -> {tw} (expect Monday)"))

            pw = read("planner_wins")
            out.append(self.check("P.planner_wins.correct",
                                  any("friday" in v for v in pw) and not any("monday" in v for v in pw),
                                  detail=f"planner_wins -> {pw} (expect Friday)"))

            hil = read("human_in_loop")
            out.append(self.check("P.human_in_loop.correct",
                                  any("friday" in v for v in hil) and any("monday" in v for v in hil),
                                  detail=f"human_in_loop -> {hil} (expect both, unresolved)"))
            # surfaced: an HITL event was emitted for the conflict
            try:
                events = sut.pending_events(workflow_id=WF)
                surfaced = any(e.get("type", "").startswith("conflict") for e in events)
                out.append(self.check("P.human_in_loop.surfaced", surfaced,
                                      detail=f"{len(events)} event(s) emitted"))
            except Unsupported as e:
                out.append(self.na("P.human_in_loop.surfaced", str(e)))
        except Unsupported as e:
            for p in ("ignore", "timestamp_wins", "planner_wins", "human_in_loop"):
                out.append(self.na(f"P.{p}.correct", str(e)))
        return out
