"""Create or update a structured Agent Search (Discovery Engine) data store from a JSON corpus.

Defaults provision the guidance corpus. The research evidence store is the same
script with three environment variables:

    VERTEX_SEARCH_DATA_STORE=duty-of-care-evidence \\
    CORPUS_PATH=guidance/evidence.json DOCUMENT_ID_FIELD=record_id \\
    DATA_STORE_DISPLAY_NAME="Duty of Care research evidence" python infra/provision_agent_search.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import discoveryengine_v1 as discoveryengine

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "agentic-fleet-2026")
LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
DATA_STORE = os.getenv("VERTEX_SEARCH_DATA_STORE", "duty-of-care-guidance")
COLLECTION = "default_collection"
CORPUS_PATH = os.getenv("CORPUS_PATH", "guidance/corpus.json")
ID_FIELD = os.getenv("DOCUMENT_ID_FIELD", "clause_id")
DISPLAY_NAME = os.getenv("DATA_STORE_DISPLAY_NAME", "Duty of Care approved guidance")


def load_records(path: Path) -> list[dict]:
    loaded = json.loads(path.read_text("utf-8"))
    return loaded["records"] if isinstance(loaded, dict) else loaded


def main() -> None:
    parent = f"projects/{PROJECT}/locations/{LOCATION}/collections/{COLLECTION}"
    name = f"{parent}/dataStores/{DATA_STORE}"
    stores = discoveryengine.DataStoreServiceClient()
    try:
        stores.get_data_store(name=name)
        print(f"data store exists: {name}")
    except NotFound:
        operation = stores.create_data_store(
            parent=parent,
            data_store=discoveryengine.DataStore(
                display_name=DISPLAY_NAME,
                industry_vertical=discoveryengine.IndustryVertical.GENERIC,
                solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
            ),
            data_store_id=DATA_STORE,
        )
        operation.result(timeout=600)
        print(f"created data store: {name}")

    documents = discoveryengine.DocumentServiceClient()
    branch = f"{name}/branches/default_branch"
    corpus = load_records(Path(__file__).resolve().parents[1] / CORPUS_PATH)
    for record in corpus:
        document_id = str(record[ID_FIELD])
        document = discoveryengine.Document(
            id=document_id,
            name=f"{branch}/documents/{document_id}",
            struct_data=record,
        )
        try:
            documents.create_document(parent=branch, document=document, document_id=document_id)
            print(f"created {document_id}")
        except AlreadyExists:
            documents.update_document(
                request=discoveryengine.UpdateDocumentRequest(document=document, allow_missing=True)
            )
            print(f"updated {document_id}")
    print(f"{len(corpus)} documents in {DATA_STORE} from {CORPUS_PATH}")


if __name__ == "__main__":
    main()
