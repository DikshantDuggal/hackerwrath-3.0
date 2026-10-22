"""The policy decides every level. These pin down what plug-in output can and can't do."""

from __future__ import annotations

from detection.policy import DEGRADED, KEEP, Decision, OpenAlert, decide
from detection.schemas import Assessment

TURNS = {"turn_1", "turn_2"}
ALL_SIGNALS = (
    "otp_or_pin_request",
    "remote_access",
    "financial_solicitation",
    "authority_impersonation",
    "coercive_threat",
    "account_suspension_threat",
)


def judge(assessment, *, failed=False, open_alert=None, role_context=None, turns=TURNS):
    return decide(assessment, failed=failed, open_alert=open_alert, role_context=role_context, known_turn_ids=turns)


def ask(request_type="otp_share", confidence="high", evidence=("turn_2",), **kw) -> Assessment:
    return Assessment(request_type=request_type, confidence=confidence, evidence_turn_ids=evidence, **kw)


def test_failed_detector_output_reports_degraded_and_raises_nothing():
    assert judge(None, failed=True) == DEGRADED


def test_no_assessment_keeps_things_as_they_are():
    assert judge(None) == KEEP


def test_an_otp_request_with_high_confidence_and_cited_evidence_is_high_risk():
    assert judge(ask()) == Decision("confirm", "otp_share", "high")


def test_a_remote_access_request_with_cited_evidence_is_high_risk():
    assert judge(ask("remote_access")).level == "high"


def test_uncited_evidence_stays_possible_risk():
    assert judge(ask(evidence=())).level == "possible"


def test_evidence_citing_a_turn_that_was_never_heard_stays_possible_risk():
    assert judge(ask(evidence=("turn_99",))).level == "possible"


def test_setup_only_stays_possible_risk():
    assert judge(ask(setup_only=True)).level == "possible"


def test_a_request_the_caller_is_only_reporting_stays_possible_risk():
    assert judge(ask(requester_is_speaker=False)).level == "possible"


def test_scan_to_receive_is_possible_risk_unless_the_user_expects_a_payment():
    assert judge(ask("qr_receive")).level == "possible"
    assert judge(ask("qr_receive"), role_context="expecting_payment").level == "high"


def test_low_confidence_keeps_things_as_they_are():
    assert judge(ask(confidence="low")) == KEEP


def test_a_harmless_reading_clears_a_possible_warning_but_never_a_high_one():
    harmless = Assessment(request_type="none", confidence="high")
    possible = OpenAlert("al_1", "qr_receive", "possible", confirmed=False)
    high = OpenAlert("al_1", "otp_share", "high", confirmed=True)
    assert judge(harmless, open_alert=possible) == Decision("clear")
    assert judge(harmless, open_alert=high) == KEEP


def test_a_weaker_later_reading_never_takes_high_risk_down():
    high = OpenAlert("al_1", "otp_share", "high", confirmed=True)
    assert judge(ask(confidence="medium"), open_alert=high) == KEEP


def test_signals_never_change_the_level():
    assert judge(ask(confidence="medium", signals=ALL_SIGNALS)).level == "possible"
    assert judge(ask(signals=ALL_SIGNALS)).level == "high"


def test_signals_pass_through_once_each_in_order():
    decision = judge(ask(signals=("authority_impersonation", "otp_or_pin_request", "authority_impersonation")))
    assert decision.signals == ("authority_impersonation", "otp_or_pin_request")
