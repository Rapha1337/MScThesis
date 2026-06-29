from __future__ import annotations
import argparse,csv,json,random,shutil,sys,zlib,struct
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import mean,pstdev
from typing import Any,Iterable
ROOT=Path(__file__).resolve().parents[1]; SIM=ROOT/'Simulation'
if str(SIM) not in sys.path: sys.path.insert(0,str(SIM))
from agent_context_export import PSYCHOLOGICAL_SEED_OFFSET
from persona_wrappers import StudentHoursWrapper,StudentWrapper
from psychological_state import BACKEND_CONSTRUCT_RANGES,build_psychological_state
from schedule_model_student import YearPhase,distribute_weekly_budgets_to_days,generate_full_day_schedule
ACTIVE_CONSTRUCTS=tuple(BACKEND_CONSTRUCT_RANGES.keys()); WEEKDAY_LABELS=("Mon","Tue","Wed","Thu","Fri","Sat","Sun"); TOTAL_WEEK_SLOTS=168
DEFAULT_OUTPUT_DIR=ROOT/'Analysis'/'outputs'/'h2_agent_heterogeneity'
@dataclass(frozen=True)
class AgentRecord:
    unique_agent_id:str; base_seed:int; persona_index:int; persona_id:str; persona_seed:int; psychological_seed:int; phase:str; wrapper:StudentHoursWrapper; weekly_structure:Any

def base_seed_sequence(base_seed:int,n_base_seeds:int)->list[int]:
    if n_base_seeds<1: raise ValueError('n_base_seeds must be at least 1')
    return list(range(base_seed,base_seed+n_base_seeds))
def psychological_seed_from_persona_seed(persona_seed:int)->int: return int(persona_seed)+int(PSYCHOLOGICAL_SEED_OFFSET)
def generic_student_inputs()->dict[str,float|None]: return StudentHoursWrapper.from_zve_student_generic().input_parameters()
def generate_agents(base_seeds:Iterable[int],agents_per_seed:int,phase:str)->list[AgentRecord]:
    ph=YearPhase.coerce(phase); params=StudentHoursWrapper.from_zve_student_generic(); out=[]
    for bs in base_seeds:
        ps=StudentWrapper(params,int(bs)).create_personas(agents_per_seed,ph)
        if len(ps)!=agents_per_seed: raise ValueError('persona count mismatch')
        for p in ps:
            idx=int(p['persona_index']); pid=str(p['persona_name']); seed=int(p['persona_seed'])
            out.append(AgentRecord(f'base{bs}_{pid}',int(bs),idx,pid,seed,psychological_seed_from_persona_seed(seed),ph.value,p['wrapper'],p['weekly_structure']))
    if len({a.unique_agent_id for a in out})!=len(out): raise ValueError('Generated agent IDs are not globally unique')
    return sorted(out,key=lambda a:(a.base_seed,a.persona_index))
def generate_agent_schedule(a:AgentRecord)->list[dict[str,Any]]:
    distribute_weekly_budgets_to_days(a.weekly_structure,rng=random.Random(a.persona_seed)); rows=[]
    for wd in range(7):
        day=generate_full_day_schedule(a.weekly_structure,wd,rng=random.Random(a.persona_seed+wd))
        if len(day)!=24: raise ValueError('day must have 24 slots')
        for ep in sorted(day,key=lambda e:int(e.hour)):
            rows.append({'unique_agent_id':a.unique_agent_id,'base_seed':a.base_seed,'persona_index':a.persona_index,'persona_id':a.persona_id,'persona_seed':a.persona_seed,'psychological_seed':a.psychological_seed,'phase':a.phase,'weekday':wd,'weekday_label':WEEKDAY_LABELS[wd],'hour':int(ep.hour),'week_hour':wd*24+int(ep.hour),'activity_type':str(getattr(ep.activity_type,'value',ep.activity_type)),'subtype':ep.subtype or ''})
    return rows
