"""FRC System — Policy Engine"""
import logging
from typing import Any, Dict, List, Optional
from backend.core.database import policy_rules_col
from backend.models.common import PolicyRuleType, SubmissionType
from backend.models.policy import PolicyEvaluationResult

log = logging.getLogger(__name__)

STATIC_FX_RATES = {"USD": 1.0, "MUR": 0.022, "EUR": 1.08, "GBP": 1.27, "ZAR": 0.054, "KES": 0.0078}

def to_usd(amount: float, currency: str) -> float:
    return amount * STATIC_FX_RATES.get(currency.upper(), 1.0)

def _eval_threshold_amount(c, tx):
    min_usd = float(c.get("min_amount_usd", 15000))
    amount = float(tx.get("amount", 0)); currency = str(tx.get("currency", "USD")).upper()
    usd = float(tx.get("amount_usd_equivalent") or to_usd(amount, currency))
    return usd >= min_usd

def _eval_cross_border(c, tx):
    if not tx.get("is_cross_border", False): return False
    min_usd = float(c.get("min_amount_usd", 10000))
    amount = float(tx.get("amount", 0)); currency = str(tx.get("currency", "USD")).upper()
    usd = float(tx.get("amount_usd_equivalent") or to_usd(amount, currency))
    return usd >= min_usd

def _eval_ml_score(c, tx):
    min_score = float(c.get("min_score", 0.70)); ml = tx.get("ml_score")
    return ml is not None and float(ml) >= min_score

def _eval_transaction_type(c, tx):
    types = [t.upper() for t in c.get("types", [])]; tx_type = str(tx.get("transaction_type", "")).upper()
    return tx_type in types

def _eval_geographic(c, tx):
    countries = [c2.upper() for c2 in c.get("countries", [])]
    return str(tx.get("origin_country","")).upper() in countries or str(tx.get("destination_country","")).upper() in countries

EVALUATORS = {
    PolicyRuleType.THRESHOLD_AMOUNT: _eval_threshold_amount,
    PolicyRuleType.CROSS_BORDER: _eval_cross_border,
    PolicyRuleType.ML_SCORE: _eval_ml_score,
    PolicyRuleType.TRANSACTION_TYPE: _eval_transaction_type,
    PolicyRuleType.GEOGRAPHIC: _eval_geographic,
}

async def evaluate_transaction(tx: dict) -> PolicyEvaluationResult:
    try:
        cursor = policy_rules_col().find({"is_active": True}).sort("priority", 1)
        active_rules = await cursor.to_list(length=None)
    except Exception as e:
        log.error(f"Failed to load policy rules: {e}")
        return PolicyEvaluationResult(triggered=False, matched_rules=[], reason="Policy engine error")

    matched_rules: List[str] = []
    regulatory_triggered = False; sar_triggered = False

    for rule in active_rules:
        rule_code = rule.get("rule_code", ""); rule_type_str = rule.get("rule_type", "")
        submission_type_str = rule.get("submission_type", ""); conditions = rule.get("conditions", {})
        try:
            rule_type = PolicyRuleType(rule_type_str)
        except ValueError:
            continue
        evaluator = EVALUATORS.get(rule_type)
        if not evaluator: continue
        try:
            matched = evaluator(conditions, tx)
        except Exception as e:
            log.warning(f"Rule '{rule_code}' eval failed: {e}"); continue
        if matched:
            matched_rules.append(rule_code)
            if submission_type_str == SubmissionType.REGULATORY_REPORT.value: regulatory_triggered = True
            elif submission_type_str == SubmissionType.SUSPICIOUS_ACTIVITY_REPORT.value: sar_triggered = True

    if not matched_rules:
        return PolicyEvaluationResult(triggered=False, matched_rules=[], reason="No rules matched")

    submission_type = SubmissionType.REGULATORY_REPORT if regulatory_triggered else SubmissionType.SUSPICIOUS_ACTIVITY_REPORT
    return PolicyEvaluationResult(
        triggered=True, matched_rules=matched_rules, submission_type=submission_type,
        highest_priority_rule=matched_rules[0],
        reason=f"{len(matched_rules)} rule(s) matched. Type: {submission_type.value}"
    )
