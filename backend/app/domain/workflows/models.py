"""Executable workflow-model primitives used for model-based testing."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Generic, Iterable, TypeVar

StateT = TypeVar("StateT")


@dataclass(frozen=True, slots=True)
class WorkflowModel(Generic[StateT]):
    """Executable transition graph for one workflow domain."""

    name: str
    states: tuple[StateT, ...]
    transitions: dict[StateT, tuple[StateT, ...]]
    initial_states: tuple[StateT, ...]

    def allowed_targets(self, state: StateT) -> tuple[StateT, ...]:
        return self.transitions.get(state, ())

    def can_transition(self, current: StateT, target: StateT) -> bool:
        if current == target:
            return True
        return target in self.allowed_targets(current)

    def terminal_states(self) -> tuple[StateT, ...]:
        return tuple(state for state in self.states if not self.allowed_targets(state))

    def reachable_states(self, start_states: Iterable[StateT] | None = None) -> frozenset[StateT]:
        seeds = tuple(start_states or self.initial_states)
        visited: set[StateT] = set(seeds)
        queue: deque[StateT] = deque(seeds)
        while queue:
            current = queue.popleft()
            for target in self.allowed_targets(current):
                if target in visited:
                    continue
                visited.add(target)
                queue.append(target)
        return frozenset(visited)

    def enumerate_paths(
        self,
        max_steps: int,
        start_states: Iterable[StateT] | None = None,
    ) -> tuple[tuple[StateT, ...], ...]:
        if max_steps < 0:
            raise ValueError("max_steps must be >= 0")

        seeds = tuple(start_states or self.initial_states)
        paths: list[tuple[StateT, ...]] = []

        def walk(path: tuple[StateT, ...], remaining_steps: int) -> None:
            current = path[-1]
            targets = self.allowed_targets(current)
            if remaining_steps == 0 or not targets:
                paths.append(path)
                return
            for target in targets:
                walk(path + (target,), remaining_steps - 1)

        for seed in seeds:
            walk((seed,), max_steps)

        return tuple(paths)
