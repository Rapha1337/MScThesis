"""Reproduce final H1-H3 statistics from reviewed analysis inputs; no simulation/LLM calls."""
from pathlib import Path
from itertools import combinations
import argparse, json, sys, math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import t, binomtest, friedmanchisquare

P=Path(__file__).resolve().parent.parent / 'data'
def same(a,b,what):
 try:pd.testing.assert_frame_equal(a.reset_index(drop=True),b.reset_index(drop=True),check_dtype=False,rtol=1e-8,atol=1e-8)
 except AssertionError as e:raise AssertionError(what+' differs: '+str(e)) from e
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(args.repo.resolve()/'Analysis'));import h1_weather_validation as h1
 # H2: reproduce the original 1,900 within-seed comparisons from full lossless compressed schedules.
 h2=pd.read_csv(P/'h2/data/initial_psychological_constructs.csv').sort_values(['base_seed','persona_index']);assert len(h2)==200 and (h2.groupby('base_seed').size()==20).all()
 grids={}; phases={}
 for chunk in pd.read_csv(P/'h2/data/agent_year_schedules_long.csv.gz',usecols=['unique_agent_id','year_hour','activity_type','week_index','phase'],chunksize=100000):
  for aid,g in chunk.groupby('unique_agent_id',sort=False):
   grids.setdefault(aid,[]).append(g[['year_hour','activity_type']]);
   for week,phase in g[['week_index','phase']].drop_duplicates().itertuples(index=False,name=None):
    key=(aid,week);assert key not in phases or phases[key]==phase;phases[key]=phase
 arrays={}
 for aid,parts in grids.items():
  g=pd.concat(parts).sort_values('year_hour');assert np.array_equal(g.year_hour.to_numpy(),np.arange(8736));arrays[aid]=g.activity_type.to_numpy()
 assert len(arrays)==200 and len(phases)==10400
 pairs=[]
 for seed,g in h2.groupby('base_seed'):
  for a,b in combinations(g.unique_agent_id,2):pairs.append((seed,a,b,int(np.count_nonzero(arrays[a]==arrays[b]))))
 saved=pd.read_csv(P/'h2/data/pairwise_annual_schedule_similarity.csv');assert len(pairs)==len(saved)==1900
 for (seed,a,b,n),r in zip(pairs,saved.itertuples(index=False)):assert (seed,a,b,n)==(r.base_seed,r.agent_a_id,r.agent_b_id,r.matching_slots)
 similarity=np.array([n/8736*100 for _,_,_,n in pairs]);s=pd.read_csv(P/'h2/tables/schedule_similarity_overall_summary.csv').iloc[0]
 for actual,key in [(similarity.mean(),'mean_similarity_percent'),(similarity.std(ddof=0),'sd_similarity_percent'),(similarity.min(),'min_similarity_percent'),(similarity.max(),'max_similarity_percent')]:assert abs(actual-s[key])<1e-10
 expected_phases=pd.read_csv(P/'h2/data/agent_phase_sequence.csv'); assert all(phases[(r.unique_agent_id,r.week_index)]==r.phase for r in expected_phases.itertuples())
 phasecounts=pd.DataFrame([{'unique_agent_id':a,'phase':phase,'n_weeks':sum(1 for (x,_),v in phases.items() if x==a and v==phase)} for a in arrays for phase in ('normal','high_stress','holiday')])
 prev=pd.read_csv(P/'h2/data/agent_phase_week_counts.csv'); same(phasecounts.sort_values(['unique_agent_id','phase']),prev[['unique_agent_id','phase','n_weeks']].sort_values(['unique_agent_id','phase']),'H2 phase counts')
 phase_summary=pd.read_csv(P/'h2/tables/phase_week_count_summary.csv').set_index('phase')
 for phase,g in phasecounts.groupby('phase'):
  for actual,key in [(g.n_weeks.mean(),'mean_weeks'),(g.n_weeks.std(ddof=0),'population_sd_weeks'),(g.n_weeks.min(),'minimum_weeks'),(g.n_weeks.max(),'maximum_weeks')]:assert abs(actual-phase_summary.loc[phase,key])<1e-10
 names=['action_planning','automaticity','pa_specific_self_control','attitude_toward_the_behavior','intention','perceived_behavioral_control','subjective_norm','motivational_competence','intrinsic_motivation']
 x=h2[names].to_numpy().reshape(10,20,9);rng=np.random.default_rng(3263);si=rng.integers(0,10,(5000,10));ai=rng.integers(0,20,(5000,10,20));bs=x[si[:,:,None],ai,:].reshape(5000,200,9).std(axis=1,ddof=0);lower,upper=np.percentile(bs,[2.5,97.5],axis=0);sd=x.reshape(200,9).std(axis=0,ddof=0)
 intervals=pd.read_csv(P/'h2/figure_5_intervals.csv').set_index('construct').loc[names]; assert np.allclose(intervals.population_sd,sd,atol=1e-9) and np.allclose(intervals.sd_ci_lower,lower,atol=1e-9) and np.allclose(intervals.sd_ci_upper,upper,atol=1e-9)
 summary=pd.read_csv(P/'h2/tables/construct_heterogeneity_summary.csv').set_index('construct').loc[names]
 for key,calculated in [('mean',x.reshape(200,9).mean(axis=0)),('population_sd',sd),('minimum',x.reshape(200,9).min(axis=0)),('maximum',x.reshape(200,9).max(axis=0))]:assert np.allclose(summary[key],calculated,atol=1e-9)
 # Figure 5 preserves the original Matplotlib H2 visual settings and fixed construct order.
 labels=['Action\nplanning','Automaticity','PA-specific\nself-control','Attitude\ntoward the\nbehavior','Intention','Perceived\nbehavioral\ncontrol','Subjective\nnorm','Motivational\ncompetence','Intrinsic\nmotivation']
 fig,ax=plt.subplots(figsize=(12,5.4));ax.bar(np.arange(9),sd,yerr=np.vstack([sd-lower,upper-sd]),capsize=3);ax.set_xticks(np.arange(9),labels,fontsize=12);ax.set_xlabel('Construct',fontsize=14);ax.set_ylabel('SD',fontsize=14);ax.set_ylim(0,1);ax.set_yticks(np.arange(0,1.01,.2));ax.tick_params(axis='y',labelsize=12);ax.grid(axis='y',alpha=.25);ax.set_axisbelow(True);fig.tight_layout()
 for ext in ('png','svg'):fig.savefig(out/f'figure_5.{ext}',dpi=300,bbox_inches='tight')
 plt.close(fig)
 print('PASS H2 200 agents, schedules, 1900 pairs, phases, bootstrap and Figure 5')
if __name__ == '__main__': main()
