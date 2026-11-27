"""Fixed six-replication H3 analysis; source data remain read-only and local."""
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
from statistics import mean
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'Analysis'),str(Path(__file__).resolve().parent)]
from empirical_context_binary_v1_2 import classify_records
import validiere_replikation as validator

MEDOIDS=('C1','C2','C3','C4')
CONTEXTS=('supportive','non_supportive')
# Prespecified operational quality rule, not a statistically validated cutoff.
MAX_FALLBACK_FRACTION=0.05

def contrast(rows, *, require_downtime=False):
 details=[]
 for medoid in MEDOIDS:
  r=[x for x in rows if x['medoid']==medoid and not x['technical_fallback'] and (not require_downtime or x['downtime_length']>=1)]
  counts={c:[x for x in r if x['binary_context_class']==c] for c in CONTEXTS}
  if any(not counts[c] for c in counts):return None,[]
  rate={c:sum(x['activity_performed'] for x in counts[c])/len(counts[c]) for c in counts}
  details.append({'medoid':medoid,'supportive_n':len(counts['supportive']),'non_supportive_n':len(counts['non_supportive']),'supportive_pa_n':sum(x['activity_performed'] for x in counts['supportive']),'non_supportive_pa_n':sum(x['activity_performed'] for x in counts['non_supportive']),'difference':rate['supportive']-rate['non_supportive']})
 return mean(d['difference'] for d in details),details

def fallback_quality(rows):
 """All simulated days in denominators; no fallback imputation."""
 if len(rows)!=360 or any(sum(x['medoid']==m for x in rows)!=90 for m in MEDOIDS):
  raise ValueError('Expected 90 days for each of four medoids')
 details=[]
 for medoid in ('all',*MEDOIDS):
  for context in ('all',*CONTEXTS):
   group=[r for r in rows if (medoid=='all' or r['medoid']==medoid) and (context=='all' or r['binary_context_class']==context)]
   n=len(group); fallback=sum(bool(r['technical_fallback']) for r in group)
   details.append({'medoid':medoid,'context':context,'simulated_days':n,'fallback_days':fallback,'fallback_fraction':fallback/n if n else None,'eligible_outcome_days':n-fallback})
 # 18/360 and 4/90 pass; 19/360 or 5/90 fail.
 overall=details[0]
 medoid_all=[d for d in details if d['medoid']!='all' and d['context']=='all']
 passed=overall['fallback_days']<=18 and all(d['fallback_days']<=4 for d in medoid_all)
 return passed,details

def sign_test(differences):
 nonzero=[d for d in differences if d!=0]; n=len(nonzero); positives=sum(d>0 for d in nonzero)
 return {'positive':positives,'negative':n-positives,'ties':len(differences)-n,'n':n,'p_one_sided':sum(math.comb(n,k) for k in range(positives,n+1))/2**n if n else None}

def main():
 a=argparse.ArgumentParser();a.add_argument('--persona-file',type=Path,required=True);a.add_argument('--baseline-manifest',type=Path,required=True);a.add_argument('--output-dir',type=Path,required=True);x=a.parse_args()
 if x.output_dir.exists():raise FileExistsError('Output directory exists; use a new one')
 frozen=json.loads((ROOT/'Analysis/h3_plan/auswertung_hashes.json').read_text(encoding='utf8'))
 if any(hashlib.sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=expected for path,expected in frozen.items()):raise ValueError('Analysis classifier or seed plan differs from frozen version')
 plan=json.loads((ROOT/'Analysis/h3_plan/replikationen.json').read_text(encoding='utf8'))['replications']
 results={name:{'replications':[],'medoids':[],'issues':[]} for name in ('primary','downtime_sensitivity')}
 quality=[];source_hashes={}
 with x.persona_file.open(encoding='utf-8-sig',newline='') as f:
  identities={f"T1_Medoid_C{r['cluster']}_{r['participant_id']}":f"C{r['cluster']}" for r in csv.DictReader(f)}
 if set(identities.values())!=set(MEDOIDS) or len(identities)!=4:raise ValueError('Wrong medoid set')
 for item in plan:
  seed=item['base_seed'];run=ROOT/item['output_dir'];validator.EXPECTED['base_seed']=seed;rep=item['replication']
  try:
   valid=validator.audit(run,x.persona_file,x.baseline_manifest)
   if valid['status']!='PASS':raise ValueError('quality validation failed')
   filenames=['simulation_run_manifest.json','full_simulation_trace.json','contexts_compact.json','daily_decision_log.csv','full_simulation_checkpoint.json']
   source_hashes[str(rep)]={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in filenames}
   rec=json.loads((run/'full_simulation_trace.json').read_text(encoding='utf8'))['records'];ctx=json.loads((run/'contexts_compact.json').read_text(encoding='utf8'))['llm_contexts']
   rows=classify_records(rec,ctx,seed,identities); passed,counts=fallback_quality(rows)
   if sum(bool(r['technical_fallback']) for r in rows)!=valid['technical_fallback_days']:raise ValueError('fallback count disagreement')
   quality.extend({'replication':rep,'quality_passed':passed,**d} for d in counts)
   if not passed:raise ValueError('fallback fraction exceeds prespecified limit')
   for name,require in [('primary',False),('downtime_sensitivity',True)]:
    value,detail=contrast(rows,require_downtime=require)
    if value is None:results[name]['issues'].append(f'replication {rep}: context category missing for a medoid');continue
    results[name]['replications'].append({'replication':rep,'base_seed':seed,'contrast_supportive_minus_non_supportive':value})
    results[name]['medoids'].extend({'replication':rep,**d} for d in detail)
  except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
   for name in results:results[name]['issues'].append(f'replication {rep}: incomplete, invalid, or outside fallback limit ({type(exc).__name__})')
 x.output_dir.mkdir(parents=True)
 def write_rows(name,rows):
  if rows:
   with (x.output_dir/name).open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 write_rows('fallback_qualitaet.csv',quality)
 summary={}
 for name,data in results.items():
  write_rows(f'{name}_replikationskontraste.csv',data['replications']);write_rows(f'{name}_medoid_aggregate.csv',data['medoids'])
  complete=len(data['replications'])==6 and not data['issues']
  summary[name]={'status':'complete' if complete else 'not_estimable','estimable_replications':len(data['replications']),'issues':data['issues'],'sign_test':sign_test([r['contrast_supportive_minus_non_supportive'] for r in data['replications']]) if complete else None}
 result={'analyses':summary,'planned_replications':6,'analysis_source_hashes':frozen,'simulation_source_file_hashes':source_hashes,'fallback_rule':'at most 5% of all 360 days AND 5% within each 90-day medoid (integer limits 18 and 4); all fallback outcomes excluded','sensitivity':'same contrast restricted to at least one contiguous downtime hour; exploratory, not a causal effect','test':'one-sided exact sign test; zeros excluded; sensitivity is descriptive/exploratory; no test if any replication/medoid missing','interpretation':'simulation-seed variation for fixed four medoids, not person/population inference; observational context association'}
 (x.output_dir/'ergebnis.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 print('H3 primary:',summary['primary']['status'],'sensitivity:',summary['downtime_sensitivity']['status']);return 0 if summary['primary']['status']=='complete' else 1
if __name__=='__main__':sys.exit(main())
