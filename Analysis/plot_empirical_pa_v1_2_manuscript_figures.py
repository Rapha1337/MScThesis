#!/usr/bin/env python3
"""Rebuild six JMIR manuscript figures from the aggregate empirical PA v1.2 report.

Usage:
    python Analysis/plot_empirical_pa_v1_2_manuscript_figures.py \
        --analysis-dir Analysis/outputs/final_empirical_pa_v1_2 \
        --output-dir Analysis/outputs/manuscript_figures

The input directory must contain final_empirical_pa_v1_2_analysis.py output tables:
01_context_pa.csv, 03_probability_pathway.csv, 05_t1_agreement_summary.csv.
Figures 1–3 show the fixed model architecture; Figures 6–8 read aggregate-only
statistics. This command never loads T1 participant records, medoid profiles,
diaries, or individual simulation traces; it does not call LLMs or rerun models.
The analysis and plot should use the same version of the source model.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
import pandas as pd

OUT: Path
mpl.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 10, 'svg.fonttype': 'none',
    'figure.facecolor': 'white', 'savefig.facecolor': 'white',
    'axes.spines.top': False, 'axes.spines.right': False,
    'axes.labelsize': 11, 'xtick.labelsize': 10, 'ytick.labelsize': 10,
})


def save(fig, basename):
    fig.savefig(OUT / (basename + '.png'), dpi=245, bbox_inches='tight',
                pad_inches=.18, facecolor='white')
    fig.savefig(OUT / (basename + '.svg'), bbox_inches='tight',
                pad_inches=.18, facecolor='white')
    plt.close(fig)


def box(ax,x,y,w,h,head,lines,fs=9,head_fs=10.5,fill='#f5f5f5'):
    p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.008,rounding_size=0.012',linewidth=1.2,edgecolor='#333333',facecolor=fill,transform=ax.transAxes,clip_on=False)
    ax.add_patch(p)
    ax.text(x+w/2,y+h-(.058 if h<.26 else .075),head,ha='center',va='top',fontsize=head_fs,fontweight='bold',transform=ax.transAxes,color='#202020')
    text='\n'.join(lines)
    ax.text(x+w/2,y+h-(.115 if h<.26 else .19),text,ha='center',va='top',fontsize=fs,linespacing=1.5,transform=ax.transAxes,color='#313131')

def arr(ax,start,end,curve=0):
    a=FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=14,lw=1.4,color='#333333',connectionstyle=f'arc3,rad={curve}',transform=ax.transAxes,clip_on=False)
    ax.add_patch(a)

def fig1():
    fig,ax=plt.subplots(figsize=(14,6.8));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    heads=['Initialization','Daily context','PA decision','Closed-loop update','Recorded outputs']
    desc=[['4 T1 medoid personas','9 psychological constructs','Individual time-use inputs'],
          ['24-hour schedules','Weather and accessibility','Energy and downtime'],
          ['LLM1 psychological prior','Action-planning calibration','LLM2 contextual probability','Feasibility + Bernoulli'],
          ['Conditional diary entry','LLM3 item-level assessment','Bounded construct update'],
          ['Binary PA + duration','Three probabilities','Longitudinal constructs','Run traces and metadata']]
    w=.166;gap=.031;x0=.018;y=.44;h=.405
    for i,(head,lines) in enumerate(zip(heads,desc)):
        x=x0+i*(w+gap)
        box(ax,x,y,w,h,head,lines,fs=9,head_fs=11)
        if i<4:arr(ax,(x+w+.004,y+.203),(x+w+gap-.004,y+.203))
    x3=x0+3*(w+gap)
    ax.plot([x3+w/2,x3+w/2],[.438,.25],color='#333333',lw=1.2,transform=ax.transAxes)
    ax.plot([x0+w/2,x3+w/2],[.25,.25],color='#333333',lw=1.2,transform=ax.transAxes)
    arr(ax,(x0+w/2,.25),(x0+w/2,.43))
    ax.text((x3+w/2+x0+w/2)/2,.274,'Updated psychological state → following day',fontsize=11,ha='center',va='bottom',fontweight='bold',transform=ax.transAxes)
    ax.text(.5,.087,'Shared calendar/weather within a run  •  Agent-specific schedules, accessibility, energy and states',fontsize=10,ha='center',transform=ax.transAxes,color='#555555')
    save(fig,'Figure_1_Model_Architecture')

def fig2():
    fig,ax=plt.subplots(figsize=(14,7.5));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    x=[.03,.281,.532,.783];w=.187;y=.51;h=.34
    stages=[('Empirical persona', ['Occupation and workload','Social and care hours','Holiday / stress weeks','Distances to PA options']),
            ('Annual / weekly', ['52-week phase structure','Normal / high stress / holiday','Weekly activity budgets','Activity-specific allocation']),
            ('Daily schedule', ['Sleep, meals and routines','Work / education / social / care','Hourly priority and time windows','No pre-scheduled PA']),
            ('Downtime windows', ['Unoccupied hourly slots','Contiguous free-time blocks','Potential PA opportunities','Not a PA commitment'])]
    for i,(t,ls) in enumerate(stages):
        box(ax,x[i],y,w,h,t,ls,fs=9.4,head_fs=11)
        if i<3: arr(ax,(x[i]+w+.006,y+.17),(x[i+1]-.008,y+.17))
    box(ax,.26,.14,.215,.19,'Temporary constraints',['Synthetic holidays; illness','Modify allocated activities'],fs=9.7,head_fs=10.8,fill='#fbfbfb')
    box(ax,.53,.14,.26,.19,'Hourly context generation',['Energy, location, weather','Accessibility and downtime'],fs=9.7,head_fs=10.8,fill='#fbfbfb')
    arr(ax,(.367,.334),(.627,.506),curve=-.08)
    arr(ax,(.876,.506),(.661,.334),curve=.08)
    ax.text(.5,.925,'Activity scheduling and availability of PA opportunities',fontsize=13,fontweight='bold',ha='center',transform=ax.transAxes)
    ax.text(.5,.052,'PA itself is not scheduled; proposed activities are checked against the available downtime later.',ha='center',fontsize=10,transform=ax.transAxes,color='#555555')
    save(fig,'Figure_2_Schedule_Generation')

def fig3():
    fig,ax=plt.subplots(figsize=(15,9));ax.axis('off');ax.set(xlim=(0,1),ylim=(0,1))
    top=[('Current state',['9 normalized constructs','Action planning neutralized']),
         ('LLM1',['Psychological PA prior','P(PA), P(no PA)']),
         ('Empirical adjustment',['T1 action-planning beta','Adjust prior odds']),
         ('LLM2',['24-h context + prior','Contextual P(PA)','Conditional PA / no-PA diaries'])]
    x=[.026,.275,.524,.773]; w=.202;y=.60;h=.295
    for i,(t,lines) in enumerate(top):
        box(ax,x[i],y,w,h,t,lines,fs=10.3,head_fs=12.2)
        if i<3:arr(ax,(x[i]+w+.004,y+.15),(x[i+1]-.008,y+.15))
    bottom=[('Time-feasibility check',['Does proposed activity fit','one contiguous downtime block?','If not: effective P(PA) = 0']),
            ('Seeded Bernoulli draw',['Sample from effective P(PA)','Performed / not performed','Record minutes (0 if skipped)']),
            ('Diary branch',['Select entry for sampled','behavioral outcome']),
            ('LLM3 + bounded update',['Diary-based item scoring','Missing evidence → no change','α = 0.20; max |Δ| = 0.10'])]
    y2=.215;h2=.265
    for i,(t,lines) in enumerate(bottom):
        xrev=x[3-i]
        box(ax,xrev,y2,w,h2,t,lines,fs=9.8,head_fs=11.4)
        if i<3:arr(ax,(xrev-.008,y2+.133),(x[2-i]+w+.008,y2+.133))
    arr(ax,(x[3]+w/2,.595),(x[3]+w/2,.482))
    ax.text(.499,.542,'LLM2 estimates a probability; it does not select the final outcome.',ha='center',va='center',fontsize=10.3,fontstyle='italic',transform=ax.transAxes)
    ax.plot([.128,.128],[.212,.085],lw=1.1,color='#333333',transform=ax.transAxes)
    ax.plot([.128,.984],[.085,.085],lw=1.1,color='#333333',transform=ax.transAxes)
    ax.text(.5,.11,'Updated state is carried forward to the next simulation day',fontsize=10,ha='center',va='bottom',transform=ax.transAxes,fontweight='bold')
    save(fig,'Figure_3_Daily_PA_Decision')


def load_table(root: Path, filename: str, required: tuple[str, ...]) -> pd.DataFrame:
    path = root / 'tables' / filename
    if not path.is_file():
        raise FileNotFoundError(f'Missing final-analysis table: {path}')
    table = pd.read_csv(path)
    missing = set(required) - set(table.columns)
    if missing:
        raise ValueError(f'{filename} is missing columns: {sorted(missing)}')
    return table


def _find_one(frame: pd.DataFrame, **filters) -> pd.Series:
    subset = frame
    for field, value in filters.items():
        subset = subset[subset[field].astype(str) == str(value)]
    if len(subset) != 1:
        raise ValueError(f'Expected exactly one row for {filters}; found {len(subset)}')
    return subset.iloc[0]


def fig6(context: pd.DataFrame):
    """PA participation with descriptive Wilson 95% CIs, by seed and medoid."""
    seeds = sorted(int(v) for v in context.seed.unique() if str(v) != 'all')
    medoids = sorted(v for v in context.medoid.unique() if v != 'all')
    groups = [('Overall', 'all', 'all')]
    groups += [(f'Seed {s}', s, 'all') for s in seeds]
    groups += [(f'Medoid {m}', 'all', m) for m in medoids] if ((context.seed.astype(str)=='all') & (context.medoid != 'all')).any() else []
    # The final analysis exports all / all, seed / all, and seed / medoid.
    # Pool seed-specific counts for each medoid, then recompute Wilson intervals.
    if len(groups) == 1 + len(seeds):
        groups += [(f'Medoid {m}', None, m) for m in medoids]

    def wilson(k, n):
        if n == 0:
            return float('nan'), float('nan')
        from statistics import NormalDist
        z = NormalDist().inv_cdf(.975)
        p = k/n
        d = 1 + z*z/n
        c = (p+z*z/(2*n))/d
        h = z * np.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
        return max(0., c-h), min(1., c+h)

    labels=[]; ys=[]; rates={'supportive':[], 'non_supportive':[]}
    lo={'supportive':[], 'non_supportive':[]}; hi={'supportive':[], 'non_supportive':[]}
    sparse=[]
    for ix, (label, seed, medoid) in enumerate(groups):
        n_total = 0
        for category in ['supportive','non_supportive']:
            if seed is None:
                rows = context[(context.seed.astype(str)!='all') & (context.medoid==medoid) & (context.context==category)]
                if len(rows) != len(seeds):
                    raise ValueError(f'Incomplete per-seed rows for medoid {medoid}, {category}')
                n = int(rows.person_days.sum()); k = int(rows.pa_days.sum())
                lb, ub = wilson(k,n)
            else:
                row = _find_one(context, seed=seed, medoid=medoid, context=category)
                n, k = int(row.person_days), int(row.pa_days)
                lb, ub = float(row.wilson95_low), float(row.wilson95_high)
            n_total += n
            rates[category].append(100*k/n if n else np.nan)
            lo[category].append(100*lb)
            hi[category].append(100*ub)
            if category == 'non_supportive' and n < 5:
                sparse.append(f'{label}: n={n}')
        labels.append(f'{label} ({n_total} days)')
        ys.append(len(groups)-1-ix)

    fig,ax=plt.subplots(figsize=(12.8,7.9))
    for idx, category in enumerate(['supportive','non_supportive']):
        x=np.asarray(rates[category]); low=np.asarray(lo[category]); high=np.asarray(hi[category])
        y=np.asarray(ys) + ([.145,-.145][idx])
        ax.errorbar(x,y,xerr=[x-low,high-x],fmt='o' if idx==0 else 's',
                    markersize=6.8,capsize=3.2,linewidth=1.3,
                    label=category.replace('_','-'),zorder=3)
        for j in range(min(3,len(groups))):
            ax.annotate(f'{x[j]:.1f}%',(x[j],y[j]),xytext=(3,5 if idx==0 else -14),
                        textcoords='offset points',fontsize=8.8)
    ax.set_yticks(ys,labels)
    ax.set_xlim(0,104);ax.set_xticks(np.arange(0,101,20))
    ax.set_xlabel('Days with physical activity (%)')
    ax.grid(axis='x',alpha=.23)
    if medoids:
        ax.axhline(len(medoids)-.5,lw=.85,color='.72')
    ax.legend(frameon=False,loc='lower center',bbox_to_anchor=(.5,1.02),ncol=2,title='Retrospective context')
    ax.text(.01,-.16,'Descriptive Wilson 95% intervals; repeated persona-days are not independent participants.',
            transform=ax.transAxes,fontsize=8.7,color='.35')
    if sparse:
        ax.text(.01,-.22,'Small non-supportive denominator: ' + '; '.join(sparse),
                transform=ax.transAxes,fontsize=8.7,color='.35')
    fig.subplots_adjust(left=.24,right=.96,bottom=.21,top=.88)
    save(fig,'Figure_6_PA_by_Context')


def fig7(probability: pd.DataFrame):
    """Exact cluster-bootstrap percentile CIs exported by the canonical analysis."""
    columns = ('behavior_policy_pa_prior','contextual_pa_probability','effective_pa_probability')
    settings = [('All days','all'),('Supportive','supportive'),('Non-supportive','non_supportive')]
    fig,ax=plt.subplots(figsize=(12.8,7.2))
    x=np.arange(3,dtype=float)
    for idx, (label, category) in enumerate(settings):
        row = _find_one(probability,seed='all',context=category)
        n=int(row.person_days)
        values=np.array([float(row[f'mean_{c}']) for c in columns])*100
        low=np.array([float(row[f'ci95_low_{c}']) for c in columns])*100
        high=np.array([float(row[f'ci95_high_{c}']) for c in columns])*100
        if np.any(low>values) or np.any(values>high):
            raise ValueError(f'Invalid bootstrap bounds in {category} probability path')
        offset=[-.12,0,.12][idx]
        ax.errorbar(x+offset,values,yerr=[values-low,high-values],
                    marker=['D','o','s'][idx],linestyle='-',linewidth=1.7,
                    markersize=7.5,capsize=4,label=f'{label} (n={n})')
        for j in range(3):
            ax.annotate(f'{values[j]:.1f}%',(x[j]+offset,values[j]),
                        xytext=(5,8 if idx==1 else -18 if idx==2 else 0),
                        textcoords='offset points',fontsize=8.6)
    ax.set_xticks(x,['Psychological prior','After LLM2','After time-feasibility check'])
    ax.set_ylim(0,99);ax.set_ylabel('Estimated probability of PA (%)')
    ax.grid(axis='y',alpha=.22)
    ax.legend(loc='upper center',ncol=3,frameon=False,bbox_to_anchor=(.5,1.09))
    ax.text(0,-.145,'Error bars: exploratory 95% percentile intervals from medoid-cluster resampling.',
            transform=ax.transAxes,fontsize=9.3,color='.35')
    ax.text(0,-.205,'The decision stages are model outputs; intervals do not establish empirical predictive validity.',
            transform=ax.transAxes,fontsize=9.3,color='.35')
    fig.subplots_adjust(left=.12,bottom=.22,right=.97,top=.84)
    save(fig,'Figure_7_Probability_Pathway')


def fig8(agreement: pd.DataFrame):
    """Mean bias with its four-paired-medoid 95% t CI, not an invalid MAE CI."""
    references=[('T1 MVPA','T1_MVPA'),('T1 total PA','T1_total_PA')]
    metrics=[]
    for label, ref in references:
        row=_find_one(agreement,seed='seed_mean',reference=ref)
        metrics.append((label,float(row.mean_bias_hours_week),float(row.bias_ci95_low),
                        float(row.bias_ci95_high),float(row.mae_hours_week),
                        float(row.rmse_hours_week),float(row.spearman_rho),int(row.medoids)))
    fig,ax=plt.subplots(figsize=(11.8,6.8))
    ys=np.arange(len(metrics))[::-1]
    points=np.asarray([m[1] for m in metrics]); low=np.asarray([m[2] for m in metrics]); high=np.asarray([m[3] for m in metrics])
    ax.errorbar(points,ys,xerr=[points-low,high-points],fmt='o',markersize=8,capsize=5,linewidth=2)
    ax.axvline(0,linewidth=1,color='.45')
    ax.set_yticks(ys,[m[0] for m in metrics])
    ax.set_xlabel('Mean bias in simulated weekly PA (hours/week)\n(simulated minus T1)')
    ax.set_title('Descriptive correspondence with empirical T1 physical activity',pad=12)
    ax.set_ylim(-.55,len(metrics)-.45)
    ax.grid(axis='x',alpha=.25)
    ax.set_xlim(min(-10.,np.floor(low.min())),max(4.2,np.ceil(high.max())))
    for yi, (label,p,lo,hi,mae,rmse,rho,n) in zip(ys,metrics):
        ax.text(p+.18,yi+.10,f'{p:+.2f} h/week',va='center',ha='left',fontsize=11,fontweight='bold')
        summary=f'95% CI {lo:+.2f} to {hi:+.2f}   |   MAE {mae:.2f}   |   RMSE {rmse:.2f}   |   Spearman rho {rho:+.2f}'
        ax.text(ax.get_xlim()[0]+.2,yi-.18,summary,va='center',ha='left',fontsize=10)
    ax.text(0,-.20,'Error bars: exploratory 95% t intervals for mean bias from four paired medoid differences.',
            transform=ax.transAxes,fontsize=10,va='top')
    ax.text(0,-.27,'Simulated PA was averaged across two seeds; MAE, RMSE, and rho are descriptive.',
            transform=ax.transAxes,fontsize=10,va='top')
    fig.tight_layout(rect=[0,.08,1,1])
    save(fig,'Figure_8_T1_Correspondence_CI')


def main() -> None:
    global OUT
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--analysis-dir',type=Path,required=True,help='Directory produced by final_empirical_pa_v1_2_analysis.py')
    parser.add_argument('--output-dir',type=Path,required=True,help='Folder for PNG/SVG figures')
    args=parser.parse_args()
    context=load_table(args.analysis_dir,'01_context_pa.csv',(
        'seed','medoid','context','person_days','pa_days','wilson95_low','wilson95_high'))
    probability=load_table(args.analysis_dir,'03_probability_pathway.csv',(
        'seed','context','person_days',
        *[f'{prefix}_{column}' for prefix in ('mean','ci95_low','ci95_high')
          for column in ('behavior_policy_pa_prior','contextual_pa_probability','effective_pa_probability')]))
    agreement=load_table(args.analysis_dir,'05_t1_agreement_summary.csv',(
        'seed','reference','medoids','mean_bias_hours_week','bias_ci95_low','bias_ci95_high',
        'mae_hours_week','rmse_hours_week','spearman_rho'))
    OUT=args.output_dir
    OUT.mkdir(parents=True,exist_ok=True)
    for fn in (fig1,fig2,fig3):
        fn()
    fig6(context);fig7(probability);fig8(agreement)
    print(f'Created Figures 1-3 and 6-8 as PNG and SVG in {OUT}')


if __name__=='__main__':
    main()
