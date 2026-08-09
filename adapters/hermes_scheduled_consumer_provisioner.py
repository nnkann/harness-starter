from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from harness_runtime.scheduled_consumer import validate_scheduled_consumer

RECEIPT_SCHEMA = "harness.scheduled-readonly-consumer-receipt.v1"
PROVISIONER_IDENTITY = "hermes_scheduled_consumer_provisioner"
RECEIPT_ACTIONS = {"created", "updated", "noop"}
RECEIPT_KEYS = {
    "schema",
    "action",
    "provisioner",
    "owner",
    "job_id",
    "declaration_digest",
    "source",
}
SOURCE_KEYS = {"class", "ref", "availability"}
AVAILABILITY_KEYS = {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"}


class ProvisioningError(ValueError):
    pass


def _owner(plan: dict[str, Any]) -> dict[str, str]:
    return {
        "project_id": plan["project"]["id"],
        "job_identity": plan["job"]["identity"],
    }


def _argv(plan: dict[str, Any], job_id: str | None) -> list[str]:
    job = plan["job"]
    script = plan["script"]
    if job_id is None:
        return [
            "hermes", "cron", "create", job["schedule"], "--no-agent",
            "--script", script["identity"], "--deliver", job["delivery"],
            "--name", job["identity"],
        ]
    return [
        "hermes", "cron", "edit", job_id, "--schedule", job["schedule"], "--no-agent",
        "--script", script["identity"], "--deliver", job["delivery"],
        "--name", job["identity"],
    ]


def _receipt(plan: dict[str, Any], job_id: str, action: str) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "action": action,
        "provisioner": PROVISIONER_IDENTITY,
        "owner": _owner(plan),
        "job_id": job_id,
        "declaration_digest": plan["declaration_digest"],
        "source": {
            "class": plan["source"]["class"],
            "ref": plan["source"]["ref"],
            "availability": dict(plan["source"]["availability"]),
        },
    }


def _validate_receipt(plan: dict[str, Any], receipt: object) -> tuple[dict[str, Any], str]:
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_KEYS:
        raise ProvisioningError("invalid receipt shape")
    if receipt["schema"] != RECEIPT_SCHEMA:
        raise ProvisioningError("scheduled consumer ownership is absent")
    if receipt["action"] not in RECEIPT_ACTIONS:
        raise ProvisioningError("invalid receipt action")
    if receipt["provisioner"] != PROVISIONER_IDENTITY:
        raise ProvisioningError("invalid receipt provisioner")

    owner = receipt["owner"]
    if not isinstance(owner, dict) or set(owner) != {"project_id", "job_identity"}:
        raise ProvisioningError("invalid receipt owner shape")
    if owner != _owner(plan):
        raise ProvisioningError("foreign ownership receipt")

    source = receipt["source"]
    if not isinstance(source, dict) or set(source) != SOURCE_KEYS:
        raise ProvisioningError("invalid receipt source shape")
    availability = source["availability"]
    if (
        not isinstance(availability, dict)
        or set(availability) != AVAILABILITY_KEYS
        or any(not isinstance(value, bool) for value in availability.values())
    ):
        raise ProvisioningError("invalid receipt source availability")
    if source != plan["source"]:
        raise ProvisioningError("invalid receipt source")

    job_id = receipt["job_id"]
    if not isinstance(job_id, str) or not job_id:
        raise ProvisioningError("receipt/job mismatch")
    digest = receipt["declaration_digest"]
    if not isinstance(digest, str) or not digest.startswith("sha256:") or len(digest) != 71:
        raise ProvisioningError("invalid receipt declaration digest")
    return receipt, job_id


def reconcile_scheduled_consumer(
    project_root: str | Path,
    declaration: object,
    *,
    jobs: list[dict[str, Any]],
    receipt: object,
    invoke: Callable[[list[str]], object],
) -> dict[str, Any]:
    plan = validate_scheduled_consumer(project_root, declaration)
    identity = plan["job"]["identity"]
    name_matches = [job for job in jobs if isinstance(job, dict) and job.get("name") == identity]

    if len(name_matches) > 1:
        raise ProvisioningError("duplicate scheduled consumer identity match")
    if receipt is None:
        if name_matches:
            raise ProvisioningError("scheduled consumer ownership is absent; refusing name-only adoption")
        argv = _argv(plan, None)
        result = invoke(argv)
        job_id = result.get("job_id") if isinstance(result, dict) else None
        if not isinstance(job_id, str) or not job_id:
            raise ProvisioningError("create did not return an exact job ID")
        return {
            "operation": "create",
            "receipt": _receipt(plan, job_id, "created"),
            "invocations": [argv],
        }

    receipt, job_id = _validate_receipt(plan, receipt)
    exact_matches = [job for job in jobs if isinstance(job, dict) and job.get("id") == job_id]
    if len(exact_matches) != 1 or exact_matches[0].get("name") != identity:
        raise ProvisioningError("receipt/job mismatch")
    if receipt["declaration_digest"] == plan["declaration_digest"]:
        return {"operation": "noop", "receipt": _receipt(plan, job_id, "noop"), "invocations": []}

    argv = _argv(plan, job_id)
    result = invoke(argv)
    returned_id = result.get("job_id") if isinstance(result, dict) else None
    if returned_id != job_id:
        raise ProvisioningError("edit result does not match the stored exact job ID")
    return {
        "operation": "update",
        "receipt": _receipt(plan, job_id, "updated"),
        "invocations": [argv],
    }
