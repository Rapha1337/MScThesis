"""Check public synthetic weather aggregation without reference data or simulation."""
import argparse,sys
from pathlib import Path
import pandas as pd
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();repo=a.repo.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(repo/'Analysis'));import h1_weather_validation as h1
 daily=pd.read_csv(repo/'data/h1/simulated_daily_weather.csv');assert len(daily)==10800 and daily.seed.nunique()==30
 monthly=h1.aggregate_monthly(daily);expected=pd.read_csv(repo/'data/h1/simulated_monthly_weather.csv')
 pd.testing.assert_frame_equal(monthly.reset_index(drop=True),expected.reset_index(drop=True),check_dtype=False,rtol=1e-8,atol=1e-8)
 annual=h1.annual_summary(monthly); expected_annual=pd.read_csv(repo/'data/h1/h1_annual_summary.csv')
 pd.testing.assert_frame_equal(annual.reset_index(drop=True),expected_annual.reset_index(drop=True),check_dtype=False,rtol=1e-8,atol=1e-8)
 monthly.to_csv(out/'h1_monthly.csv',index=False);annual.to_csv(out/'h1_annual_summary.csv',index=False)
 print('PASS 30 simulated weather years: monthly and annual aggregation; reference comparisons not tested')
if __name__=='__main__':main()
