"""Optional final H2 generator using provided aggregate parameters; no LLM calls.

Reanalysis of stored results uses reproduce.py and does not run this generator.
"""
import argparse, copy, csv, gc, hashlib, json, random, sys
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--parameters',type=Path,required=True);a=p.parse_args()
 sys.path[:0]=[str(a.repo.resolve()/'Analysis'),str(a.repo.resolve()/'Simulation')]
 import h2_agent_heterogeneity as h2
 import psychological_state as ps
 params=json.loads(a.parameters.read_text(encoding='utf8'))['t1_parameters'];assert set(params)==set(h2.ACTIVE_CONSTRUCTS)
 output=a.output.resolve();output.mkdir(parents=True,exist_ok=False);data=output/'data';tables=output/'tables';data.mkdir();tables.mkdir()
 ref=copy.deepcopy(ps._LEGACY_PSYCHOLOGICAL_STATE_REFERENCE)
 for name,q in params.items():
  if name!='intrinsic_motivation':ref['constructs'][name]['norm_mean']=q['mean'];ref['constructs'][name]['norm_sd']=q['sd']
 ps._LEGACY_PSYCHOLOGICAL_STATE_REFERENCE=ref
 old_sampler=ps._sample_multivariate_normal
 def sampler(seed):
  values=old_sampler(seed);q=params['intrinsic_motivation'];s=hashlib.sha256(f'H2-intrinsic-v1:{seed}'.encode()).digest();z=random.Random(int.from_bytes(s,'big')).gauss(q['mean'],q['sd']);values['intrinsic_motivation']=max(0.,min(1.,z));return values
 ps._sample_multivariate_normal=sampler
 agents=h2.generate_agents(range(3263,3273),20);psych=h2.generate_psychological_constructs(agents);h2.write_csv(data/'initial_psychological_constructs.csv',psych)
 pairs=[];phases=[];counts=[];weekly=[]
 with (data/'agent_year_schedules_long.csv').open('x',encoding='utf8',newline='') as f:
  writer=None
  for seed in range(3263,3273):
   schedules=h2.generate_schedules([agent for agent in agents if agent.base_seed==seed])
   if writer is None:writer=csv.DictWriter(f,fieldnames=list(schedules[0]));writer.writeheader()
   writer.writerows(schedules);f.flush();pairs.extend(h2.pairwise_schedule_similarity(schedules));phase=h2.phase_sequence_rows(schedules);phases.extend(phase);counts.extend(h2.phase_week_counts(phase));_,weeks=h2.activity_hours(schedules);weekly.extend(weeks);del schedules;gc.collect()
 for name,rows in [('agent_phase_sequence.csv',phases),('agent_phase_week_counts.csv',counts),('pairwise_annual_schedule_similarity.csv',pairs)]:h2.write_csv(data/name,rows)
 overall,runs,across=h2.summarize_schedule_similarity(pairs,20);constructs,cruns,corr=h2.construct_summaries(psych);_,phase_activity=h2.phase_activity_summaries(weekly,counts)
 for name,rows in [('schedule_similarity_overall_summary.csv',overall),('schedule_similarity_run_summary.csv',runs),('schedule_similarity_across_run_means.csv',across),('construct_heterogeneity_summary.csv',constructs),('construct_run_summary.csv',cruns),('construct_correlation_matrix.csv',corr),('phase_week_count_summary.csv',h2.phase_count_summary(counts)),('phase_activity_summary.csv',phase_activity)]:h2.write_csv(tables/name,rows)
 print('Completed 200 agents, 10 base seeds, 52 weeks; no LLM calls')
if __name__=='__main__':main()
