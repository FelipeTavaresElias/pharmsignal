"""Proof of concept: top adverse events for one drug from the live openFDA API."""
import os

import requests
from dotenv import load_dotenv

DRUG = "metformin"  # change freely

load_dotenv()

params = {
    "search": f'patient.drug.medicinalproduct:"{DRUG}"',
    "count": "patient.reaction.reactionmeddrapt.exact",
    "limit": 20,
}
api_key = os.environ.get("OPENFDA_API_KEY")
if api_key:
    params["api_key"] = api_key

resp = requests.get("https://api.fda.gov/drug/event.json", params=params, timeout=30)
resp.raise_for_status()

print(f"Top 20 reported adverse events for {DRUG!r} (FAERS via openFDA)\n")
print(f"{'reaction':<45} count")
print("-" * 55)
for row in resp.json()["results"]:
    print(f"{row['term']:<45} {row['count']}")
