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
                display_name="Duty of Care approved guidance",
                industry_vertical=discoveryengine.IndustryVertical.GENERIC,
                solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
            ),
            data_store_id=DATA_STORE,
        )
        operation.result(timeout=600)
        print(f"created data store: {name}")

    documents = discoveryengine.DocumentServiceClient()
    branch = f"{name}/branches/default_branch"
    corpus = json.loads(
        (Path(__file__).resolve().parents[1] / "guidance" / "corpus.json").read_text("utf-8")
    )
    for record in corpus:
        document = discoveryengine.Document(id=record["clause_id"], struct_data=record)
        try:
            documents.create_document(
                parent=branch, document=document, document_id=record["clause_id"]
            )
            print(f"created {record['clause_id']}")
        except AlreadyExists:
            documents.update_document(document=document, allow_missing=False)
            print(f"updated {record['clause_id']}")


if __name__ == "__main__":
    main()
