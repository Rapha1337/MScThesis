"""Read-only audit for the 4 x 90 empirical PA replication; no network or simulation."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, re, sys
from datetime import date, timedelta
from pathlib import Path

DAYS=range(90)
DATES=[(date(2027,1,1)+timedelta(days=i)).isoformat() for i in DAYS]
EXPECTED={'n_personas':4,'n_days':90,'start_date':'2027-01-01','base_seed':654346558,'dry_run':False,'empirical_pa_v1_2':True}
TOTAL=360

def as_bool(value):
    if isinstance(value,bool): return value
    if value in ('True','true','1'): return True
    if value in ('False','false','0'): return False
    raise ValueError('invalid boolean')

def index_rows(rows):
    result={}
    for r in rows:
        key=(str(r['persona_id']),int(r['day_index']))
        if key in result: raise ValueError('duplicate persona-day')
        result[key]=r
    return result

def blocks(hourly):
    if not isinstance(hourly,list) or len(hourly)!=24 or [e.get('hour') for e in hourly]!=list(range(24)):
        raise ValueError('hourly context must contain chronological hours 0..23')
    groups=[]; start=None
    for i in range(25):
        free=i<24 and hourly[i].get('activity_type')=='downtime'
        if free and start is None: start=i
        if not free and start is not None: groups.append((start,i)); start=None
    return groups

def audit(folder:Path, persona_file:Path, baseline:Path):
    errors=[]; warnings=[]; out=[]
    def ensure(condition,message):
        if not condition: errors.append(message)
    def load(name): return json.loads((folder/name).read_text(encoding='utf-8'))
    trace=load('full_simulation_trace.json'); checkpoint=load('full_simulation_checkpoint.json'); manifest=load('simulation_run_manifest.json'); contexts=load('contexts_compact.json')
    baseline_manifest=json.loads(baseline.read_text(encoding='utf-8'))
    with (folder/'daily_decision_log.csv').open(encoding='utf-8-sig',newline='') as f: logs=list(csv.DictReader(f))
    with persona_file.open(encoding='utf-8-sig',newline='') as f: original=list(csv.DictReader(f))
    if len(original)!=4 or {r['cluster'] for r in original}!={'1','2','3','4'}: raise ValueError('persona input must have clusters 1..4')
    id_to_cluster={f"T1_Medoid_C{r['cluster']}_{r['participant_id']}":int(r['cluster']) for r in original}
    ensure(len(id_to_cluster)==4,'Persona IDs not unique')
    expected={(i,d) for i in id_to_cluster for d in DAYS}
    tr=index_rows(trace['records']); cp=index_rows(checkpoint['records']); log=index_rows(logs); ctx=index_rows(contexts['llm_contexts'])
    for label,rows in [('trace',tr),('checkpoint',cp),('log',log),('contexts',ctx)]: ensure(set(rows)==expected,f'{label}: persona-day set incomplete or inconsistent')
    ensure(checkpoint.get('completed_record_count')==TOTAL and len(checkpoint.get('completed_persona_days',[]))==TOTAL,'checkpoint record count')
    ensure(index_rows(checkpoint.get('completed_persona_days',[])).keys()==expected,'checkpoint completed-day keys')
    ensure(tr==cp,'checkpoint records differ from trace')
    ensure(checkpoint.get('next_persona_index')==4 and checkpoint.get('next_day_index')==0,'checkpoint cursor not complete')
    ensure(checkpoint.get('run_id')==manifest.get('run_id') and bool(manifest.get('run_id')),'manifest/checkpoint run ID mismatch')
    ensure(manifest.get('run_status')=='success','manifest run status not success')
    for name, filename in [('full_simulation_trace','full_simulation_trace.json'),('daily_decision_log','daily_decision_log.csv'),('contexts_compact','contexts_compact.json')]:
        ensure(manifest.get('output_files',{}).get(name)==filename,f'manifest output reference {name} mismatch')
        ensure(trace.get('metadata',{}).get('output_files',{}).get(name)==filename,f'trace output reference {name} mismatch')
    for k,v in EXPECTED.items():
        ensure(manifest.get('simulation',{}).get(k)==v,f'manifest config {k} mismatch')
        ensure(checkpoint.get('run_configuration',{}).get(k)==v,f'checkpoint config {k} mismatch')
        if k in trace.get('metadata',{}): ensure(trace['metadata'][k]==v,f'trace metadata {k} mismatch')
    ensure(trace.get('metadata',{}).get('n_records')==TOTAL,'trace record count')
    ensure(all(manifest.get('models',{}).get(k)=='gpt-oss-120b' for k in ('llm1','llm2','state_assessment')),'model mismatch')
    ensure(manifest.get('simulation',{}).get('temperature')==0,'temperature mismatch')
    ensure(checkpoint.get('run_configuration',{}).get('model')=='gpt-oss-120b' and checkpoint.get('run_configuration',{}).get('temperature')==0,'checkpoint model/temperature mismatch')
    digest=hashlib.sha256(persona_file.read_bytes()).hexdigest()
    ensure(manifest.get('persona_initialization',{}).get('input_sha256')==digest,'persona file hash mismatch')
    for k in ('simulation_source_sha256','prompt_sha256','persona_input_sha256'):
        ensure(manifest.get('provenance',{}).get(k)==baseline_manifest.get('provenance',{}).get(k),f'version fingerprint mismatch: {k}')
    ensure(manifest.get('model_parameters')==baseline_manifest.get('model_parameters'),'model parameters differ from pilot baseline')
    ensure(manifest.get('empirical_pa_v1_2_calibration')==baseline_manifest.get('empirical_pa_v1_2_calibration'),'calibration differs from pilot baseline')
    ensure(checkpoint.get('run_configuration',{}).get('provenance',{}).get('simulation_source_sha256')==manifest.get('provenance',{}).get('simulation_source_sha256'),'checkpoint source fingerprint mismatch')
    retry_total=0; fallbacks=0
    for key in sorted(set(tr)&set(log)&set(ctx),key=lambda k:(id_to_cluster.get(k[0],99),k[1])):
        r=tr[key]; l=log[key]; context=ctx[key]; p=r['pa_decision']; closed=r['closed_loop_update']; day=key[1]; cluster=id_to_cluster.get(key[0]); tag=f'C{cluster}/Tag{day}'
        ensure(day in DAYS and r.get('calendar_date')==DATES[day] and l.get('calendar_date')==DATES[day] and context.get('calendar_date')==DATES[day],f'{tag}: date mismatch')
        ensure(p.get('persona_id')==key[0] and p.get('day_index')==day,f'{tag}: decision key mismatch')
        availability=blocks(context['hourly_context_24h'])
        if 'hourly_context_24h' in r: ensure(r['hourly_context_24h']==context['hourly_context_24h'],f'{tag}: trace context mismatch')
        performed=as_bool(p['activity_performed']); start=p.get('start_hour'); duration=p.get('duration_min'); fallback=as_bool(p['technical_fallback'])
        retries=int(p['llm2_validation_retry_count']); attempts=int(p['llm2_validation_attempt_count']); retry_total+=retries; fallbacks+=fallback
        ensure(1<=attempts<=3 and retries==attempts-1,f'{tag}: invalid LLM2 attempts/retries')
        ensure(as_bool(closed['activity_done'])==performed and as_bool(closed['activity_performed'])==performed,f'{tag}: closed loop activity mismatch')
        ensure(as_bool(l['activity_performed'])==performed and as_bool(l['activity_done'])==performed,f'{tag}: log activity mismatch')
        ensure(l['decision_label']==p['decision_label'] and int(l['decision_code'])==p['decision_code'],f'{tag}: decision mismatch')
        ensure(as_bool(l['technical_fallback'])==fallback and int(l['llm2_validation_retry_count'])==retries and int(l['llm2_validation_attempt_count'])==attempts,f'{tag}: retry/fallback log mismatch')
        ensure(l['decision_origin']==p['decision_origin'],f'{tag}: decision origin mismatch')
        ensure((l.get('technical_fallback_reason') or '')==(p.get('technical_fallback_reason') or ''),f'{tag}: fallback reason mismatch')
        if performed:
            valid=type(start) is int and 0<=start<=23 and type(duration) is int and 1<=duration<=240
            ensure(valid,f'{tag}: invalid start or duration')
            if valid: ensure(any(a<=start and start*60+duration<=b*60 for a,b in availability),f'{tag}: activity outside one contiguous downtime block')
            ensure(p['decision_label']=='extra_activity' and not fallback,f'{tag}: invalid performed decision/fallback')
            ensure(str(start)==l['start_hour'] and str(duration)==l['duration_min'],f'{tag}: time allocation differs from log')
            ensure(closed.get('start_hour')==start and closed.get('duration_min')==duration,f'{tag}: time allocation differs from closed loop')
        else:
            ensure(p['decision_label']=='skip_activity' and start is None and duration==0,f'{tag}: invalid skip time allocation')
            ensure(l['start_hour'] in ('','None') and l['duration_min']=='0',f'{tag}: skip log time allocation')
        if fallback: ensure(p['decision_origin']=='technical_validation_fallback' and bool(p.get('technical_fallback_reason')),f'{tag}: fallback provenance missing')
        out.append({'cluster':cluster,'day_index':day,'date':DATES[day],'performed':performed,'start_hour':start,'duration_min':duration,'downtime_block_count':len(availability),'technical_fallback':fallback,'llm2_attempts':attempts,'llm2_retries':retries,'state_assessment_fallback':bool(r.get('state_assessment_fallback_used',False)),'state_assessment_attempt_count':r.get('state_assessment_attempt_count')})
    ex=manifest.get('execution',{}); failed=int(ex.get('failed_day_validation_retry_count',0))
    ensure(failed==0,'failed-day retries present in successful run')
    ensure(ex.get('validation_retry_count')==retry_total+failed and checkpoint.get('llm2_validation_retry_count')==retry_total,'retry totals differ')
    ensure(ex.get('technical_fallback_count')==fallbacks and checkpoint.get('technical_fallback_count')==fallbacks,'fallback totals differ')
    ensure(manifest.get('state_assessment',{}).get('state_assessment_call_count')==TOTAL and checkpoint.get('state_assessment_call_count')==TOTAL,'state assessment count mismatch')
    ensure(manifest.get('state_assessment',{}).get('state_assessment_dry_run_count')==0 and checkpoint.get('state_assessment_dry_run_count')==0,'unexpected dry-run state assessment')
    if fallbacks: warnings.append('Technical fallback days must be analyzed separately or excluded from primary PA outcome analyses.')
    if retry_total: warnings.append('LLM2 validation retries occurred; inspect diagnostics locally.')
    if any(row['state_assessment_fallback'] for row in out): warnings.append('State assessment fallback occurred; inspect diagnostics locally.')
    return {'status':'FAIL' if errors else 'PASS','checked_persona_days':len(out),'technical_fallback_days':fallbacks,'llm2_validation_retries':retry_total,'errors':errors,'warnings':warnings,'days':out,'limitations':['Checks persisted records; cannot independently reconstruct discarded LLM responses or detect hidden SDK-level HTTP retries.','A PASS is a technical consistency result, not empirical validation.']}

def main():
    cli=argparse.ArgumentParser(); cli.add_argument('--run-dir',type=Path,required=True); cli.add_argument('--persona-file',type=Path,required=True); cli.add_argument('--report',type=Path,required=True); cli.add_argument('--baseline-manifest',type=Path,required=True); cli.add_argument('--seed',type=int,required=True); args=cli.parse_args()
    EXPECTED['base_seed']=args.seed
    if args.report.exists(): raise FileExistsError('Report already exists; use a new report filename.')
    try: result=audit(args.run_dir,args.persona_file,args.baseline_manifest)
    except (OSError,ValueError,KeyError,TypeError,IndexError,json.JSONDecodeError): result={'status':'FAIL','errors':['Input files incomplete, malformed, or inconsistent; inspect the local run files.'],'days':[]}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open('x',encoding='utf-8') as f: json.dump(result,f,indent=2,ensure_ascii=False); f.write('\n')
    print(f"Status: {result['status']}; checked days: {len(result['days'])}; errors: {len(result['errors'])}; warnings: {len(result.get('warnings',[]))}")
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__': sys.exit(main())
