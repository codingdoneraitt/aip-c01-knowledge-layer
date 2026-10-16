"""Template for fetchers: subclasses only say what to discover and how to fetch one target."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from itertools import islice

from aipc01_core.http import FetchError, PoliteClient
from aipc01_core.models import Document
from aipc01_core.report import Failure, FetchReport
from aipc01_core.store import DocumentStore, WriteResult
from aipc01_core.validate import Level, has_errors, validate_document

log = logging.getLogger(__name__)

PROGRESS_EVERY = 100


@dataclass(frozen=True)
class Target:
    """One unit of work. `context` carries manifest data the fetcher needs later."""

    url: str
    context: dict[str, object] = field(default_factory=dict)


class BaseFetcher(ABC):
    source: str

    def __init__(self, client: PoliteClient, store: DocumentStore, *, workers: int = 4) -> None:
        self.client = client
        self.store = store
        self.workers = workers
        self.discovery_failures: list[Failure] = []

    @abstractmethod
    def discover(self) -> Iterable[Target]:
        """Enumerate everything this fetcher should fetch."""

    @abstractmethod
    def fetch(self, target: Target) -> list[Document]:
        """Fetch one target. May return several documents (e.g. one per region)."""

    def run(self, limit: int | None = None) -> FetchReport:
        report = FetchReport(source=self.source)
        targets = list(islice(self.discover(), limit))
        report.discovered = len(targets)
        report.failed.extend(self.discovery_failures)
        done = 0
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            for outcome in pool.map(self._safe_fetch, targets):
                if isinstance(outcome, Failure):
                    report.failed.append(outcome)
                else:
                    report.skipped += 0 if outcome else 1
                    for doc in outcome:
                        self._store(doc, report)
                done += 1
                if done % PROGRESS_EVERY == 0:
                    log.info("progress %d/%d | %s", done, len(targets), report.summary())
        log.info(report.summary())
        return report

    def _safe_fetch(self, target: Target) -> list[Document] | Failure:
        try:
            return self.fetch(target)
        except FetchError as exc:
            return Failure(target.url, str(exc))
        except Exception as exc:  # noqa: BLE001 - one bad page must not stop the run
            log.exception("unexpected error for %s", target.url)
            return Failure(target.url, f"{type(exc).__name__}: {exc}")

    def _store(self, doc: Document, report: FetchReport) -> None:
        issues = validate_document(doc)
        if has_errors(issues):
            reasons = "; ".join(i.message for i in issues if i.level is Level.ERROR)
            report.invalid.append(Failure(doc.meta.source_url, reasons))
            return
        path, result = self.store.write(doc)
        if result is WriteResult.WRITTEN:
            report.written += 1
            report.bytes_written += path.stat().st_size
        else:
            report.unchanged += 1


class CompositeFetcher(BaseFetcher):
    """Runs several fetchers as one: discovery is concatenated, `fetch` is delegated."""

    _CHILD_KEY = "_child"

    def __init__(self, children: list[BaseFetcher], *, source: str, workers: int = 4) -> None:
        first = children[0]
        super().__init__(first.client, first.store, workers=workers)
        self.source = source
        self.children = children

    def discover(self) -> Iterable[Target]:
        for child in self.children:
            yield from (
                Target(t.url, {**t.context, self._CHILD_KEY: child}) for t in child.discover()
            )
            self.discovery_failures.extend(child.discovery_failures)

    def fetch(self, target: Target) -> list[Document]:
        child: BaseFetcher = target.context[self._CHILD_KEY]  # type: ignore[assignment]
        return child.fetch(target)
