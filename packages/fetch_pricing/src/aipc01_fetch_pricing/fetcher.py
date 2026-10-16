from __future__ import annotations

import json
import logging
from collections.abc import Iterable

from aipc01_core import BaseFetcher, Document, DocumentMeta, Target
from aipc01_core.http import NotFound
from aipc01_core.report import Failure
from aipc01_core.store import slugify

from aipc01_fetch_pricing.manifest import Offer, PricingManifest
from aipc01_fetch_pricing.render import render_family, rows_by_family

log = logging.getLogger(__name__)


class PricingFetcher(BaseFetcher):
    """One target per (offer, region); one document per product family."""

    source = "pricing"

    def __init__(self, manifest: PricingManifest, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.manifest = manifest

    def _offer_url(self, offer: Offer, tail: str) -> str:
        return f"{self.manifest.base_url}/offers/v1.0/aws/{offer.offer_code}/current/{tail}"

    def discover(self) -> Iterable[Target]:
        for offer in self.manifest.offers:
            try:
                available = json.loads(
                    self.client.get(self._offer_url(offer, "region_index.json")).text
                )["regions"]
            except (NotFound, KeyError, ValueError) as exc:
                self.discovery_failures.append(Failure(offer.offer_code, f"no region index: {exc}"))
                continue
            for region in self.manifest.regions:
                if region in available:
                    yield Target(
                        self._offer_url(offer, f"{region}/index.json"),
                        {"offer": offer, "region": region},
                    )
                else:
                    log.info("%s is not offered in %s", offer.offer_code, region)

    def fetch(self, target: Target) -> list[Document]:
        offer: Offer = target.context["offer"]  # type: ignore[assignment]
        region = str(target.context["region"])
        data = json.loads(self.client.get(target.url).text)
        published = str(data.get("publicationDate", ""))
        docs = []
        for family, rows in sorted(rows_by_family(data).items()):
            title = f"{offer.title} pricing: {family} ({region})"
            body = (
                f"# {title}\n\n"
                f"Source: AWS Price List API, offer `{offer.offer_code}`, region `{region}`, "
                f"published {published[:10]}. Prices in USD.\n\n"
                f"{render_family(family, rows)}"
            )
            meta = DocumentMeta(
                source_url=f"{target.url}#{slugify(family)}",
                source_type="pricing",
                title=title,
                collection=f"{offer.id}-pricing",
                exam_domains=offer.exam_domains,
                services=offer.services,
                license_note="AWS Price List bulk API (public).",
                extra={
                    "offer": offer.offer_code,
                    "region": region,
                    "family": family,
                    "published": published[:10],
                    "rows": len(rows),
                },
            )
            docs.append(
                Document(meta=meta, body=body, slug=f"{offer.id}--{region}--{slugify(family)}")
            )
        return docs