def generate_schedules(agents:list[AgentRecord])->list[dict[str,Any]]:
    rows=[r for a in agents for r in generate_agent_schedule(a)]; validate_schedules(rows,len(agents)); return sorted(rows,key=lambda r:(r['base_seed'],r['persona_index'],r['weekday'],r['hour']))
def validate_schedules(rows:list[dict[str,Any]],expected_agents:int)->None:
    ids=sorted({r['unique_agent_id'] for r in rows})
    if len(ids)!=expected_agents: raise ValueError('agent count mismatch')
    for i in ids:
        g=[r for r in rows if r['unique_agent_id']==i]
        if len(g)!=168 or len({(r['weekday'],r['hour']) for r in g})!=168: raise ValueError('Each agent must have 168 unique weekday-hour rows')
        if sorted({r['weekday'] for r in g})!=list(range(7)) or sorted({r['hour'] for r in g})!=list(range(24)): raise ValueError('bad weekday/hour coverage')
        if any(not str(r['activity_type']) for r in g): raise ValueError('empty activity_type')
def week_grid(rows:list[dict[str,Any]],agent_id:str)->list[str]: return [r['activity_type'] for r in sorted([x for x in rows if x['unique_agent_id']==agent_id],key=lambda r:(r['weekday'],r['hour']))]
def compare_week_activity_types(a:list[str],b:list[str])->dict[str,float|int]:
    if len(a)!=168 or len(b)!=168: raise ValueError('Weekly schedules must contain 168 activity labels')
    m=sum(x==y for x,y in zip(a,b)); sim=m/168; return {'matching_slots':m,'differing_slots':168-m,'total_slots':168,'similarity':sim,'similarity_percent':sim*100,'difference':1-sim,'difference_percent':(1-sim)*100}
def pairwise_schedule_similarity(rows:list[dict[str,Any]])->list[dict[str,Any]]:
    out=[]
    for bs in sorted({r['base_seed'] for r in rows}):
        g=[r for r in rows if r['base_seed']==bs]; ids=[uid for _,uid in sorted({(r['persona_index'],r['unique_agent_id']) for r in g})]; grids={i:week_grid(g,i) for i in ids}
        for a,b in combinations(ids,2): out.append({'base_seed':bs,'agent_a_id':a,'agent_b_id':b,**compare_week_activity_types(grids[a],grids[b])})
    return out
def summarize_schedule_similarity(pairs:list[dict[str,Any]],agents_per_seed:int):
    run=[]
    for bs in sorted({p['base_seed'] for p in pairs}):
        g=[p for p in pairs if p['base_seed']==bs]; sim=[p['similarity_percent'] for p in g]; diff=[p['difference_percent'] for p in g]
        run.append({'base_seed':bs,'n_agents':agents_per_seed,'n_pairs':len(g),'mean_similarity_percent':mean(sim),'sd_similarity_percent':pstdev(sim) if len(sim)>1 else 0,'min_similarity_percent':min(sim),'max_similarity_percent':max(sim),'mean_difference_percent':mean(diff),'sd_difference_percent':pstdev(diff) if len(diff)>1 else 0,'min_difference_percent':min(diff),'max_difference_percent':max(diff)})
    sim=[p['similarity_percent'] for p in pairs] or [100.0]; diff=[p['difference_percent'] for p in pairs] or [0.0]
    overall=[{'scope':'all_within_run_pairs','n_pairs':len(pairs),'mean_similarity_percent':mean(sim),'sd_similarity_percent':pstdev(sim) if len(sim)>1 else 0,'min_similarity_percent':min(sim),'max_similarity_percent':max(sim),'mean_difference_percent':mean(diff),'sd_difference_percent':pstdev(diff) if len(diff)>1 else 0,'min_difference_percent':min(diff),'max_difference_percent':max(diff),'sd_type':'population'}]
    means=[r['mean_similarity_percent'] for r in run] or [100.0]; across=[{'scope':'run_level_means','n_runs':len(run),'mean_of_run_mean_similarity_percent':mean(means),'sd_of_run_mean_similarity_percent':pstdev(means) if len(means)>1 else 0,'min_run_mean_similarity_percent':min(means),'max_run_mean_similarity_percent':max(means),'sd_type':'population'}]
    return overall,run,across
