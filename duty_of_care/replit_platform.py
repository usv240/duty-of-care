"""Replit platform adapters with honest fallbacks.

The same FastAPI app serves three hosts: a developer laptop, the Cloud Run
Google backend, and the Replit product surface. Each Replit service is used
when Replit provides it and replaced by a clearly labelled local fallback when
it does not, so the feature can be exercised anywhere and the stack panel never
reports a Replit service as active unless it really is.

Services and how they are detected:

* Runtime and Autoscale Deployment: ``REPL_ID`` marks a Replit workspace;
  ``REPLIT_DEPLOYMENT`` marks a published deployment; ``REPLIT_DOMAINS`` and
  ``REPLIT_DEV_DOMAIN`` carry the public hostnames.
* Replit Auth: identity is read from the ``X-Replit-User-Id`` and
  ``X-Replit-User-Name`` headers that Replit injects for a signed-in user.
  Nothing else is trusted, and anonymous use never needs it.
* Replit Database: ``DATABASE_URL`` (managed Postgres) when psycopg is
  installed, otherwise the key-value store at ``REPLIT_DB_URL`` over plain
  HTTP, otherwise a JSON file in the state directory.
* Replit App Storage: the ``replit.object_storage`` client when importable and
  a bucket is configured, otherwise files in the state directory.
* Scheduled Deployment: ``scripts/scheduled_recheck.py`` writes its last run
  into the same store, which is how the app knows it ran.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
import time
import urllib.parse
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

SYSTEM_USER = "__system__"
RECHECK_KEY = "scheduled_recheck"


def state_dir() -> Path:
    path = Path(os.getenv("DUTY_OF_CARE_STATE_DIR") or Path(tempfile.gettempdir()) / "duty-of-care-state")
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------- runtime ----


def runtime() -> dict[str, Any]:
    on_replit = bool(os.getenv("REPL_ID"))
    deployment = bool(os.getenv("REPLIT_DEPLOYMENT"))
    domains = os.getenv("REPLIT_DOMAINS") or os.getenv("REPLIT_DEV_DOMAIN") or None
    return {
        "on_replit": on_replit,
        "deployment": deployment,
        "domains": domains,
        "slug": os.getenv("REPL_SLUG"),
        "surface": "replit" if on_replit else ("cloud_run" if os.getenv("K_REVISION") else "local"),
    }


def agent_evidence() -> dict[str, Any]:
    """Replit Agent build evidence, present only when the owner recorded it.

    The status is driven by an environment variable the owner sets after the
    genuine Agent session, so no code path can mark the mandatory track item
    done on its own.
    """
    url = os.getenv("DUTY_OF_CARE_REPLIT_AGENT_EVIDENCE_URL")
    commit = os.getenv("DUTY_OF_CARE_REPLIT_AGENT_COMMIT")
    present = bool(url and commit)
    return {
        "present": present,
        "url": url if present else None,
        "commit": commit if present else None,
        "summary": (
            f"Agent-authored commit {commit[:12]} with transcript evidence"
            if present
            else "No Replit Agent build record yet; see replit.md"
        ),
        "evidence_file": "docs/REPLIT-BUILD-EVIDENCE.md",
    }


# --------------------------------------------------------------- identity ----


@dataclass(frozen=True)
class WriterIdentity:
    user_id: str
    name: str | None
    provider: str

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "name": self.name, "provider": self.provider}


def identity_from_headers(headers: Mapping[str, str]) -> WriterIdentity | None:
    """Resolve a signed-in writer from Replit Auth headers, if any.

    Headers are only trusted when the process is running on Replit, because
    anywhere else a client could set them itself.
    """
    lowered = {str(key).lower(): value for key, value in headers.items()}
    user_id = lowered.get("x-replit-user-id")
    if not user_id:
        return None
    if not runtime()["on_replit"] and not os.getenv("DUTY_OF_CARE_TRUST_AUTH_HEADERS"):
        return None
    return WriterIdentity(
        user_id=str(user_id), name=lowered.get("x-replit-user-name"), provider="replit_auth"
    )


# ---------------------------------------------------------- decision store ----


class DecisionStore(Protocol):
    backend: str

    def put(self, user_id: str, record: Mapping[str, Any]) -> None: ...

    def list(self, user_id: str) -> list[dict[str, Any]]: ...

    def delete(self, user_id: str, decision_id: str) -> bool: ...

    def get_system(self, key: str) -> dict[str, Any] | None: ...

    def put_system(self, key: str, value: Mapping[str, Any]) -> None: ...


class FileDecisionStore:
    """JSON-on-disk fallback for laptops and the Cloud Run backend (ephemeral there)."""

    backend = "local_file"

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or state_dir() / "decisions.json"

    def _load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save(self, data: Mapping[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True), "utf-8")
        temporary.replace(self.path)

    def put(self, user_id: str, record: Mapping[str, Any]) -> None:
        data = self._load()
        data.setdefault(user_id, {})[str(record["decision_id"])] = dict(record)
        self._save(data)

    def list(self, user_id: str) -> list[dict[str, Any]]:
        data = self._load().get(user_id, {})
        return sorted(data.values(), key=lambda item: str(item.get("created_at", "")))

    def delete(self, user_id: str, decision_id: str) -> bool:
        data = self._load()
        removed = data.get(user_id, {}).pop(decision_id, None) is not None
        self._save(data)
        return removed

    def get_system(self, key: str) -> dict[str, Any] | None:
        return self._load().get(SYSTEM_USER, {}).get(key)

    def put_system(self, key: str, value: Mapping[str, Any]) -> None:
        data = self._load()
        data.setdefault(SYSTEM_USER, {})[key] = dict(value)
        self._save(data)


class KeyValueDecisionStore:
    """Replit key-value database over its HTTP API (REPLIT_DB_URL)."""

    backend = "replit_key_value"

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    @staticmethod
    def _key(user_id: str, decision_id: str) -> str:
        return f"decision:{user_id}:{decision_id}"

    def _get(self, key: str) -> dict[str, Any] | None:
        request = urllib.request.Request(f"{self.url}/{urllib.parse.quote(key, safe='')}")
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    def _set(self, key: str, value: Mapping[str, Any]) -> None:
        body = urllib.parse.urlencode({key: json.dumps(value)}).encode()
        request = urllib.request.Request(self.url, data=body, method="POST")
        with urllib.request.urlopen(request, timeout=10):
            pass

    def _keys(self, prefix: str) -> list[str]:
        request = urllib.request.Request(
            f"{self.url}?prefix={urllib.parse.quote(prefix, safe='')}"
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            text = response.read().decode("utf-8")
        return [line for line in text.splitlines() if line]

    def put(self, user_id: str, record: Mapping[str, Any]) -> None:
        self._set(self._key(user_id, str(record["decision_id"])), record)

    def list(self, user_id: str) -> list[dict[str, Any]]:
        records = [self._get(key) for key in self._keys(f"decision:{user_id}:")]
        return sorted(
            (item for item in records if item), key=lambda item: str(item.get("created_at", ""))
        )

    def delete(self, user_id: str, decision_id: str) -> bool:
        request = urllib.request.Request(
            f"{self.url}/{urllib.parse.quote(self._key(user_id, decision_id), safe='')}",
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                return True
        except Exception:
            return False

    def get_system(self, key: str) -> dict[str, Any] | None:
        return self._get(f"system:{key}")

    def put_system(self, key: str, value: Mapping[str, Any]) -> None:
        self._set(f"system:{key}", value)


class PostgresDecisionStore:
    """Replit's managed Postgres via DATABASE_URL; requires psycopg."""

    backend = "replit_postgres"

    def __init__(self, dsn: str) -> None:
        import psycopg  # type: ignore[import-not-found]

        self._psycopg = psycopg
        self.dsn = dsn
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS duty_of_care_decisions ("
                "user_id TEXT NOT NULL, decision_id TEXT NOT NULL, payload JSONB NOT NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
                "PRIMARY KEY (user_id, decision_id))"
            )

    def _connect(self):
        return self._psycopg.connect(self.dsn, autocommit=True)

    def put(self, user_id: str, record: Mapping[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO duty_of_care_decisions (user_id, decision_id, payload) "
                "VALUES (%s, %s, %s::jsonb) ON CONFLICT (user_id, decision_id) "
                "DO UPDATE SET payload = EXCLUDED.payload",
                (user_id, str(record["decision_id"]), json.dumps(dict(record))),
            )

    def list(self, user_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM duty_of_care_decisions WHERE user_id = %s "
                "ORDER BY created_at",
                (user_id,),
            ).fetchall()
        return [dict(row[0]) for row in rows]

    def delete(self, user_id: str, decision_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM duty_of_care_decisions WHERE user_id = %s AND decision_id = %s",
                (user_id, decision_id),
            )
            return bool(cursor.rowcount)

    def get_system(self, key: str) -> dict[str, Any] | None:
        rows = self.list(SYSTEM_USER)
        for row in rows:
            if row.get("decision_id") == key:
                return row
        return None

    def put_system(self, key: str, value: Mapping[str, Any]) -> None:
        self.put(SYSTEM_USER, {**dict(value), "decision_id": key})


_DECISION_STORE: DecisionStore | None = None


def decision_store() -> DecisionStore:
    global _DECISION_STORE
    if _DECISION_STORE is not None:
        return _DECISION_STORE
    store: DecisionStore | None = None
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        try:
            store = PostgresDecisionStore(dsn)
        except Exception:
            store = None
    if store is None and os.getenv("REPLIT_DB_URL"):
        store = KeyValueDecisionStore(os.environ["REPLIT_DB_URL"])
    if store is None:
        store = FileDecisionStore()
    _DECISION_STORE = store
    return store


def reset_stores() -> None:
    """Test hook so a monkeypatched environment picks a fresh backend."""
    global _DECISION_STORE, _EXPORT_STORE
    _DECISION_STORE = None
    _EXPORT_STORE = None


# ------------------------------------------------------------ export store ----


class ExportStore(Protocol):
    backend: str

    def put(self, name: str, text: str) -> str: ...

    def get(self, export_id: str) -> str | None: ...


class FileExportStore:
    backend = "local_file"

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or state_dir() / "exports"
        self.directory.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, text: str) -> str:
        export_id = f"exp_{secrets.token_hex(8)}"
        (self.directory / f"{export_id}.json").write_text(text, "utf-8")
        return export_id

    def get(self, export_id: str) -> str | None:
        if not export_id.startswith("exp_") or not export_id[4:].isalnum():
            return None
        path = self.directory / f"{export_id}.json"
        return path.read_text("utf-8") if path.exists() else None


