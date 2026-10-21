"""UI-independent screening, visit planning and briefing preparation."""
from dataclasses import dataclass, asdict
from html import escape
import json
import math


@dataclass(frozen=True)
class Scenario:
    budget: int = 5000000
    cost_per_visit: int = 100000
    max_visits: int = 20

    def __post_init__(self):
        if self.budget < 0 or self.cost_per_visit <= 0 or self.max_visits < 0:
            raise ValueError('Use non-negative budget and visit limit, and positive cost.')


def screen(evidence):
    df = evidence.copy()
    measured = (df.tiles_count > 0) & df.mean_u_mbps.notna() & df.mean_lat_ms.notna()
    upload = ((2.5 - df.mean_u_mbps) / 2.5).clip(0, 1)
    latency = ((df.mean_lat_ms - 50) / 200).clip(0, 1)
    df['screening_score'] = ((upload * .7 + latency * .3) * 100).round(1).where(measured)
    df['evidence_status'] = 'Insufficient evidence'
    df.loc[measured, 'evidence_status'] = 'Lower observed concern'
    df.loc[measured & (df.screening_score >= 35), 'evidence_status'] = 'Review performance'
    df.loc[measured & (df.screening_score >= 65), 'evidence_status'] = 'Poor observed performance'
    df['sample_strength'] = 'No usable observations'
    df.loc[measured, 'sample_strength'] = 'Limited sample'
    df.loc[measured & (df.tiles_count >= 10) & (df.total_tests >= 30), 'sample_strength'] = 'Larger sample; freshness unverified'
    df['verification_priority'] = df.screening_score.fillna(75)
    df['next_action'] = 'Check current performance at actual operational sites'
    df.loc[~measured, 'next_action'] = 'Collect a first connectivity observation'
    df.loc[measured & (df.screening_score >= 65), 'next_action'] = 'Verify current conditions and assess backup options'
    return df.sort_values(['verification_priority', 'shapeID'], ascending=[False, True]).reset_index(drop=True)


def allocate_visits(evidence, scenario):
    ranked = screen(evidence).drop_duplicates('shapeID')
    count = min(len(ranked), scenario.max_visits, scenario.budget // scenario.cost_per_visit)
    chosen = ranked.head(count).copy()
    chosen['estimated_cost_ngn'] = scenario.cost_per_visit
    return chosen, {'selected': count, 'remaining_lgas': len(ranked)-count, 'estimated_spend': count*scenario.cost_per_visit, 'unspent': scenario.budget-count*scenario.cost_per_visit}


def rehearsal_action(completed, seconds):
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Elapsed time must be positive and finite.')
    return 'Check backup options' if not completed or seconds > 60 else 'Repeat at another time and on another carrier'


def briefing(evidence, selected, scenario, summary, observations=None):
    table = selected[['shapeName', 'shapeID', 'evidence_status', 'next_action', 'estimated_cost_ngn']].to_html(index=False, escape=True)
    assumptions = escape(json.dumps(asdict(scenario), indent=2))
    notes = escape(json.dumps(observations or [], indent=2, default=str))
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>SENTINEL decision brief</title>
    <style>body{{font:15px Arial;max-width:1000px;margin:40px auto;color:#172638}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{border:1px solid #bbc5cf;padding:8px;text-align:left}}pre{{white-space:pre-wrap}}@media print{{body{{margin:0}}tr{{break-inside:avoid}}}}</style>
    <h1>SENTINEL · Verification decision brief</h1><p>Planning prototype. No operational or INEC certification.</p>
    <p>{len(evidence)} LGAs in scope; {summary['selected']} proposed visits; estimated spend ₦{summary['estimated_spend']:,}; {summary['remaining_lgas']} LGAs outside this shortlist.</p>
    <h2>Proposed verification visits</h2>{table}<h2>Scenario assumptions</h2><pre>{assumptions}</pre>
    <p>Equal-cost visits ranked by screening priority. Unknown evidence gets verification priority 75, not a risk score. Screening score: 70% upload deficit against 2.5 Mbps, 30% latency deficit from 50 to 250 ms. Thresholds are illustrative, not validated BVAS requirements.</p>
    <h2>Sources and limitations</h2><p>Local Ookla extract; geoBoundaries LGA boundaries; GRID3 health and HOT OSM education records. Observation period and network type unverified. Unweighted tile averages are not nationwide coverage. Schools are not verified polling units. Distance is from an LGA interior point to a historically observed tile, not road access or a verified upload facility. Costs are user assumptions. No connectivity improvement is predicted.</p>
    <h2>Synthetic rehearsal notes</h2><pre>{notes}</pre><p>Assign a reviewer, verify actual operational sites and costs, and approve any deployment separately.</p></html>'''
