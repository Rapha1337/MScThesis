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

P=Path(__file__).resolve().parent
def same(a,b,what):
 try:pd.testing.assert_frame_equal(a.reset_index(drop=True),b.reset_index(drop=True),check_dtype=False,rtol=1e-8,atol=1e-8)
 except AssertionError as e:raise AssertionError(what+' differs: '+str(e)) from e
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--data-dir',type=Path,required=True);args=parser.parse_args();global P;P=args.data_dir.resolve()
 out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(args.repo.resolve()/'Analysis'));import h1_weather_validation as h1
 # H1: daily observations reproduce all monthly and comparison tables, no weather simulation.
 d=pd.read_csv(P/'h1/data/simulated_daily_weather.csv'); assert len(d)==30*360 and d.seed.nunique()==30
 monthly=h1.aggregate_monthly(d); prior=pd.read_csv(P/'h1/data/simulated_monthly_weather.csv'); same(monthly,prior,'H1 monthly')
 ref=h1.load_reference(args.repo.resolve()/'data/h1/zollikofen_climate_normals_1991_2020.csv'); comp=h1.monthly_comparison(monthly,ref)
 same(comp,pd.read_csv(P/'h1/data/monthly_climate_comparison.csv'),'H1 comparison')
 same(h1.summary_metrics(comp),pd.read_csv(P/'h1/tables/h1_summary_metrics.csv'),'H1 summary')
 coverage=comp.groupby('variable',sort=True).agg(months_inside_95_interval=('reference_inside_95_interval','sum'),n_months=('month','count')).reset_index();coverage['coverage_fraction']=coverage.months_inside_95_interval/coverage.n_months
 same(coverage,pd.read_csv(P/'h1/tables/h1_interval_coverage.csv'),'H1 coverage')
 precip=h1.precip_quantile_comparison(monthly,ref);same(precip,pd.read_csv(P/'h1/data/precipitation_quantile_comparison.csv'),'H1 precipitation quantiles')
 same(h1.annual_summary(monthly),pd.read_csv(P/'h1/tables/h1_annual_summary.csv'),'H1 annual summary')
 h1_figures=out/'h1_figures';h1_figures.mkdir();h1.make_figures(comp,precip,h1_figures)
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
 # H3: fixed 6 x 4 x 2 aggregate counts; no pseudoreplication or individual day records.
 h=pd.read_csv(P/'h3/medoid_run_context_counts.csv'); assert len(h)==48 and h.simulated_days.sum()==2160 and not h.duplicated(['run','medoid','context']).any()
 assert set(h.context)=={'supportive','hindering'} and (h.simulated_days==h.eligible_days).all()
 totals=h.groupby('context')[['pa_days','eligible_days']].sum()
 runs=h.groupby(['run','context'])[['pa_days','eligible_days']].sum();rate=(runs.pa_days/runs.eligible_days).unstack();delta=rate.supportive-rate.hindering
 reference_runs=pd.read_csv(P/'h3/reference_replication_contrasts.csv').set_index('replication').sort_index();assert np.allclose(delta,reference_runs.pooled_difference,atol=1e-12)
 for label in ('supportive','hindering'):
  assert np.array_equal(runs.loc[(slice(None),label),'pa_days'].to_numpy(),reference_runs[label+'_pa_days'].to_numpy())
  assert np.array_equal(runs.loc[(slice(None),label),'eligible_days'].to_numpy(),reference_runs[label+'_denominator'].to_numpy())
 stats={'pooled_difference':totals.loc['supportive','pa_days']/totals.loc['supportive','eligible_days']-totals.loc['hindering','pa_days']/totals.loc['hindering','eligible_days'],'mean':delta.mean(),'sample_sd':delta.std(ddof=1),'min':delta.min(),'max':delta.max()};mo=t.ppf(.975,5)*stats['sample_sd']/math.sqrt(6);stats.update(ci_low=stats['mean']-mo,ci_high=stats['mean']+mo,p_sign=binomtest(int((delta>0).sum()),int((delta!=0).sum()),.5,alternative='greater').pvalue)
 a=h.groupby(['run','medoid'])[['pa_days','eligible_days']].sum();r=(a.pa_days/a.eligible_days).unstack().loc[:,['C1','C2','C3','C4']]; fr=friedmanchisquare(*(r[c] for c in r.columns));stats.update(friedman_chi2=fr.statistic,friedman_p=fr.pvalue,kendall_w=fr.statistic/18)
 expected=json.loads((P/'h3/reference_statistics.json').read_text(encoding='utf8'));assert all(np.isclose(stats[k],expected[k],rtol=1e-10,atol=1e-10) for k in ('mean','sample_sd','ci_low','ci_high','p_sign','friedman_chi2','kendall_w'))
 med=h.groupby('medoid')[['pa_days','eligible_days']].sum();assert len(med)==4 and (med.eligible_days==540).all()
 overall=pd.read_csv(P/'h3/medoid_run_overall.csv').set_index(['replication','medoid']).sort_index();assert np.array_equal(a.pa_days,overall.overall_pa_days) and np.array_equal(a.eligible_days,overall.overall_pa_denominator)
 fig,ax=plt.subplots(figsize=(9,5.4));ax.scatter(delta.index,delta*100,color='#1f77b4',s=50,zorder=3);ax.axhline(stats['mean']*100,color='#1f77b4',linestyle='--',label='Mean');ax.axhspan(stats['ci_low']*100,stats['ci_high']*100,color='#1f77b4',alpha=.15,label='95% CI');ax.axhline(0,color='black',linewidth=.8);ax.set_xticks(range(1,7));ax.set_xlabel('Simulation run',fontsize=13);ax.set_ylabel('Difference in PA-frequency (%)',fontsize=13);ax.tick_params(labelsize=12);ax.grid(axis='y',alpha=.25);ax.set_axisbelow(True);ax.legend(frameon=False,fontsize=10);fig.tight_layout()
 for ext in ('png','svg'):fig.savefig(out/f'figure_6.{ext}',dpi=300,bbox_inches='tight')
 plt.close(fig)
 fig,ax=plt.subplots(figsize=(9,5.4));bars=ax.bar(med.index,100*med.pa_days/med.eligible_days,color='#1f77b4',width=.65);ax.bar_label(bars,labels=[f'{x:.1f}%' for x in 100*med.pa_days/med.eligible_days],padding=4,fontsize=12);ax.set_xlabel('Medoid persona',fontsize=13);ax.set_ylabel('Total PA-frequency across runs (%)',fontsize=13);ax.set_ylim(0,100);ax.set_yticks(np.arange(0,101,20));ax.tick_params(labelsize=12);ax.grid(axis='y',alpha=.25);ax.set_axisbelow(True);ax.plot([0,0,3,3],[78,81,81,78],color='black',linewidth=1.2);ax.text(1.5,82,'**',ha='center',va='bottom',fontsize=12);fig.tight_layout()
 for ext in ('png','svg'):fig.savefig(out/f'figure_7.{ext}',dpi=300,bbox_inches='tight')
 plt.close(fig)
 (out/'statistics.json').write_text(json.dumps(stats,indent=2)+'\n',encoding='utf8')
 print('PASS H1 monthly/reference/summary, H2 1900 pairs/phases/bootstrap, H3 context/sign/Friedman; figures 5–7 generated')
if __name__=='__main__':main()