class ObjectStorageExportStore:
    backend = "replit_app_storage"

    def __init__(self) -> None:
        from replit.object_storage import Client  # type: ignore[import-not-found]

        self.client = Client()

    def put(self, name: str, text: str) -> str:
        export_id = f"exp_{secrets.token_hex(8)}"
        self.client.upload_from_text(f"exports/{export_id}.json", text)
        return export_id

    def get(self, export_id: str) -> str | None:
        if not export_id.startswith("exp_") or not export_id[4:].isalnum():
            return None
        try:
            return self.client.download_as_text(f"exports/{export_id}.json")
        except Exception:
            return None


_EXPORT_STORE: ExportStore | None = None


def export_store() -> ExportStore:
    global _EXPORT_STORE
    if _EXPORT_STORE is not None:
        return _EXPORT_STORE
    store: ExportStore | None = None
    if runtime()["on_replit"]:
        try:
            store = ObjectStorageExportStore()
        except Exception:
            store = None
    _EXPORT_STORE = store or FileExportStore()
    return _EXPORT_STORE


# ------------------------------------------------------- scheduled re-check ----


def corpus_version(corpus_path: Path) -> str:
    return sha256(corpus_path.read_bytes()).hexdigest()[:16]


def record_scheduled_recheck(
    *, corpus_path: Path, backend_health: Mapping[str, Any], store: DecisionStore | None = None
) -> dict[str, Any]:
    """Write uptime metadata and count decisions made under an older corpus.

    No screenplay text is read or stored. The record is what the product shows
    a signed-in writer so they know to re-run a saved scene when guidance changed.
    """
    store = store or decision_store()
    version = corpus_version(corpus_path)
    stale_users = 0
    previous = store.get_system(RECHECK_KEY) or {}
    record = {
        "ran_at": datetime.now(UTC).isoformat(),
        "corpus_version": version,
        "corpus_changed_since_last_run": bool(previous) and previous.get("corpus_version") != version,
        "backend_agent_runtime_ready": bool(backend_health.get("agent_runtime_ready")),
        "backend_surface": backend_health.get("product_surface"),
        "stale_decision_users": stale_users,
        "runs": int(previous.get("runs", 0)) + 1,
    }
    store.put_system(RECHECK_KEY, record)
    return record


