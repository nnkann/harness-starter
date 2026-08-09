import hashlib
import json

import pytest

from harness_runtime.l3_manual_classification import (
    read_manual_classification,
    record_manual_classification,
)


def test_record_manual_classification_persists_exact_candidate_disposition_binding(tmp_path):
    candidate_ref = "C-L3.5:manual-candidate-001"
    disposition = "confirm"
    disposition_ref = "maat/dispositions/C-L3.5:confirm-001"

    observation = record_manual_classification(
        tmp_path,
        candidate_ref=candidate_ref,
        disposition=disposition,
        disposition_ref=disposition_ref,
    )

    assert observation == {
        "schema": "harness.l3-manual-candidate-classification.v1",
        "candidate_ref": candidate_ref,
        "classification_mode": "manual",
        "classifier": "Maat",
        "disposition": disposition,
        "disposition_ref": disposition_ref,
        "producer": "ptah",
        "consumer": "maat",
        "authority_effect": "evidence-only",
    }
    filename = hashlib.sha256(disposition_ref.encode("utf-8")).hexdigest() + ".json"
    persisted_path = tmp_path / "l3-manual-classifications" / filename
    persisted_bytes = persisted_path.read_bytes()
    assert persisted_bytes.endswith(b"\n")
    envelope = json.loads(persisted_bytes)
    canonical_observation = json.dumps(
        observation, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    assert envelope == {
        "observation": observation,
        "observation_sha256": hashlib.sha256(canonical_observation).hexdigest(),
    }
    assert persisted_bytes == (
        json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    assert persisted_path.name == filename
    assert disposition_ref not in str(persisted_path.relative_to(tmp_path))

    with pytest.raises(FileExistsError):
        record_manual_classification(
            tmp_path,
            candidate_ref=candidate_ref,
            disposition="revert",
            disposition_ref=disposition_ref,
        )
    assert persisted_path.read_bytes() == persisted_bytes


def test_read_manual_classification_revalidates_digest_and_expected_consumer(tmp_path):
    candidate_ref = "C-L3.5:manual-candidate-002"
    disposition = "owner-hold"
    disposition_ref = "maat:disposition:C-L3.5:owner-hold-002"

    record_manual_classification(
        tmp_path,
        candidate_ref=candidate_ref,
        disposition=disposition,
        disposition_ref=disposition_ref,
    )

    observation = read_manual_classification(
        tmp_path,
        expected_candidate_ref=candidate_ref,
        expected_disposition=disposition,
        expected_disposition_ref=disposition_ref,
        expected_consumer="maat",
    )
    assert observation["candidate_ref"] == candidate_ref
    assert observation["disposition"] == disposition
    assert observation["disposition_ref"] == disposition_ref
    assert observation["consumer"] == "maat"

    with pytest.raises(ValueError):
        read_manual_classification(
            tmp_path,
            expected_candidate_ref=candidate_ref,
            expected_disposition=disposition,
            expected_disposition_ref=disposition_ref,
            expected_consumer="other-consumer",
        )
    with pytest.raises(ValueError):
        read_manual_classification(
            tmp_path,
            expected_candidate_ref=candidate_ref,
            expected_disposition="revert",
            expected_disposition_ref=disposition_ref,
            expected_consumer="maat",
        )

    filename = hashlib.sha256(disposition_ref.encode("utf-8")).hexdigest() + ".json"
    persisted_path = tmp_path / "l3-manual-classifications" / filename
    envelope = json.loads(persisted_path.read_bytes())
    envelope["observation"]["candidate_ref"] = "tampered-candidate"
    persisted_path.write_bytes(
        (
            json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("utf-8")
    )

    with pytest.raises(ValueError):
        read_manual_classification(
            tmp_path,
            expected_candidate_ref=candidate_ref,
            expected_disposition=disposition,
            expected_disposition_ref=disposition_ref,
            expected_consumer="maat",
        )
