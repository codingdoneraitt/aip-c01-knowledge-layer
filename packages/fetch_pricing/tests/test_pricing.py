import json

import httpx
from aipc01_core import DocumentStore, PoliteClient
from aipc01_fetch_pricing import PricingFetcher, PricingManifest, render_family
from aipc01_fetch_pricing.render import format_price, rows_by_family

OFFER = {
    "publicationDate": "2026-10-16T18:00:00Z",
    "products": {
        "S1": {
            "productFamily": "Amazon Bedrock",
            "attributes": {
                "usagetype": "EUC1-NovaMicro-input-tokens",
                "model": "Nova Micro",
                "inferenceType": "Input tokens",
            },
        },
        "S2": {
            "productFamily": "Amazon Bedrock",
            "attributes": {
                "usagetype": "EUC1-NovaMicro-output|tokens",
                "model": "Nova Micro",
                "inferenceType": "Output tokens",
            },
        },
        "S3": {"productFamily": "Storage", "attributes": {"usagetype": "TimedStorage-ByteHrs"}},
    },
    "terms": {
        "OnDemand": {
            "S1": {
                "S1.T": {
                    "priceDimensions": {
                        "S1.T.R": {
                            "unit": "1K tokens",
                            "beginRange": "0",
                            "endRange": "Inf",
                            "pricePerUnit": {"USD": "0.0000350000"},
                            "description": "$0.000035 per 1K input tokens",
                        }
                    }
                }
            },
            "S2": {
                "S2.T": {
                    "priceDimensions": {
                        "S2.T.R": {
                            "unit": "1K tokens",
                            "beginRange": "0",
                            "endRange": "Inf",
                            "pricePerUnit": {"USD": "0.0001400000"},
                            "description": "output",
                        }
                    }
                }
            },
            "S3": {
                "S3.T": {
                    "priceDimensions": {
                        "S3.T.A": {
                            "unit": "GB-Mo",
                            "beginRange": "0",
                            "endRange": "51200",
                            "pricePerUnit": {"USD": "0.0230000000"},
                            "description": "first 50 TB",
                        },
                        "S3.T.B": {
                            "unit": "GB-Mo",
                            "beginRange": "51200",
                            "endRange": "Inf",
                            "pricePerUnit": {"USD": "0.0220000000"},
                            "description": "next",
                        },
                    }
                }
            },
        },
        "Reserved": {
            "S1": {
                "S1.R": {
                    "termAttributes": {
                        "LeaseContractLength": "1yr",
                        "PurchaseOption": "No Upfront",
                    },
                    "priceDimensions": {
                        "S1.R.D": {
                            "unit": "Hrs",
                            "beginRange": "0",
                            "endRange": "Inf",
                            "pricePerUnit": {"USD": "10.5"},
                            "description": "pt",
                        }
                    },
                }
            },
        },
    },
}
MANIFEST = PricingManifest.model_validate(
    {
        "regions": ["eu-central-1", "ap-south-9"],
        "offers": [
            {
                "id": "bedrock",
                "offer_code": "AmazonBedrock",
                "title": "Amazon Bedrock",
                "exam_domains": [4],
            },
            {"id": "ghost", "offer_code": "Ghost", "title": "Ghost"},
        ],
    }
)


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("AmazonBedrock/current/region_index.json"):
        return httpx.Response(200, text=json.dumps({"regions": {"eu-central-1": {}}}))
    if path.endswith("AmazonBedrock/current/eu-central-1/index.json"):
        return httpx.Response(200, text=json.dumps(OFFER))
    return httpx.Response(404)


def test_format_price_trims_zeros_but_keeps_precision():
    assert format_price("0.0000350000") == "0.000035"
    assert format_price("10.0000") == "10" and format_price("0.0000000000") == "0"


def test_rows_group_by_family_with_tiers_and_reserved_terms():
    fam = rows_by_family(OFFER)
    assert set(fam) == {"Amazon Bedrock", "Storage"}
    storage = {tuple(r[3:5]) for r in fam["Storage"]}
    assert storage == {("0 to 51200", "0.023"), ("51200 to Inf", "0.022")}
    terms = {r[1] for r in fam["Amazon Bedrock"]}
    assert terms == {"OnDemand", "Reserved 1yr No Upfront"}


def test_render_escapes_pipes_and_sorts():
    table = render_family("Amazon Bedrock", rows_by_family(OFFER)["Amazon Bedrock"])
    assert table.splitlines()[0].startswith("| Item | Term") and "output\\|tokens" in table


def test_fetcher_writes_one_document_per_family_and_reports_missing_offers(tmp_path):
    client = PoliteClient(transport=httpx.MockTransport(handler), min_interval=0, max_retries=0)
    report = PricingFetcher(MANIFEST, client, DocumentStore(tmp_path)).run()
    assert (report.discovered, report.written, report.invalid) == (1, 2, [])
    assert [f.url for f in report.failed] == ["Ghost"]
    text = (
        tmp_path / "pricing/bedrock-pricing/bedrock--eu-central-1--amazon-bedrock.md"
    ).read_text()
    assert "region: eu-central-1" in text and "| Nova Micro / Input tokens" in text
