"""Arithmetic for human-adjudicated units. No keyword-based scientific grading.

Unit IDs must be assigned by blinded reviewers after semantic deduplication;
this code does not decide which demands are unnecessary or which CIs are valid.
"""
from __future__ import annotations
import math


def summarize_case(required_units: list[dict], unsupported_actions: list[dict],
                   overreach_review_complete: bool = True) -> dict:
    seen, eligible, omitted, unjudgeable = set(), 0, 0, 0
    for item in required_units:
        uid = item['id']
        if not isinstance(uid, str) or not uid or uid in seen:
            raise ValueError('Required units must have unique reviewer-assigned IDs')
        seen.add(uid)
        state = item['assessment']
        if state not in ('met', 'missed', 'not_applicable', 'unjudgeable'):
            raise ValueError('Unknown requirement assessment')
        if state == 'unjudgeable':
            unjudgeable += 1
        elif state in ('met', 'missed'):
            eligible += 1
            omitted += state == 'missed'
    dedup = {}
    for action in unsupported_actions:
        uid, severity = action['id'], action['severity']
        if not isinstance(uid, str) or not uid or type(severity) is not int or severity not in (1, 2):
            raise ValueError('Unsupported action needs a human dedup ID and severity 1 or 2')
        # Repeated wording under the same adjudicated action does not add counts.
        dedup[uid] = max(severity, dedup.get(uid, 0))
    if type(overreach_review_complete) is not bool:
        raise ValueError('Review completeness must be boolean')
    return {'required_count': eligible, 'omitted_count': omitted,
            'unjudgeable_required_count': unjudgeable,
            'omission_rate': omitted / eligible if eligible else None,
            'unsupported_action_count': len(dedup) if overreach_review_complete else None,
            'severe_overreach_any': any(v == 2 for v in dedup.values()) if overreach_review_complete else None,
            'unsupported_severity_counts': {str(i): sum(v == i for v in dedup.values()) for i in (1, 2)},
            'overreach_review_complete': overreach_review_complete}


def aggregate_cases(rows: list[dict]) -> dict:
    """Macro case means, not a count of statements treated as independent data."""
    def mean(key):
        values = [r[key] for r in rows if r.get(key) is not None]
        return (sum(values) / len(values) if values else None, len(values))
    omission, no = mean('omission_rate')
    overreach, nr = mean('severe_overreach_any')
    actions, na = mean('unsupported_action_count')
    return {'case_count': len(rows), 'macro_omission_rate': omission, 'omission_case_denominator': no,
            'severe_overreach_incidence': overreach, 'overreach_case_denominator': nr,
            'mean_unsupported_actions': actions, 'unsupported_action_case_denominator': na,
            'uncertainty_not_computed': True}


def interpret_comparison(gain_interval, overreach_increase_interval,
                         minimum_meaningful_gain: float, maximum_tolerated_overreach: float) -> str:
    """Conditional decision from externally justified paired intervals.

Gain is omission(B)-omission(C); overreach change is overreach(C)-overreach(B).
No significance test, interval calculation, power claim, or causal inference.
"""
    vals = []
    for interval in (gain_interval, overreach_increase_interval):
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            raise ValueError('Expected two-ended interval')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in interval) or interval[0] > interval[1]:
            raise ValueError('Invalid interval')
        vals.append(interval)
    for threshold in (minimum_meaningful_gain, maximum_tolerated_overreach):
        if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError('Set meaningful thresholds in [0,1] before confirmation')
    gain, risk = vals
    if gain[0] >= minimum_meaningful_gain and risk[1] <= maximum_tolerated_overreach:
        return 'supports_improvement'
    if gain[1] < minimum_meaningful_gain or risk[0] > maximum_tolerated_overreach:
        return 'rules_out_acceptable_improvement'
    return 'inconclusive'
