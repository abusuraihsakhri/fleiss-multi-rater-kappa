"""
Automated Pytest Test Suite for Fleiss Multi Rater Kappa.
Domain: Clinical & Biomedical AI
Standard: CAP / CLSI / ISO Standards
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.base import PHIGuard, AuditLogger, SecurityException
from agents.models import SystemTaskPayload, UrgencyLevel, SystemIntegrityStatus
from agents.workers import InvariantQCWorker, SafetyEscalationWorker, ProtocolConformanceWorker
from agents.supervisor import SystemSupervisor
from cli import main


def test_phi_guard_enforcement():
    with pytest.raises(SecurityException):
        PHIGuard.assert_no_phi("Patient MRN-994827 blood culture positive for Staphylococcus")

    # Clean text passes
    PHIGuard.assert_no_phi("Analytical assay specimen KEY-001 optimal")


def test_specialized_workers():
    # Worker 1: QC Invariant
    p1 = SystemTaskPayload(task_id="T1", target_identifier="KEY-01", primary_metric=35.0)
    alerts1 = InvariantQCWorker.evaluate(p1)
    assert len(alerts1) == 1
    assert alerts1[0].urgency == UrgencyLevel.ELEVATED

    # Worker 2: Safety
    p2 = SystemTaskPayload(task_id="T2", target_identifier="KEY-02", primary_metric=10.0, is_critical_flag=True)
    alerts2 = SafetyEscalationWorker.evaluate(p2)
    assert len(alerts2) == 1
    assert alerts2[0].urgency == UrgencyLevel.CRITICAL_STAT

    # Worker 3: Protocol Conformance
    p3 = SystemTaskPayload(task_id="T3", target_identifier="KEY-03", primary_metric=10.0, status_descriptor="DISCORDANT_ANOMALY")
    alerts3 = ProtocolConformanceWorker.evaluate(p3)
    assert len(alerts3) == 1


def test_supervisor_consensus_and_audit():
    supervisor = SystemSupervisor(model_provider="mock")
    payload = SystemTaskPayload(
        task_id="TASK-PROD-01",
        target_identifier="KEY-PROD-01",
        primary_metric=12.0,
        secondary_metric=4.0,
        status_descriptor="NOMINAL"
    )
    dossier = supervisor.process_task(payload)
    assert dossier.overall_urgency == UrgencyLevel.ROUTINE
    assert dossier.integrity_status == SystemIntegrityStatus.VALIDATED
    assert dossier.audit_hash != ""

    # Verify cryptographic audit trail
    assert AuditLogger.verify_integrity() is True

    # CLI tests
    assert main(["audit", "--task-id", "CLI-TEST-01"]) == 0
    assert main(["chat", "Explain", "specifications"]) == 0
    assert main(["verify-audit"]) == 0

def test_audit_chain_detects_signature_tampering():
    from agents.base import AuditTrail
    log = AuditTrail(secret_key="test-only-nonproduction-key")
    log.log("operator", "unit-test", "created", {"value": "a"})
    log.log("operator", "unit-test", "updated", {"value": "b"})
    assert log.verify_integrity()
    snapshot = log.get_trail()
    snapshot[0]["event_type"] = "tampered-copy"
    assert log.verify_integrity()
    log.logs[0]["event_type"] = "tampered-live-record"
    assert not log.verify_integrity()

def test_supervisor_batch_false_flag_is_not_critical(tmp_path):
    import csv
    inp = tmp_path / "tasks.csv"
    out = tmp_path / "results.csv"
    inp.write_text(
        "task_id,target_identifier,primary_metric,secondary_metric,status_descriptor,is_critical_flag\n"
        "T1,SPECIMEN-01,5,2,NOMINAL,false\n",
        encoding="utf-8",
    )
    assert main(["batch", "-i", str(inp), "-o", str(out)]) == 0
    with out.open(newline="", encoding="utf-8") as f:
        row = next(csv.DictReader(f))
    assert row["overall_urgency"] == "ROUTINE"


def test_kappa_api_computes_actual_agreement_and_rejects_invalid():
    from fastapi import HTTPException
    from agents.api import KappaRequest, api_kappa
    result = api_kappa(KappaRequest(matrix=[[3, 0], [0, 3]]))
    assert result["kappa"] == 1.0
    with pytest.raises(HTTPException) as exc:
        api_kappa(KappaRequest(matrix=[[2, 1], [3, 1]]))
    assert exc.value.status_code == 422