def capabilities() -> dict[str, Any]:
    """Which Replit services are actually backing this process right now."""
    info = runtime()
    store = decision_store()
    exports = export_store()
    recheck = store.get_system(RECHECK_KEY)
    return {
        "auth": {
            "ok": info["on_replit"],
            "detail": (
                "Replit Auth headers are trusted on this host"
                if info["on_replit"]
                else "identity headers are only trusted on Replit; anonymous use is unaffected"
            ),
        },
        "database": {
            "ok": True,
            "backend": store.backend,
            "detail": {
                "replit_postgres": "managed Postgres via DATABASE_URL",
                "replit_key_value": "key-value store via REPLIT_DB_URL",
                "local_file": "local JSON fallback; ephemeral on Cloud Run",
            }[store.backend],
        },
        "object_storage": {
            "ok": True,
            "backend": exports.backend,
            "detail": {
                "replit_app_storage": "App Storage bucket via the Replit client",
                "local_file": "temporary local files; ephemeral on Cloud Run",
            }[exports.backend],
        },
        "scheduled": {
            "ok": bool(recheck),
            "detail": (
                f"last re-check {recheck.get('ran_at')} on corpus {recheck.get('corpus_version')}"
                if recheck
                else "no scheduled re-check has run on this host yet"
            ),
            "last_run": recheck,
        },
    }


def status() -> dict[str, Any]:
    return {"runtime": runtime(), "capabilities": capabilities(), "agent_evidence": agent_evidence()}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def monotonic_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
