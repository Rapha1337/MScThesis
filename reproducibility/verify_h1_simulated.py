"""Reproduce H1 from stored simulation output and the provided reference; no simulation."""
import argparse
import sys
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repo / 'Analysis'))
    import h1_weather_validation as h1

    daily = pd.read_csv(repo / 'data/h1/simulated_daily_weather.csv')
    assert len(daily) == 10800 and daily.seed.nunique() == 30
    monthly = h1.aggregate_monthly(daily)
    expected_monthly = pd.read_csv(repo / 'data/h1/simulated_monthly_weather.csv')
    pd.testing.assert_frame_equal(monthly, expected_monthly, check_dtype=False, rtol=1e-8, atol=1e-8)
    annual = h1.annual_summary(monthly)
    expected_annual = pd.read_csv(repo / 'data/h1/h1_annual_summary.csv')
    pd.testing.assert_frame_equal(annual, expected_annual, check_dtype=False, rtol=1e-8, atol=1e-8)
    reference = h1.load_reference(repo / 'data/h1/zollikofen_climate_normals_1991_2020.csv')
    comparison = h1.monthly_comparison(monthly, reference)
    summary = h1.summary_metrics(comparison)
    quantiles = h1.precip_quantile_comparison(monthly, reference)
    coverage = comparison.groupby('variable', sort=True).agg(
        months_inside_95_interval=('reference_inside_95_interval', 'sum'),
        n_months=('month', 'count'),
    ).reset_index()
    coverage['coverage_fraction'] = coverage.months_inside_95_interval / coverage.n_months
    results = {'monthly_climate_comparison.csv': comparison, 'h1_summary_metrics.csv': summary,
               'precipitation_quantile_comparison.csv': quantiles, 'h1_interval_coverage.csv': coverage}
    for name, frame in results.items():
        expected_path = repo / 'data/h1/results' / name
        if expected_path.exists():
            pd.testing.assert_frame_equal(frame, pd.read_csv(expected_path), check_dtype=False, rtol=1e-8, atol=1e-8)
        frame.to_csv(out / name, index=False)
    monthly.to_csv(out / 'h1_monthly.csv', index=False)
    annual.to_csv(out / 'h1_annual_summary.csv', index=False)
    figures = out / 'figures'
    figures.mkdir()
    h1.make_figures(comparison, quantiles, figures)
    print('PASS H1: 30 saved years, reference comparisons, quantiles, coverage, summaries and five figures')


if __name__ == '__main__':
    main()
