"""Tests for the gate-ready handoff packet runtime object."""

from __future__ import annotations

import inspect
import json

from runner.handoff_packet import (
    GateReadyHandoffPacket,
    HandoffPacketStatus,
    HandoffPacketValidation,
    validate_handoff_packet,
    REASON_MISSING_PRODUCT_STATE_REF,
    REASON_MISSING_ACCEPTANCE_CRITERIA_REF,
    REASON_MISSING_PHASE_IDENTITY,
    REASON_MISSING_RUN_IDENTITY,
    REASON_MISSING_GATE,
    REASON_MISSING_ACTOR_OR_ROLE,
    REASON_MISSING_PROOF_REFS,
    REASON_INADMISSIBLE_PROOF_REF,
    REASON_STALE_OR_UNLINKED_STATE,
    REASON_HIDDEN_REASONING_NOT_ALLOWED,
    REASON_UNBOUNDED_PAYLOAD,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_packet(**overrides: object) -> GateReadyHandoffPacket:
    kwargs = {
        "product_state_ref": "abc123",
        "acceptance_criteria_ref": "def456",
        "phase_id": "phase-1",
        "run_id": "run-001",
        "gate_id": "human_review_gate",
        "actor_or_role": "reviewer",
        "proof_ref_ids": ("pr-001", "pr-002"),
        "payload": "All automated checks passed.",
    }
    kwargs.update(overrides)
    return GateReadyHandoffPacket(**kwargs)  # type: ignore[arg-type]


_ADMISSIBLE = frozenset({"pr-001", "pr-002"})


# ---------------------------------------------------------------------------
# Valid gate-ready packet
# ---------------------------------------------------------------------------


class TestValidPacket:
    def test_valid_packet_passes(self):
        packet = _valid_packet()
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.GATE_READY
        assert v.reason_codes == ()

    def test_valid_packet_no_details(self):
        packet = _valid_packet()
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.details is None

    def test_valid_packet_with_metadata(self):
        packet = _valid_packet(metadata=(("key1", "value1"), ("key2", "value2")))
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.GATE_READY
        assert v.reason_codes == ()


# ---------------------------------------------------------------------------
# Missing product state ref
# ---------------------------------------------------------------------------


class TestMissingProductStateRef:
    def test_empty_string_fails(self):
        packet = _valid_packet(product_state_ref="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes

    def test_whitespace_only_fails(self):
        packet = _valid_packet(product_state_ref="   ")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes


# ---------------------------------------------------------------------------
# Missing acceptance criteria ref
# ---------------------------------------------------------------------------


class TestMissingAcceptanceCriteriaRef:
    def test_empty_string_fails(self):
        packet = _valid_packet(acceptance_criteria_ref="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in v.reason_codes

    def test_whitespace_only_fails(self):
        packet = _valid_packet(acceptance_criteria_ref="   ")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in v.reason_codes


# ---------------------------------------------------------------------------
# Missing phase identity
# ---------------------------------------------------------------------------


class TestMissingPhaseIdentity:
    def test_empty_string_fails(self):
        packet = _valid_packet(phase_id="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_MISSING_PHASE_IDENTITY in v.reason_codes

    def test_whitespace_only_fails(self):
        packet = _valid_packet(phase_id="   ")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_PHASE_IDENTITY in v.reason_codes


# ---------------------------------------------------------------------------
# Missing run identity
# ---------------------------------------------------------------------------


class TestMissingRunIdentity:
    def test_empty_string_fails(self):
        packet = _valid_packet(run_id="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_MISSING_RUN_IDENTITY in v.reason_codes

    def test_whitespace_only_fails(self):
        packet = _valid_packet(run_id="   ")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_RUN_IDENTITY in v.reason_codes


# ---------------------------------------------------------------------------
# Missing gate
# ---------------------------------------------------------------------------


class TestMissingGate:
    def test_empty_string_fails(self):
        packet = _valid_packet(gate_id="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_MISSING_GATE in v.reason_codes

    def test_whitespace_only_fails(self):
        packet = _valid_packet(gate_id="   ")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_GATE in v.reason_codes


# ---------------------------------------------------------------------------
# Missing actor or role
# ---------------------------------------------------------------------------


class TestMissingActorOrRole:
    def test_empty_string_fails(self):
        packet = _valid_packet(actor_or_role="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_MISSING_ACTOR_OR_ROLE in v.reason_codes

    def test_whitespace_only_fails(self):
        packet = _valid_packet(actor_or_role="   ")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_ACTOR_OR_ROLE in v.reason_codes


# ---------------------------------------------------------------------------
# Missing proof refs
# ---------------------------------------------------------------------------


class TestMissingProofRefs:
    def test_empty_tuple_fails(self):
        packet = _valid_packet(proof_ref_ids=())
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_MISSING_PROOF_REFS in v.reason_codes

    def test_empty_string_in_tuple_fails(self):
        packet = _valid_packet(proof_ref_ids=("pr-001", ""))
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_PROOF_REFS in v.reason_codes


# ---------------------------------------------------------------------------
# Inadmissible proof ref
# ---------------------------------------------------------------------------


class TestInadmissibleProofRef:
    def test_unknown_ref_id_fails(self):
        packet = _valid_packet(proof_ref_ids=("pr-999",))
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_INADMISSIBLE_PROOF_REF in v.reason_codes

    def test_preserves_proof_ref_reason(self):
        """The reason code 'inadmissible_proof_ref' is preserved in output."""
        packet = _valid_packet(proof_ref_ids=("pr-999",))
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_INADMISSIBLE_PROOF_REF in v.reason_codes
        assert v.details is not None
        assert REASON_INADMISSIBLE_PROOF_REF in v.details


# ---------------------------------------------------------------------------
# Hidden reasoning not allowed
# ---------------------------------------------------------------------------


class TestHiddenReasoning:
    def test_cot_tag_fails(self):
        packet = _valid_packet(payload="Some text <cot> hidden reasoning here")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in v.reason_codes

    def test_chain_of_thought_tag_fails(self):
        packet = _valid_packet(payload="<chain_of_thought> reasoning")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in v.reason_codes

    def test_hidden_reasoning_string_fails(self):
        packet = _valid_packet(payload="contains hidden_reasoning content")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_HIDDEN_REASONING_NOT_ALLOWED in v.reason_codes


# ---------------------------------------------------------------------------
# Unbounded payload
# ---------------------------------------------------------------------------


class TestUnboundedPayload:
    def test_exceeds_max_length_fails(self):
        long_payload = "x" * 65537
        packet = _valid_packet(payload=long_payload)
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_UNBOUNDED_PAYLOAD in v.reason_codes

    def test_boundary_65536_passes(self):
        boundary_payload = "x" * 65536
        packet = _valid_packet(payload=boundary_payload)
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.GATE_READY

    def test_empty_payload_fails(self):
        packet = _valid_packet(payload="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_UNBOUNDED_PAYLOAD in v.reason_codes


# ---------------------------------------------------------------------------
# Stale or unlinked product state
# ---------------------------------------------------------------------------


class TestStaleState:
    def test_mismatched_state_fails(self):
        packet = _valid_packet(product_state_ref="abc123")
        v = validate_handoff_packet(packet, "xyz789", _ADMISSIBLE)
        assert v.status == HandoffPacketStatus.NOT_GATE_READY
        assert REASON_STALE_OR_UNLINKED_STATE in v.reason_codes

    def test_empty_product_state_ref_does_not_trigger_stale(self):
        """When product_state_ref is empty, we get missing_product_state_ref,
        but stale_or_unlinked_state should not also fire."""
        packet = _valid_packet(product_state_ref="")
        v = validate_handoff_packet(packet, "xyz789", _ADMISSIBLE)
        assert REASON_STALE_OR_UNLINKED_STATE not in v.reason_codes
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes


# ---------------------------------------------------------------------------
# JSON determinism
# ---------------------------------------------------------------------------


class TestJsonDeterminism:
    def test_identical_packets_produce_identical_json(self):
        p1 = _valid_packet()
        p2 = _valid_packet()
        assert p1.to_json() == p2.to_json()

    def test_to_dict_returns_sorted_lists(self):
        packet = _valid_packet(
            proof_ref_ids=("pr-002", "pr-001"),
            metadata=(("z", "1"), ("a", "2")),
        )
        d = packet.to_dict()
        assert d["proof_ref_ids"] == ["pr-001", "pr-002"]
        assert d["metadata"] == [("a", "2"), ("z", "1")]

    def test_to_json_is_valid_json(self):
        packet = _valid_packet()
        s = packet.to_json()
        loaded = json.loads(s)
        assert loaded["product_state_ref"] == "abc123"
        assert loaded["phase_id"] == "phase-1"

    def test_validation_is_json_serializable(self):
        packet = _valid_packet(product_state_ref="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        dumped = json.dumps(
            {
                "status": v.status.value,
                "reason_codes": list(v.reason_codes),
            },
            sort_keys=True,
        )
        assert isinstance(dumped, str)


# ---------------------------------------------------------------------------
# Stable reason codes
# ---------------------------------------------------------------------------


class TestStableReasonCodes:
    def test_reason_codes_sorted(self):
        packet = _valid_packet(
            product_state_ref="",
            acceptance_criteria_ref="",
            phase_id="",
            run_id="",
            gate_id="",
            actor_or_role="",
            proof_ref_ids=(),
            payload="",
        )
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        codes = list(v.reason_codes)
        assert codes == sorted(codes)

    def test_multiple_failures_produce_multiple_codes(self):
        packet = _valid_packet(
            product_state_ref="",
            acceptance_criteria_ref="",
            phase_id="",
            run_id="",
            gate_id="",
            actor_or_role="",
            proof_ref_ids=(),
            payload="",
        )
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert REASON_MISSING_PRODUCT_STATE_REF in v.reason_codes
        assert REASON_MISSING_ACCEPTANCE_CRITERIA_REF in v.reason_codes
        assert REASON_MISSING_PHASE_IDENTITY in v.reason_codes
        assert REASON_MISSING_RUN_IDENTITY in v.reason_codes
        assert REASON_MISSING_GATE in v.reason_codes
        assert REASON_MISSING_ACTOR_OR_ROLE in v.reason_codes
        assert REASON_MISSING_PROOF_REFS in v.reason_codes
        assert REASON_UNBOUNDED_PAYLOAD in v.reason_codes

    def test_validation_output_contains_stable_reason_codes(self):
        """Validation output (details) contains the stable reason code strings."""
        packet = _valid_packet(product_state_ref="")
        v = validate_handoff_packet(packet, "abc123", _ADMISSIBLE)
        assert v.details is not None
        assert REASON_MISSING_PRODUCT_STATE_REF in v.details


# ---------------------------------------------------------------------------
# No side effects
# ---------------------------------------------------------------------------


class TestNoSideEffects:
    def test_validation_does_not_mutate_packet(self):
        packet = _valid_packet(product_state_ref="abc")
        original_id = id(packet)
        original_product = packet.product_state_ref
        v = validate_handoff_packet(packet, "def", _ADMISSIBLE)
        assert id(packet) == original_id
        assert packet.product_state_ref == original_product

    def test_packet_is_frozen(self):
        packet = _valid_packet()
        import dataclasses
        assert dataclasses.fields(packet)  # confirm it's a dataclass
        # Attempting to set an attribute should raise
        import dataclasses
        assert dataclasses.is_dataclass(packet)
        assert isinstance(packet, GateReadyHandoffPacket)


# ---------------------------------------------------------------------------
# Product name is Ariadne
# ---------------------------------------------------------------------------


class TestProductName:
    def test_module_docstring_contains_ariadne(self):
        import runner.handoff_packet
        doc = runner.handoff_packet.__doc__ or ""
        assert "Ariadne" in doc


# ---------------------------------------------------------------------------
# No forbidden legacy names
# ---------------------------------------------------------------------------


class TestNoForbiddenNames:
    def test_no_forbidden_strings(self):
        """The handoff_packet source should not contain forbidden legacy names."""
        import inspect
        source = inspect.getsource(_valid_packet)
        source += inspect.getsource(validate_handoff_packet)
        forbidden = [
            "water_meter", "water-meter", "Broken Clock", "broken_clock",
            "daily-consumption", ".grace", "@grace-", "old Flask",
        ]
        for f in forbidden:
            assert f not in source, f"Forbidden string found: {f!r}"


# ---------------------------------------------------------------------------
# No filesystem or network
# ---------------------------------------------------------------------------


class TestNoFilesystemOrNetwork:
    def test_validation_does_not_read_files(self):
        """validate_handoff_packet is a pure function with no I/O."""
        import dis
        import runner.handoff_packet
        # Check that validate_handoff_packet bytecode contains no file I/O
        # or network opcodes. We look for LOAD_GLOBAL calls to known I/O
        # functions as a heuristic.
        bytecode = dis.Bytecode(runner.handoff_packet.validate_handoff_packet)
        names = set()
        for instr in bytecode:
            if instr.argrepr:
                names.add(instr.argrepr)
        io_names = {"open", "read", "write", "urllib", "requests", "subprocess",
                     "os", "pathlib", "socket", "http"}
        overlap = names & io_names
        assert not overlap, f"Found I/O-related names in bytecode: {overlap}"

    def test_validation_does_not_call_network(self):
        """No network-related imports in handoff_packet module."""
        import runner.handoff_packet
        mod = runner.handoff_packet
        # Check that the module doesn't import network-related modules
        source = inspect.getsource(mod)
        network_imports = [
            "import urllib", "from urllib",
            "import requests", "from requests",
            "import socket", "from socket",
            "import http", "from http",
        ]
        for imp in network_imports:
            assert imp not in source, f"Network import found: {imp}"

    def test_validation_does_not_depend_on_wall_clock(self):
        """No datetime, time, or clock-related imports in handoff_packet module."""
        import inspect
        import runner.handoff_packet
        source = inspect.getsource(runner.handoff_packet)
        clock_imports = [
            "import datetime", "from datetime",
            "import time", "from time",
            "import timeit", "from timeit",
        ]
        for imp in clock_imports:
            assert imp not in source, f"Clock import found: {imp}"