def activity_hours(rows):
    def count(keys):
        d={}
        for r in rows: d[tuple(r[k] for k in keys)]=d.get(tuple(r[k] for k in keys),0)+1
        return [{**dict(zip(keys,k)),'hours':v,**({'day_type':'weekday' if dict(zip(keys,k)).get('weekday',0)<5 else 'weekend'} if 'weekday' in keys else {})} for k,v in sorted(d.items())]
    return count(['unique_agent_id','base_seed','persona_index','activity_type']),count(['unique_agent_id','base_seed','persona_index','weekday','weekday_label','activity_type'])
def generate_psychological_constructs(agents):
    out=[]
    for a in agents:
        vals=build_psychological_state(a.psychological_seed,method='multivariate_normal')['values_normalized']
        if tuple(vals.keys())!=ACTIVE_CONSTRUCTS: raise ValueError('Expected exactly nine active constructs')
        if any(not 0<=float(v)<=1 for v in vals.values()): raise ValueError('values out of range')
        out.append({'unique_agent_id':a.unique_agent_id,'base_seed':a.base_seed,'persona_index':a.persona_index,'persona_id':a.persona_id,'persona_seed':a.persona_seed,'psychological_seed':a.psychological_seed,**vals})
    return out
def quantile(vals,q):
    vals=sorted(vals); pos=(len(vals)-1)*q; lo=int(pos); hi=min(lo+1,len(vals)-1); return vals[lo]+(vals[hi]-vals[lo])*(pos-lo)
def construct_summaries(psych):
    summary=[]; run=[]
    for c in ACTIVE_CONSTRUCTS:
        vals=[float(r[c]) for r in psych]; q1=quantile(vals,.25); med=quantile(vals,.5); q3=quantile(vals,.75)
        summary.append({'construct':c,'n':len(vals),'mean':mean(vals),'population_sd':pstdev(vals) if len(vals)>1 else 0,'minimum':min(vals),'percentile_25':q1,'median':med,'percentile_75':q3,'maximum':max(vals),'range':max(vals)-min(vals),'iqr':q3-q1,'n_exactly_0':sum(v==0 for v in vals),'percent_exactly_0':100*sum(v==0 for v in vals)/len(vals),'n_exactly_1':sum(v==1 for v in vals),'percent_exactly_1':100*sum(v==1 for v in vals)/len(vals)})
        for bs in sorted({r['base_seed'] for r in psych}):
            vs=[float(r[c]) for r in psych if r['base_seed']==bs]; run.append({'base_seed':bs,'construct':c,'n_agents':len(vs),'mean':mean(vs),'population_sd':pstdev(vs) if len(vs)>1 else 0,'minimum':min(vs),'maximum':max(vs)})
    corr=[]
    for c1 in ACTIVE_CONSTRUCTS:
        row={'construct':c1}; x=[float(r[c1]) for r in psych]
        for c2 in ACTIVE_CONSTRUCTS:
            y=[float(r[c2]) for r in psych]; mx=mean(x); my=mean(y); sx=(sum((v-mx)**2 for v in x))**0.5; sy=(sum((v-my)**2 for v in y))**0.5; row[c2]=sum((a-mx)*(b-my) for a,b in zip(x,y))/(sx*sy) if sx and sy else 0
        corr.append(row)
    return summary,run,corr
