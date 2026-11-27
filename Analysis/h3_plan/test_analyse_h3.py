import math
import pytest
import csv
import json
import sys
import analysiere_h3 as analysis
from analysiere_h3 import contrast,sign_test,fallback_quality

def test_sign_exact_and_ties():
 assert sign_test([1]*6)['p_one_sided']==1/64
 assert sign_test([1]*5+[-1])['p_one_sided']==7/64
 assert sign_test([1,0,-1])['n']==2
 assert sign_test([0]*6)['p_one_sided'] is None

def row(m,group,activity,free=1,fallback=False):
 return {'medoid':m,'binary_context_class':group,'technical_fallback':fallback,'activity_performed':None if fallback else activity,'downtime_length':free}

def test_primary_unchanged_and_equal_medoid_weight():
 rows=[]
 for i in range(1,5):
  rows.extend([row(f'C{i}','supportive',True),row(f'C{i}','supportive',True),row(f'C{i}','supportive',False),row(f'C{i}','non_supportive',False,0),row(f'C{i}','non_supportive',False,1)])
 value,details=contrast(rows);assert math.isclose(value,2/3);assert len(details)==4
 assert all(d['non_supportive_n']==2 for d in details)

def test_sensitivity_excludes_zero_downtime_and_fallbacks():
 rows=[]
 for i in range(1,5):
  m=f'C{i}';rows.extend([row(m,'supportive',True),row(m,'non_supportive',False,0),row(m,'non_supportive',True,1),row(m,'non_supportive',None,1,True)])
 primary,p=contrast(rows);sensitivity,s=contrast(rows,require_downtime=True)
 assert primary==0.5 and sensitivity==0
 assert all(x['non_supportive_n']==2 for x in p)
 assert all(x['non_supportive_n']==1 and x['non_supportive_pa_n']==1 for x in s)

def test_missing_sensitivity_class_does_not_change_primary():
 rows=[]
 for i in range(1,5):rows.extend([row(f'C{i}','supportive',True),row(f'C{i}','non_supportive',False,0)])
 assert contrast(rows)[0]==1
 assert contrast(rows,require_downtime=True)==(None,[])

def test_missing_primary_category_is_not_estimable():
 rows=[row(f'C{i}','supportive',True) for i in range(1,5)]
 assert contrast(rows)==(None,[])

def population(n):
 return [row(f'C{m}','supportive' if d%2 else 'non_supportive',False,1,d<n[m-1]) for m in range(1,5) for d in range(90)]

def test_fallback_threshold_and_distribution():
 passed,details=fallback_quality(population([4,4,4,4])); assert passed
 total=next(x for x in details if x['medoid']=='all' and x['context']=='all')
 assert total['simulated_days']==360 and total['fallback_days']==16 and total['eligible_outcome_days']==344
 assert not fallback_quality(population([5,0,0,0]))[0]
 assert not fallback_quality(population([5,5,5,4]))[0]
 assert fallback_quality(population([4,0,0,0]))[0]
 with pytest.raises(ValueError):fallback_quality(population([0,0,0,0])[:-1])

def test_six_replication_pipeline_synthetic(tmp_path,monkeypatch):
 plan_dir=tmp_path/'Analysis/h3_plan';plan_dir.mkdir(parents=True)
 plan=[{'replication':i,'base_seed':i,'output_dir':f'run{i}'} for i in range(1,7)]
 (plan_dir/'replikationen.json').write_text(json.dumps({'replications':plan}))
 (plan_dir/'auswertung_hashes.json').write_text('{}')
 persona=tmp_path/'personas.csv'
 with persona.open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=['cluster','participant_id']);w.writeheader();w.writerows({'cluster':i,'participant_id':f'synthetic_{i}'} for i in range(1,5))
 for item in plan:
  run=tmp_path/item['output_dir'];run.mkdir()
  for f in ['simulation_run_manifest.json','daily_decision_log.csv','full_simulation_checkpoint.json']:(run/f).write_text('{}')
  (run/'full_simulation_trace.json').write_text(json.dumps({'records':[]}))
  (run/'contexts_compact.json').write_text(json.dumps({'llm_contexts':[]}))
 rows=[]
 for m in range(1,5):
  for d in range(90):
   is_fallback=(m==1 and d==0)
   rows.append(row(f'C{m}','supportive' if d%2 else 'non_supportive',bool(d%2),0 if d==2 else 1,is_fallback))
 monkeypatch.setattr(analysis,'ROOT',tmp_path)
 monkeypatch.setattr(analysis.validator,'audit',lambda *a:{'status':'PASS','technical_fallback_days':1})
 monkeypatch.setattr(analysis,'classify_records',lambda *a:rows)
 output=tmp_path/'result';monkeypatch.setattr(sys,'argv',['analyse','--persona-file',str(persona),'--baseline-manifest',str(tmp_path/'baseline.json'),'--output-dir',str(output)])
 assert analysis.main()==0
 result=json.loads((output/'ergebnis.json').read_text(encoding='utf8'))
 assert result['analyses']['primary']['status']=='complete'
 assert result['analyses']['downtime_sensitivity']['status']=='complete'
 assert result['analyses']['primary']['sign_test']['p_one_sided']==1/64
 with (output/'fallback_qualitaet.csv').open(encoding='utf8',newline='') as f: quality=list(csv.DictReader(f))
 assert len(quality)==6*15
 assert sum(int(x['fallback_days']) for x in quality if x['medoid']=='all' and x['context']=='all')==6
