"""Controlled synthetic diagnostic of the current adapter, not empirical fitting."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from population_simu.benchmarks import fixed_trend_runner, household_simulator_runner
from population_simu.household_calibration import HouseholdCalibration


def diagnose():
    # Lock the design before inspecting outputs. No historical test outcomes used.
    calibration = HouseholdCalibration(housing_elasticity=-1.0)
    records = []
    for seed in range(20):
        for burden in (0.2, 0.35, 0.5):
            train = [dict(entity='synthetic', year=y, asfr_15_44=g,
                          births_15_44=g * 100, female_15_44=100000,
                          housing_cost_burden=burden)
                     for y, g in ((2016, 62.0), (2017, 60.0))]
            output = household_simulator_runner(calibration=calibration)(train, [2018, 2019], seed)
            raw1, raw2 = (r['world_asfr_unscaled'] for r in output)
            expected1 = 60.0 if raw1 > 1e-9 else raw1
            expected2 = 60.0 * raw2 / raw1 if raw1 > 1e-9 else raw2
            trend = fixed_trend_runner('asfr_15_44')(train, [2018, 2019], seed)
            ablated = household_simulator_runner(use_household_mechanisms=False)(train, [2018, 2019], seed)
            # Change named priors alone to check whether this adapter consumes them.
            other = replace(calibration, age_profile=(0.1,) * 7,
                            parity_progression=(0.1, 0.1, 0.1))
            altered = household_simulator_runner(calibration=other)(train, [2018, 2019], seed)
            records.append(dict(seed=seed, burden=burden, raw_first=raw1,
                                raw_second=raw2, scaled_first=output[0]['asfr_scaled'],
                                scaled_second=output[1]['asfr_scaled'],
                                first_identity_error=abs(output[0]['asfr_scaled']-expected1),
                                second_identity_error=abs(output[1]['asfr_scaled']-expected2),
                                no_household_equals_trend=ablated == trend,
                                named_prior_change_equals_original=altered == output))
    paired = []
    for seed in range(20):
        low = next(r for r in records if r['seed']==seed and r['burden']==0.2)
        high = next(r for r in records if r['seed']==seed and r['burden']==0.5)
        paired.append(dict(seed=seed, raw_first_delta=high['raw_first']-low['raw_first'],
                           scaled_first_delta=high['scaled_first']-low['scaled_first']))
    return dict(
        kind='synthetic_adapter_normalization_diagnostic',
        design=dict(seeds=list(range(20)), burdens=[0.2,0.35,0.5],
                    training_gfr=[62,60], targets=[2018,2019],
                    housing_elasticity=-1.0, initial_people=1200,
                    residual_noise=False, future_housing=None,
                    prior_perturbation='age_profile and parity_progression jointly'),
        source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
                       for name in ['scripts/diagnose_adapter_normalization.py',
                                    'src/population_simu/benchmarks.py',
                                    'src/population_simu/world.py',
                                    'src/population_simu/household_calibration.py']},
        records=records, paired_housing_differences=paired,
        summary=dict(runs=len(records), zero_first_birth_runs=sum(r['raw_first']==0 for r in records),
                     max_first_identity_error=max(r['first_identity_error'] for r in records),
                     max_second_identity_error=max(r['second_identity_error'] for r in records),
                     all_no_household_equals_trend=all(r['no_household_equals_trend'] for r in records),
                     all_named_prior_changes_equal=all(r['named_prior_change_equals_original'] for r in records),
                     raw_housing_response_seed_count=sum(abs(r['raw_first_delta'])>1e-9 for r in paired),
                     mean_paired_raw_first_delta=statistics.mean(r['raw_first_delta'] for r in paired),
                     max_abs_scaled_first_delta=max(abs(r['scaled_first_delta']) for r in paired)),
        limits=['synthetic inputs, not real housing effects',
                'housing changes both multiplier and childcare support',
                'same seed does not guarantee event-aligned random draws after trajectories diverge',
                'does not estimate how much historical error comes from normalization',
                'raw rate denominator is initial population times 0.5, not measured female exposure'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = diagnose()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result['summary'], indent=2))
    assert result['summary']['max_first_identity_error'] < 1e-9
    assert result['summary']['max_second_identity_error'] < 1e-9
    assert result['summary']['all_no_household_equals_trend']