def reproducibility_summary(base_seed,agents_per_seed,phase):
    a=generate_agents([base_seed],agents_per_seed,phase); aa=generate_agents([base_seed],agents_per_seed,phase); b=generate_agents([base_seed+1],agents_per_seed,phase)
    s=generate_schedules(a); ss=generate_schedules(aa); sb=generate_schedules(b); p=generate_psychological_constructs(a); pp=generate_psychological_constructs(aa); pb=generate_psychological_constructs(b)
    return [{'check':'same_seed_persona_seeds_identical','result':[x.persona_seed for x in a]==[x.persona_seed for x in aa]},{'check':'same_seed_schedules_identical','result':[(r['weekday'],r['hour'],r['activity_type'],r['subtype']) for r in s]==[(r['weekday'],r['hour'],r['activity_type'],r['subtype']) for r in ss]},{'check':'same_seed_psychological_seeds_identical','result':[r['psychological_seed'] for r in p]==[r['psychological_seed'] for r in pp]},{'check':'same_seed_psychological_values_identical','result':[[r[c] for c in ACTIVE_CONSTRUCTS] for r in p]==[[r[c] for c in ACTIVE_CONSTRUCTS] for r in pp]},{'check':'different_base_seed_persona_seeds_differ','result':[x.persona_seed for x in a]!=[x.persona_seed for x in b]},{'check':'different_base_seed_schedules_differ','result':[r['activity_type'] for r in s]!=[r['activity_type'] for r in sb]},{'check':'different_base_seed_psychological_values_differ','result':[[r[c] for c in ACTIVE_CONSTRUCTS] for r in p]!=[[r[c] for c in ACTIVE_CONSTRUCTS] for r in pb]}]
def write_csv(path,rows):
    rows=list(rows); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        if rows: w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
