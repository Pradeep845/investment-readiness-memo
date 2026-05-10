"""Quick verification that wire results are now exploded into multiple evidence rows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.scoring import build_investability_report

r = build_investability_report(
    company_name="Stripe",
    website_url="https://stripe.com",
    scrape_payload={
        "results": [
            {"url": "https://stripe.com/about", "markdown": "# About Stripe\nPayments infrastructure for the internet."},
            {"url": "https://stripe.com/customers", "markdown": "# Customers\nUber, Shopify, Amazon trust Stripe."},
        ]
    },
    research_payload={"generatedJson": {"summary": "Stripe is a global payments company."}},
    stock_signal=None,
    wire_results=[
        {
            "catalog_slug": "wikipedia",
            "ok": True,
            "action_id": "wp_search",
            "data": {
                "results": [
                    {"title": "Stripe, Inc.", "pageid": 32845520, "snippet": '<span class="searchmatch">Stripe</span>, Inc. is...'},
                    {"title": "Stripe", "pageid": 1258388, "snippet": "Stripe disambiguation."},
                ]
            },
        },
        {
            "catalog_slug": "google_news",
            "ok": True,
            "action_id": "gn_related",
            "data": {
                "data": [
                    {"title": "Stripe Q1 results", "url": "https://news.example.com/q1", "publisher": "Reuters"},
                    {"title": "Stripe expands India ops", "url": "https://news.example.com/india", "publisher": "TechCrunch"},
                ]
            },
        },
    ],
)
print("evidence_count:", len(r["evidence"]))
for e in r["evidence"]:
    print(" -", e["title"], "|", e["source"], "|", e["url"][:60])