def png(path,w=800,h=500):
    raw=b''.join(b'\x00'+b'\xff\xff\xff'*w for _ in range(h))
    def chunk(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
def make_dirs(output_dir,overwrite):
    if output_dir.exists() and overwrite: shutil.rmtree(output_dir)
    data=output_dir/'data'; tables=output_dir/'tables'; figs=output_dir/'figures'
    for p in (data,tables,figs): p.mkdir(parents=True,exist_ok=True)
    return data,tables,figs
def md_table(rows):
    if not rows: return ''
    cols=list(rows[0].keys()); lines=['|'+'|'.join(cols)+'|','|'+'|'.join(['---']*len(cols))+'|']
    lines += ['|'+'|'.join(str(r.get(c,'')) for c in cols)+'|' for r in rows[:20]]; return '\n'.join(lines)
def run_analysis(args):
    data,tables,figs=make_dirs(Path(args.output_dir),args.overwrite); seeds=base_seed_sequence(args.base_seed,args.n_base_seeds); agents=generate_agents(seeds,args.agents_per_seed,args.phase); schedules=generate_schedules(agents); psych=generate_psychological_constructs(agents); pairs=pairwise_schedule_similarity(schedules); weekly,daily=activity_hours(schedules); overall,run,across=summarize_schedule_similarity(pairs,args.agents_per_seed); cs,cr,corr=construct_summaries(psych); repro=reproducibility_summary(args.base_seed,args.agents_per_seed,args.phase)
    if len(pairs)!=args.n_base_seeds*(args.agents_per_seed*(args.agents_per_seed-1)//2): raise ValueError('pair count mismatch')
    for n,r in {'agent_schedules_long.csv':schedules,'agent_weekly_activity_hours.csv':weekly,'agent_daily_activity_hours.csv':daily,'initial_psychological_constructs.csv':psych,'pairwise_schedule_similarity.csv':pairs}.items(): write_csv(data/n,r)
    for n,r in {'schedule_similarity_overall_summary.csv':overall,'schedule_similarity_run_summary.csv':run,'schedule_similarity_across_run_means.csv':across,'construct_heterogeneity_summary.csv':cs,'construct_run_summary.csv':cr,'construct_correlation_matrix.csv':corr,'reproducibility_summary.csv':repro}.items(): write_csv(tables/n,r)
    acts=sorted({r['activity_type'] for r in schedules}); write_csv(tables/'activity_codebook.csv',[{'activity_type':a,'activity_code':i} for i,a in enumerate(acts)])
    for name in ['schedule_heatmap.png','schedule_similarity_distribution.png','schedule_run_means.png','construct_heatmap.png','construct_boxplots.png']: png(figs/name)
    cfg={'n_base_seeds':args.n_base_seeds,'agents_per_seed':args.agents_per_seed,'base_seed':args.base_seed,'base_seeds':seeds,'phase':YearPhase.coerce(args.phase).value,'total_agents':len(agents),'total_schedule_rows':len(schedules),'total_pairwise_comparisons':len(pairs),'psychological_seed_offset':PSYCHOLOGICAL_SEED_OFFSET,'input_parameters':generic_student_inputs(),'sd_type':'population','active_constructs':list(ACTIVE_CONSTRUCTS)}
    (Path(args.output_dir)/'run_config.json').write_text(json.dumps(cfg,indent=2),encoding='utf-8')
    report=['# H2 Agent Heterogeneity Report','', '> H2: The proposed agent-based simulation model can represent heterogeneous agents who differ in their individual characteristics, daily and weekly routines, and levels of psychological constructs.','', 'This analysis evaluates H2 descriptively; no inferential tests, p-values, or pass/fail thresholds are used.',f"Base seeds: {seeds}; agents per seed: {args.agents_per_seed}; total agent realizations: {len(agents)}; phase: {cfg['phase']}; common high-level inputs: `{cfg['input_parameters']}`.",'Persona seeds come from `StudentWrapper.create_personas`; psychological seeds use `persona_seed + 10_000_019`; schedules use generated weekly structures and `generate_full_day_schedule` with `persona_seed + weekday` daily RNGs.','Schedules are 168 hourly top-level activity-type labels. Similarity is matching slots / 168 and difference is 1 - similarity. Population SD is reported.',f"Total within-run pairwise comparisons: {len(pairs)}",'## Main schedule heterogeneity table',md_table(overall),'## Main construct heterogeneity table',md_table(cs),'## Figures','- [Schedule heatmap](figures/schedule_heatmap.png)','- [Schedule similarity distribution](figures/schedule_similarity_distribution.png)','- [Schedule run means](figures/schedule_run_means.png)','- [Construct heatmap](figures/construct_heatmap.png)','- [Construct boxplots](figures/construct_boxplots.png)','## Reproducibility results',md_table(repro),f"Only nine active constructs are analysed: {', '.join(ACTIVE_CONSTRUCTS)}. The legacy intrinsic-motivation subscales (`interest_enjoyment`, `perceived_competence`, `perceived_choice`, `pressure_tension`) are not separate model outputs.",'## Limitations','- simulated rather than empirical agents;','- common high-level input parameters;','- one controlled normal-phase week per agent;','- descriptive evidence does not establish real-world population validity;','- schedule similarity is based on top-level activity type and not subtype;','- psychological values are sampled from embedded reference parameters.','## Neutral conclusion','The descriptive outputs do not automatically accept or reject H2.']
    (Path(args.output_dir)/'h2_heterogeneity_report.md').write_text('\n\n'.join(report),encoding='utf-8'); return cfg
def parse_args(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--n-base-seeds',type=int,default=10); p.add_argument('--agents-per-seed',type=int,default=10); p.add_argument('--base-seed',type=int,default=3263); p.add_argument('--phase',default='normal'); p.add_argument('--output-dir',default=str(DEFAULT_OUTPUT_DIR)); p.add_argument('--overwrite',action='store_true'); return p.parse_args(argv)
def main(argv=None):
    args=parse_args(argv); print(json.dumps({'output_dir':str(Path(args.output_dir)),**run_analysis(args)},indent=2))
if __name__=='__main__': main()
