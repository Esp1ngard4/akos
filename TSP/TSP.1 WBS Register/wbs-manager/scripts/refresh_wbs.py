#!/usr/bin/env python3
"""
WBS Dashboard Generator (AI-First)
Reads a WBS JSON register, exports a self-contained HTML dashboard.

Usage:
    python refresh_wbs.py "<register.json>" "<output-html-path>" "<project-name>"
"""

import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry as R
import dates as D
from pathlib import Path
from datetime import datetime


SHORT = {"Baseline Start": "bs", "Baseline End": "be",
         "Planned Start": "ps", "Planned End": "pe",
         "Actual Start": "as", "Actual End": "ae"}


def build_schedule(items, log):
    """Resolve, derive and compare every row's dates, once, here.

    The dashboard receives instants and never parses a date, so the rules in
    dates.py have one implementation rather than a Python one and a
    JavaScript one drifting apart. Derivation is the other half of that: a
    parent's plan and actuals are the span of its descendants (R16), which
    is cheaper to compute here than to recompute on every re-render.
    """
    kids = {}
    for row in items:
        parent = row.get("Parent")
        kids.setdefault(str(parent) if parent not in (None, "") else None,
                        []).append(row)

    slips = {}
    for entry in log or []:
        if entry.get("Field") == "Planned End":
            before, after = D.resolve(entry.get("From")), D.resolve(entry.get("To"))
            if before and after and after["end"] > before["end"]:
                slips[str(entry.get("Item"))] = slips.get(str(entry.get("Item")), 0) + 1

    resolved = {}
    for row in items:
        got = {}
        for field, key in SHORT.items():
            value = D.resolve(row.get(field))
            if value:
                got[key] = {"t": value["text"], "s": value["start"],
                            "e": value["end"], "p": value["precision"]}
        resolved[str(row.get("ID"))] = got

    def descend(rid):
        out = []
        for child in kids.get(str(rid), []):
            out.append(child)
            out.extend(descend(child.get("ID")))
        return out

    payload = {}
    for row in items:
        rid = str(row.get("ID"))
        got = dict(resolved[rid])
        if kids.get(rid):
            below = [resolved[str(c.get("ID"))] for c in descend(row.get("ID"))]
            for start_key, end_key in (("ps", "pe"), ("as", "ae")):
                starts = [b[start_key] for b in below if start_key in b]
                ends = [b[end_key] for b in below if end_key in b]
                # A span needs both ends; one date below is a point, not a bar.
                if starts or ends:
                    edge = min([s["s"] for s in starts] + [e["e"] for e in ends])
                    far = max([s["s"] for s in starts] + [e["e"] for e in ends])
                    got[start_key] = {"t": "", "s": edge, "e": edge,
                                      "p": "day", "d": 1}
                    got[end_key] = {"t": "", "s": far, "e": far, "p": "day", "d": 1}
        entry = {"d": got}
        var = D.variance(
            D.resolve(row.get("Baseline End")),
            D.resolve(row.get("Planned End")) if not kids.get(rid) else None)
        if var is None and got.get("be") and got.get("pe"):
            # A parent compares its own baseline against its derived plan,
            # which is the whole point of letting a parent carry one (R17).
            var = {"amount": D.bucket(got["pe"]["e"], got["be"]["p"])
                   - D.bucket(got["be"]["e"], got["be"]["p"]),
                   "unit": D.UNITS[got["be"]["p"]], "precision": got["be"]["p"]}
        if var:
            entry["v"] = {"a": var["amount"], "u": var["unit"]}
        if slips.get(rid):
            entry["sl"] = slips[rid]
        payload[rid] = entry
    return payload


def compute_stats(items):
    """Compute summary statistics."""
    stats = {
        'total': len(items),
        'done': 0, 'implementing': 0, 'not_started': 0,
        'backlog': 0, 'funnel': 0, 'cancelled': 0, 'no_status': 0,
        'total_effort': 0,
        'sprints': {},
        'statuses': {},
        'priorities': {},
        'types': {},
    }
    for it in items:
        s = str(it.get('Status', 'No Status') or 'No Status')
        stats['statuses'][s] = stats['statuses'].get(s, 0) + 1
        if s == 'Done': stats['done'] += 1
        elif s == 'Implementing': stats['implementing'] += 1
        elif s == 'Not Started': stats['not_started'] += 1
        elif s == 'Portfolio Backlog': stats['backlog'] += 1
        elif s == 'Funnel': stats['funnel'] += 1
        elif s == 'Cancelled': stats['cancelled'] += 1
        else: stats['no_status'] += 1

        p = str(it.get('Priority', 'None') or 'None')
        stats['priorities'][p] = stats['priorities'].get(p, 0) + 1

        t = str(it.get('Type', '') or '')
        if t:
            stats['types'][t] = stats['types'].get(t, 0) + 1

        stats['total_effort'] += it.get('Estimated Effort (h)', 0) or 0

        sp = it.get('Sprint Planned')
        if sp and str(sp).startswith('S'):
            sp = str(sp)
            if sp not in stats['sprints']:
                stats['sprints'][sp] = {'items': [], 'effort': 0, 'done': 0}
            stats['sprints'][sp]['items'].append(it)
            stats['sprints'][sp]['effort'] += it.get('Estimated Effort (h)', 0) or 0
            if s == 'Done':
                stats['sprints'][sp]['done'] += 1

    return stats


CSS = '''
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;color:#1a1a2e;background:#fff;padding:24px;max-width:1200px;margin:0 auto}
.header{margin-bottom:24px;border-bottom:3px solid #4472C4;padding-bottom:12px}
.header h1{font-size:22px;color:#4472C4}
.header .sub{font-size:13px;color:#6b7280;margin-top:4px}
.kpi-strip{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}
.kpi{flex:1;min-width:110px;padding:14px 16px;border-radius:8px;border:1px solid #e5e7eb}
.kpi-val{font-size:28px;font-weight:700;line-height:1.2}
.kpi-label{font-size:12px;color:#6b7280;margin-top:2px}
.tabs{display:flex;gap:0;border-bottom:2px solid #e5e7eb;margin-bottom:16px;flex-wrap:wrap}
.tab{padding:8px 18px;cursor:pointer;font-size:13px;font-weight:600;color:#6b7280;border-bottom:2px solid transparent;margin-bottom:-2px;transition:.15s;user-select:none}
.tab:hover{color:#1a1a2e}
.tab.active{color:#4472C4;border-bottom-color:#4472C4}
.panel{display:none}.panel.active{display:block}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:#4472C4;color:#fff;padding:8px 6px;text-align:left;position:sticky;top:0;font-weight:600}
td{padding:6px;border-bottom:1px solid #e5e7eb;vertical-align:top}
tr:hover td{background:#f0f4ff}
.badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.b-done{background:#dcfce7;color:#166534}.b-impl{background:#dbeafe;color:#1e40af}
.b-ns{background:#f3f4f6;color:#374151}.b-bl{background:#fef3c7;color:#92400e}
.b-fn{background:#fce7f3;color:#9d174d}.b-cx{background:#f3f4f6;color:#9ca3af;text-decoration:line-through}.b-no{background:#f9fafb;color:#9ca3af}
.sprint-section{margin-bottom:24px}
.btn.on{background:#4472C4;color:#fff;border-color:#4472C4}
.sep{display:inline-block;width:1px;height:18px;background:#e5e7eb;margin:0 6px;vertical-align:middle}
.sw{display:inline-block;width:14px;height:8px;border-radius:2px;vertical-align:middle;margin-right:4px}
.sw-base{background:#cbd5e1}.sw-plan{background:#4472C4}.sw-act{background:#22c55e}
.sw-derived{background:#c7d2fe;border:1px dashed #6366f1}
.rm-row{display:flex;align-items:center;gap:8px;border-bottom:1px solid #f1f5f9;min-height:30px}
.rm-label{width:300px;flex:none;font-size:12px;padding:4px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.rm-track{flex:1;position:relative;height:26px;background:#f8fafc;border-radius:3px;overflow:hidden}
.rm-lane{position:relative;height:7px;margin-top:1.5px}
.rm-bar{position:absolute;height:7px;border-radius:2px;font-size:9px;line-height:7px;color:#fff;padding-left:3px;overflow:hidden;white-space:nowrap}
.rm-bar.b-base{background:#cbd5e1;color:#475569}
.rm-bar.b-plan{background:#4472C4}
.rm-bar.b-act{background:#22c55e}
.rm-bar.derived{background:#c7d2fe;border:1px dashed #6366f1;color:#3730a3}
.rm-bar.b-act.derived{background:#bbf7d0;border-color:#16a34a;color:#166534}
.rm-bar.open{border-right:2px dotted #1a1a2e;border-top-right-radius:0;border-bottom-right-radius:0}
.rm-slip{width:150px;flex:none;font-size:11px;text-align:right}
.slip{font-weight:600}.slip-late{color:#dc2626}.slip-early{color:#16a34a}.slip-ok{color:#6b7280}
.slip-n{color:#b45309;font-weight:700}
.hz{display:inline-block;padding:1px 6px;border-radius:8px;background:#eef2ff;color:#4338ca;font-size:10px;font-weight:600;margin-right:4px}
.rm-head .rm-track{background:transparent;height:20px;border-bottom:2px solid #4472C4}
.rm-tick{position:absolute;top:0;height:20px;border-left:1px solid #e5e7eb;font-size:10px;color:#6b7280}
.rm-tick span{padding-left:3px;white-space:nowrap}
.rm-empty{display:flex;align-items:center;justify-content:center;color:#cbd5e1}
.rm-undated{margin-top:18px;padding-top:10px;border-top:2px dashed #e5e7eb}
.rm-undated h3{font-size:13px;color:#b45309;margin-bottom:6px}
.sprint-header{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:2px solid #4472C4;margin-bottom:8px}
.sprint-name{font-size:16px;font-weight:700}
.sprint-meta{font-size:12px;color:#6b7280}
.chart-row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px}
.chart-box{flex:1;min-width:220px;padding:16px;border:1px solid #e5e7eb;border-radius:8px}
.chart-title{font-size:13px;font-weight:600;margin-bottom:12px}
.bar-row{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.bar-label{width:90px;font-size:11px;text-align:right;flex-shrink:0}
.bar-track{flex:1;height:22px;background:#e5e7eb;border-radius:4px;overflow:hidden}
.bar-fill{height:100%;border-radius:4px;display:flex;align-items:center;padding:0 6px;font-size:10px;color:#fff;font-weight:600;min-width:fit-content}
.gantt-row{display:flex;align-items:center;margin-bottom:4px}
.gantt-label{width:300px;font-size:11px;flex-shrink:0;padding-right:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gantt-track{flex:1;height:24px;position:relative;background:#f3f4f6;border-radius:3px}
.gantt-bar{position:absolute;height:20px;top:2px;border-radius:3px;display:flex;align-items:center;padding:0 6px;font-size:9px;color:#fff;font-weight:600;white-space:nowrap;overflow:hidden}
.gantt-bar.rollup{height:10px;top:7px;opacity:.85;border:1px solid rgba(0,0,0,.15)}
.legend{margin-bottom:12px;font-size:12px;color:#6b7280}
.legend span{display:inline-block;width:12px;height:12px;border-radius:2px;vertical-align:middle;margin-right:4px}
.filters{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;align-items:center}
.filters select{padding:5px 10px;border:1px solid #e5e7eb;border-radius:4px;font-size:12px;background:#fff;color:#1a1a2e;cursor:pointer}
.filters select:focus{outline:none;border-color:#4472C4}
.btn{padding:4px 10px;border:1px solid #d1d5db;border-radius:4px;font-size:11px;background:#fff;color:#374151;cursor:pointer;user-select:none}
.btn:hover{background:#f0f4ff;border-color:#4472C4}
.twisty{display:inline-block;width:14px;cursor:pointer;color:#6b7280;user-select:none;font-size:10px}
.twisty:hover{color:#4472C4}
.leafdot{display:inline-block;width:14px;color:#d1d5db;user-select:none}
.kdtag{background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:700;margin-left:6px}
.muted{color:#6b7280;font-size:12px;margin-top:10px}
.warn{color:#b91c1c}
.timestamp{margin-top:24px;padding-top:12px;border-top:1px solid #e5e7eb;font-size:11px;color:#6b7280;text-align:right}
'''

# Plain string, not an f-string: the JS keeps its own braces. Values are
# injected through the __PLACEHOLDER__ markers at the bottom of this module.
JS = '''
const DATA=__ITEMS__;
const S=__STATS__;
const SPRINTS=__SPRINTS__;

let fStatus='All',fPriority='All',fType='All';
let activeTab='tree';
let showCancelled=false;   // R28: kept deliberately, noise by default
let zoom='month';          // day | month | quarter | sprint
const collapsed=new Set();        // node ids whose children are hidden
let ganttMode='tree';             // 'tree' | 'flat'

/* ---------- tree plumbing, shared by Breakdown and Gantt ---------- */

const byId=new Map(DATA.map(d=>[String(d.id),d]));
const kids=new Map();
DATA.forEach(d=>{
  const k=(d.pa===null||d.pa===undefined)?null:String(d.pa);
  const key=(k!==null&&byId.has(k))?k:null;     // orphan parents become roots
  if(!kids.has(key))kids.set(key,[]);
  kids.get(key).push(d);
});
const byCode=(a,b)=>String(a.c).localeCompare(String(b.c),undefined,{numeric:true});
kids.forEach(v=>v.sort(byCode));
/* Cancelled work is kept on purpose - the status exists so a dropped item
   keeps the record of why - but it is noise in the common case, and on a
   roadmap it draws bars for work that will never happen. Hidden by default,
   never hidden permanently. */
function visible(d){return showCancelled||d.s!=='Cancelled';}
function childrenOf(id){return (kids.get(id===null?null:String(id))||[]).filter(visible);}
function roots(){return childrenOf(null);}
function hasKids(d){return childrenOf(d.id).length>0;}

function descendants(id){
  const out=[],stack=[...childrenOf(id)];
  while(stack.length){const c=stack.pop();out.push(c);childrenOf(c.id).forEach(k=>stack.push(k));}
  return out;
}
function depthOf(d){
  let n=0,cur=d;
  while(cur&&cur.pa!==null&&cur.pa!==undefined&&byId.has(String(cur.pa))){cur=byId.get(String(cur.pa));n++;if(n>50)break;}
  return n;
}
function maxDepth(){return DATA.reduce((m,d)=>Math.max(m,depthOf(d)),0);}

function toggle(id){
  const k=String(id);
  if(collapsed.has(k))collapsed.delete(k);else collapsed.add(k);
  render();
}
function expandAll(){collapsed.clear();render();}
function collapseAll(){DATA.forEach(d=>{if(hasKids(d))collapsed.add(String(d.id));});render();}
function showToLevel(n){
  collapsed.clear();
  DATA.forEach(d=>{if(hasKids(d)&&depthOf(d)>=n)collapsed.add(String(d.id));});
  render();
}

/* Walk the tree honouring collapse, calling fn(node, depth). */
function walk(fn){
  (function rec(list,depth){
    list.forEach(d=>{
      fn(d,depth);
      if(hasKids(d)&&!collapsed.has(String(d.id)))rec(childrenOf(d.id),depth+1);
    });
  })(roots(),0);
}

function twisty(d){
  if(!hasKids(d))return '<span class="leafdot">·</span>';
  const open=!collapsed.has(String(d.id));
  return `<span class="twisty" onclick="toggle('${d.id}')">${open?'▾':'▸'}</span>`;
}

function treeControls(extra){
  const lv=[];
  for(let i=1;i<=Math.max(1,maxDepth());i++)lv.push(`<span class="btn" onclick="showToLevel(${i})">L${i}</span>`);
  return `<div class="filters">
    <span class="btn" onclick="expandAll()">Expand all</span>
    <span class="btn" onclick="collapseAll()">Collapse all</span>
    ${lv.join('')}${extra||''}</div>`;
}

/* ---------- the rest of the plumbing ---------- */

const sprintGroups={};
function rebuildSprints(){
  Object.keys(sprintGroups).forEach(k=>delete sprintGroups[k]);
  filtered().filter(d=>d.sp&&d.sp.startsWith('S')).forEach(d=>{
    if(!sprintGroups[d.sp])sprintGroups[d.sp]={items:[],effort:0,done:0};
    sprintGroups[d.sp].items.push(d);
    sprintGroups[d.sp].effort+=d.e||0;
    if(d.s==='Done')sprintGroups[d.sp].done++;
  });
}
function filtered(){
  return DATA.filter(d=>{
    if(!visible(d))return false;
    if(fStatus!=='All'&&d.s!==fStatus)return false;
    if(fPriority!=='All'&&d.p!==fPriority)return false;
    if(fType!=='All'&&d.ty!==fType)return false;
    return true;
  });
}
function unique(key){
  const vals=new Set();DATA.forEach(d=>{if(d[key])vals.add(d[key]);});
  return [...vals].sort();
}
function badge(s){
  const m={'Done':'b-done','Implementing':'b-impl','Not Started':'b-ns','Portfolio Backlog':'b-bl','Funnel':'b-fn','Cancelled':'b-cx'};
  return `<span class="badge ${m[s]||'b-no'}">${s}</span>`;
}
function bars(data,mx){
  return data.map(d=>{
    const w=mx>0?Math.round(d.v/mx*100):0;
    return `<div class="bar-row"><div class="bar-label">${d.l}</div><div class="bar-track"><div class="bar-fill" style="width:${Math.max(w,8)}%;background:${d.c}">${d.v}</div></div></div>`;
  }).join('');
}
function renderFilters(){
  const sel=(id,cur,opts)=>`<select onchange="${id}=this.value;render()">${['All',...opts].map(o=>`<option${o===cur?' selected':''}>${o}</option>`).join('')}</select>`;
  return `<div class="filters">${sel('fStatus',fStatus,unique('s'))}${sel('fPriority',fPriority,unique('p'))}${sel('fType',fType,unique('ty'))}</div>`;
}
function renderKPIs(){
  return `<div class="kpi-strip">
    <div class="kpi"><div class="kpi-val">${S.total}</div><div class="kpi-label">Total Items</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#3b82f6">${S.implementing}</div><div class="kpi-label">Implementing</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#22c55e">${S.done}</div><div class="kpi-label">Done</div></div>
    <div class="kpi"><div class="kpi-val" style="color:#f59e0b">${S.not_started}</div><div class="kpi-label">Not Started</div></div>
    <div class="kpi"><div class="kpi-val">${S.total_effort}h</div><div class="kpi-label">Total Effort</div></div>
    <div class="kpi"><div class="kpi-val">${Object.keys(sprintGroups).length}</div><div class="kpi-label">Planned Sprints</div></div>
  </div>`;
}

/* ---------- Breakdown ---------- */

function renderTree(){
  let h=treeControls();
  h+=`<table><tr><th>Code</th><th>Item</th><th>Type</th><th>Class</th><th>Delivers</th><th>Nature</th><th>Status</th><th>Effort</th><th>Owner</th></tr>`;
  let shown=0;
  walk((d,depth)=>{
    shown++;
    const kd=d.kd==='Y'?'<span class="kdtag">KEY</span>':'';
    const strong=(depth===0||d.kd==='Y')?'font-weight:700':'';
    const sub=collapsed.has(String(d.id))?descendants(d.id):[];
    const rolled=sub.length?` <span style="color:#6b7280">(${sub.length} hidden, ${sub.reduce((a,k)=>a+(k.e||0),0)+(d.e||0)}h)</span>`:'';
    h+=`<tr><td>${d.c||'-'}</td>
      <td style="padding-left:${8+depth*18}px;${strong}">${twisty(d)} ${d.t||'<em class="warn">(no title)</em>'}${kd}${rolled}</td>
      <td>${d.ty||'<span class="warn">—</span>'}</td><td>${d.cl==='Product'?'-':(d.cl||'-')}</td><td>${d.dl||'-'}</td><td>${d.na||'-'}</td>
      <td>${badge(d.s)}</td><td>${d.e?d.e+'h':'-'}</td><td>${d.o||'-'}</td></tr>`;
  });
  h+=`</table>`;
  let reachable=0;walk(()=>reachable++);
  const untyped=DATA.filter(d=>!d.ty).length;
  if(untyped)h+=`<p class="muted">${untyped} row(s) with no Type, shown as —.</p>`;
  h+=`<p class="muted">Filters do not apply here: hiding a parent would break the tree.</p>`;
  return h;
}

/* ---------- Deliverables ---------- */

function renderDeliverables(){
  const dels=DATA.filter(d=>d.kd==='Y').sort(byCode);
  if(!dels.length)return '<p class="muted">No rows tagged Key Deliverable = Y. Tag a Feature or Enabler to see it here.</p>';
  let h=`<table><tr><th>Code</th><th>Deliverable</th><th>Delivers</th><th>Status</th><th>Work items</th><th>Done</th><th>Progress</th><th>Effort</th><th>Planned</th><th>Released</th><th>Owner</th></tr>`;
  dels.forEach(d=>{
    const sub=descendants(d.id);
    const done=sub.filter(k=>k.s==='Done').length;
    const live=sub.filter(k=>k.s!=='Cancelled').length;
    const pct=live?Math.round(done/live*100):(d.s==='Done'?100:0);
    const effort=sub.reduce((a,k)=>a+(k.e||0),0)+(d.e||0);
    const bar=`<div style="background:#e5e7eb;border-radius:4px;height:14px;width:90px;position:relative">
      <div style="background:${pct===100?'#22c55e':'#4472C4'};width:${pct}%;height:100%;border-radius:4px"></div>
      <span style="position:absolute;inset:0;font-size:10px;text-align:center;line-height:14px;color:#1a1a2e">${pct}%</span></div>`;
    h+=`<tr><td>${d.c}</td><td><strong>${d.t}</strong></td><td>${d.dl||'-'}</td>
      <td>${badge(d.s)}</td><td>${live}</td><td>${done}</td><td>${bar}</td><td>${effort}h</td>
      <td>${d.rel||'-'}</td><td>${d.relon||'-'}</td><td>${d.o||'-'}</td></tr>`;
  });
  h+=`</table>`;
  const others=DATA.filter(d=>(d.ty==='Deliverable'||d.ty==='Feature')&&d.kd!=='Y').length;
  if(others)h+=`<p class="muted">${others} further Deliverable/Feature row(s) not flagged for an executive report. Key Deliverable is curation, not classification - Class says what kind of value a row serves.</p>`;
  return h;
}

/* ---------- Sprint board ---------- */

function renderBoard(){
  const sprints=Object.keys(sprintGroups).sort();
  let h='';
  sprints.forEach(sp=>{
    const g=sprintGroups[sp];
    h+=`<div class="sprint-section"><div class="sprint-header"><div class="sprint-name">${sp}</div>
      <div class="sprint-meta">${g.items.length} items · ${g.effort}h · ${g.done} done</div></div>
      <table><tr><th>Code</th><th>Title</th><th>Status</th><th>Priority</th><th>Effort</th><th>Type</th><th>Owner</th></tr>`;
    g.items.forEach(d=>{h+=`<tr><td>${d.c}</td><td>${d.t}</td><td>${badge(d.s)}</td><td>${d.p||'-'}</td><td>${d.e||'-'}h</td><td>${d.ty||'-'}</td><td>${d.o||'-'}</td></tr>`;});
    h+=`</table></div>`;
  });
  const unplanned=filtered().filter(d=>!d.sp||!d.sp.startsWith('S'));
  if(unplanned.length){
    h+=`<div class="sprint-section"><div class="sprint-header"><div class="sprint-name">Unplanned</div>
      <div class="sprint-meta">${unplanned.length} items</div></div>
      <table><tr><th>Code</th><th>Title</th><th>Status</th><th>Effort</th><th>Type</th><th>Owner</th></tr>`;
    unplanned.forEach(d=>{h+=`<tr><td>${d.c}</td><td>${d.t}</td><td>${badge(d.s)}</td><td>${d.e||'-'}h</td><td>${d.ty||'-'}</td><td>${d.o||'-'}</td></tr>`;});
    h+=`</table></div>`;
  }
  return h||'<p class="muted">Nothing matches the current filters.</p>';
}

/* ---------- Analytics ---------- */

function renderAnalytics(){
  const C=['#4472C4','#22c55e','#f59e0b','#8b5cf6','#ec4899','#ef4444'];
  const mk=o=>Object.keys(o).map((k,i)=>({l:k,v:o[k],c:C[i%C.length]}));
  const sd=mk(S.statuses),pd=mk(S.priorities),td=mk(S.types);
  const spd=Object.keys(sprintGroups).sort().map((sp,i)=>({l:sp,v:sprintGroups[sp].effort,c:C[i%C.length]}));
  return `<div class="chart-row"><div class="chart-box"><div class="chart-title">Status Distribution</div>${bars(sd,Math.max(...sd.map(d=>d.v),1))}</div>
  <div class="chart-box"><div class="chart-title">Priority Breakdown</div>${bars(pd,Math.max(...pd.map(d=>d.v),1))}</div></div>
  <div class="chart-row"><div class="chart-box"><div class="chart-title">Type Distribution</div>${td.length?bars(td,Math.max(...td.map(d=>d.v),1)):'<p class="muted">No types assigned</p>'}</div>
  <div class="chart-box"><div class="chart-title">Sprint Effort Allocation</div>${spd.length?bars(spd,Math.max(...spd.map(d=>d.v),1)):'<p class="muted">No sprints planned</p>'}</div></div>`;
}

/* ---------- Gantt ---------- */

function sprintSpan(d){
  // A row's own sprint, plus every descendant's, so a collapsed parent still
  // shows the range its work covers.
  const all=[d,...descendants(d.id)].map(x=>x.sp).filter(s=>s&&s.startsWith('S'));
  if(!all.length)return null;
  const sorted=[...new Set(all)].sort();
  return {from:sorted[0],to:sorted[sorted.length-1]};
}

function renderGantt(){
  const sprints=[...new Set(DATA.map(d=>d.sp).filter(s=>s&&s.startsWith('S')))].sort();
  if(!sprints.length)return '<p class="muted">No sprint-planned items to show.</p>';
  const modeBtn=`<span class="btn" onclick="ganttMode='${ganttMode==='tree'?'flat':'tree'}';render()">View: ${ganttMode==='tree'?'Hierarchy':'Flat by sprint'}</span>`;
  let h=(ganttMode==='tree'?treeControls(modeBtn):`<div class="filters">${modeBtn}</div>`);
  h+=`<div class="legend"><span style="background:#86efac"></span> Done <span style="background:#4472C4;margin-left:12px"></span> Planned <span style="background:#94a3b8;margin-left:12px"></span> Rolled up from children</div>`;
  h+=`<div class="gantt-row" style="margin-bottom:8px"><div class="gantt-label" style="font-weight:700">Work Item</div><div class="gantt-track" style="display:flex;background:transparent">`;
  sprints.forEach(sp=>{h+=`<div style="flex:1;text-align:center;font-size:11px;font-weight:600;padding:4px;border-bottom:2px solid #4472C4">${sp}</div>`;});
  h+=`</div></div>`;

  const bar=(d,depth,rollup)=>{
    const span=rollup?sprintSpan(d):(d.sp&&d.sp.startsWith('S')?{from:d.sp,to:d.sp}:null);
    let track='';
    if(span){
      const i0=sprints.indexOf(span.from),i1=sprints.indexOf(span.to);
      if(i0>=0&&i1>=0){
        const left=i0/sprints.length*100,width=(i1-i0+1)/sprints.length*100;
        const own=d.sp&&d.sp.startsWith('S');
        const colour=d.s==='Done'?'#86efac':(own?'#4472C4':'#94a3b8');
        const tc=d.s==='Done'?'#166534':'#fff';
        const sub=descendants(d.id);
        const eff=own?(d.e||0):sub.reduce((a,k)=>a+(k.e||0),0);
        track=`<div class="gantt-bar${own?'':' rollup'}" style="left:${left}%;width:${width}%;background:${colour};color:${tc}">${eff?eff+'h':''}</div>`;
      }
    }
    const pad=ganttMode==='tree'?depth*14:0;
    const label=ganttMode==='tree'?`${twisty(d)} ${d.c}. ${d.t||''}`:`${d.c}. ${d.t||''}`;
    return `<div class="gantt-row"><div class="gantt-label" style="padding-left:${pad}px" title="${(d.t||'').replace(/"/g,'')}">${label}</div><div class="gantt-track">${track}</div></div>`;
  };

  if(ganttMode==='flat'){
    filtered().filter(d=>d.sp&&sprints.includes(d.sp)).sort(byCode).forEach(d=>{h+=bar(d,0,false);});
  }else{
    walk((d,depth)=>{
      // Only draw rows that have a sprint themselves or cover one below.
      if(sprintSpan(d))h+=bar(d,depth,true);
    });
  }
  return h;
}

/* ---------- roadmap ---------- */

const DAY=86400000;
const num=iso=>Date.parse(iso+'T00:00:00Z');
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function fmt(ms,mode){
  const d=new Date(ms),y=String(d.getUTCFullYear()).slice(2),m=d.getUTCMonth();
  if(mode==='day')return `${d.getUTCDate()}-${MON[m]}`;
  if(mode==='quarter')return `Q${Math.floor(m/3)+1}-${y}`;
  return `${MON[m]}-${y}`;
}

/* Every resolved instant on a row, so the span covers whatever exists. */
function instants(d){
  const out=[];
  if(d.d)for(const k in d.d){out.push(num(d.d[k].s));out.push(num(d.d[k].e));}
  return out;
}
function dated(d){return d.d&&Object.keys(d.d).length>0;}

function roadmapSpan(){
  let lo=Infinity,hi=-Infinity;
  DATA.filter(visible).forEach(d=>instants(d).forEach(v=>{if(v<lo)lo=v;if(v>hi)hi=v;}));
  SPRINTS.forEach(s=>{const a=num(s.Starts),b=num(s.Ends);if(a<lo)lo=a;if(b>hi)hi=b;});
  if(!isFinite(lo))return null;
  const pad=Math.max((hi-lo)*0.02,3*DAY);
  return {lo:lo-pad,hi:hi+pad};
}

/* Zoom changes the tick density, not the geometry: once a sprint has dates,
   the sprint view IS the date view at sprint granularity. */
function ticks(span){
  const out=[];
  if(zoom==='sprint'){
    SPRINTS.forEach(s=>{const a=num(s.Starts);
      if(a>=span.lo&&a<=span.hi)out.push({at:a,label:s.Sprint});});
    if(out.length)return out;
  }
  const step=zoom==='day'?7:0;
  if(step){for(let t=span.lo;t<=span.hi;t+=step*DAY)out.push({at:t,label:fmt(t,'day')});return out;}
  const start=new Date(span.lo),cur=new Date(Date.UTC(start.getUTCFullYear(),
      zoom==='quarter'?Math.floor(start.getUTCMonth()/3)*3:start.getUTCMonth(),1));
  while(cur.getTime()<=span.hi){
    if(cur.getTime()>=span.lo)out.push({at:cur.getTime(),label:fmt(cur.getTime(),zoom)});
    cur.setUTCMonth(cur.getUTCMonth()+(zoom==='quarter'?3:1));
  }
  return out;
}

function slipTag(d){
  if(!d.v)return '';
  const n=d.v.a,unit=d.v.u+(Math.abs(n)===1?'':'s');
  const txt=n===0?'on plan':`${Math.abs(n)} ${unit} ${n>0?'late':'early'}`;
  const cls=n>0?'slip-late':(n<0?'slip-early':'slip-ok');
  const times=d.sl?` <span class="slip-n" title="moved ${d.sl} time${d.sl===1?'':'s'}">×${d.sl}</span>`:'';
  return `<span class="slip ${cls}">${txt}</span>${times}`;
}

function renderRoadmap(){
  const span=roadmapSpan();
  if(!span)return '<p class="muted">No dates yet. Set Baseline, Planned or Actual dates to see a roadmap.</p>';
  const pct=ms=>(ms-span.lo)/(span.hi-span.lo)*100;
  const zoomBtns=['day','month','quarter','sprint'].map(z=>
    `<span class="btn${zoom===z?' on':''}" onclick="zoom='${z}';render()">${z[0].toUpperCase()+z.slice(1)}</span>`).join('');
  let h=treeControls(`<span class="sep"></span>${zoomBtns}`);
  h+=`<div class="legend">
    <span class="sw sw-base"></span> Baseline
    <span class="sw sw-plan"></span> Planned
    <span class="sw sw-derived"></span> Derived from children
    <span class="sw sw-act"></span> Actual</div>`;

  const tk=ticks(span);
  h+=`<div class="rm-row rm-head"><div class="rm-label">Work Item</div><div class="rm-track">`;
  tk.forEach(t=>{h+=`<div class="rm-tick" style="left:${pct(t.at)}%"><span>${t.label}</span></div>`;});
  h+=`</div><div class="rm-slip"></div></div>`;

  /* A pair may be half-present, and both halves mean something. "Deliver by
     Q1-26" is an end with no start - the commonest shape a commitment takes -
     and it draws across the quarter it was promised in, because that is
     exactly how precise the promise was. A start with no end is work under
     way, drawn open-ended. */
  const lane=(a,b,cls,title)=>{
    if(!a&&!b)return '';
    const from=num(a?a.s:b.s),to=num(b?b.e:a.e);
    const l=pct(from),w=Math.max(pct(to+DAY)-l,0.6);
    const derived=(a&&a.d)||(b&&b.d);
    const open=a&&!b?' open':'';
    const text=(b&&b.t)||(a&&a.t)||'';
    const tip=title+(text?': '+text:' (derived from children)')
              +(open?' — started, no end date':'');
    return `<div class="rm-bar ${cls}${derived?' derived':''}${open}" style="left:${l}%;width:${w}%" title="${tip}">${text}</div>`;
  };

  const undated=[];
  walk((d,depth)=>{
    if(!dated(d)){undated.push(d);return;}
    const s=d.d;
    h+=`<div class="rm-row"><div class="rm-label" style="padding-left:${depth*14}px" title="${(d.t||'').replace(/"/g,'')}">${twisty(d)} ${d.c}. ${d.t||''}</div>
      <div class="rm-track">
        <div class="rm-lane">${lane(s.bs,s.be,'b-base','Baseline')}</div>
        <div class="rm-lane">${lane(s.ps,s.pe,'b-plan','Planned')}</div>
        <div class="rm-lane">${lane(s.as,s.ae,'b-act','Actual')}</div>
      </div><div class="rm-slip">${slipTag(d)}</div></div>`;
  });

  /* An undated row in a roadmap is a gap to fix, and hiding it hides the gap. */
  if(undated.length){
    h+=`<div class="rm-undated"><h3>No dates yet — ${undated.length} item${undated.length===1?'':'s'}</h3>`;
    undated.forEach(d=>{
      const hz=d.hz?`<span class="hz">${d.hz}</span>`:'';
      h+=`<div class="rm-row"><div class="rm-label">${d.c}. ${d.t||''}</div>
        <div class="rm-track rm-empty">—</div><div class="rm-slip">${hz}${badge(d.s)}</div></div>`;
    });
    h+=`</div>`;
  }
  return h;
}

/* ---------- shell ---------- */

function render(){
  rebuildSprints();
  const tabs=[['tree','Breakdown'],['deliverables','Deliverables'],['roadmap','Roadmap'],['sprints','Sprint Board'],['analytics','Analytics'],['gantt','Gantt']];
  const body={tree:renderTree,deliverables:renderDeliverables,roadmap:renderRoadmap,sprints:renderBoard,analytics:renderAnalytics,gantt:renderGantt}[activeTab]();
  const showFilters=(activeTab==='sprints'||activeTab==='analytics');
  document.getElementById('app').innerHTML=`${renderKPIs()}
  <div class="tabs">${tabs.map(([k,l])=>`<div class="tab ${activeTab===k?'active':''}" onclick="activeTab='${k}';render()">${l}</div>`).join('')}</div>
  ${S.cancelled?`<div class="filters"><span class="btn${showCancelled?' on':''}" onclick="showCancelled=!showCancelled;render()">${showCancelled?'Hiding nothing':'Show '+S.cancelled+' cancelled'}</span></div>`:''}
  ${showFilters?renderFilters():''}
  <div class="panel active">${body}</div>
  <div class="timestamp">Generated __TIMESTAMP__</div>`;
}
render();
'''

SHELL = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta name="generator" content="register" data-values-hash="__HASH__">
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__PROJECT__ — WBS Dashboard</title>
<style>__CSS__</style>
</head>
<body>
<div class="header">
  <h1>__PROJECT__ — WBS Dashboard</h1>
  <div class="sub">AI-First Project Management · Generated __TIMESTAMP__</div>
</div>
<div id="app"></div>
<script>__JS__</script>
</body>
</html>'''


def generate_html(project_name, items, stats, schedule=None, sprints=None):
    """Assemble the dashboard.

    The JS and CSS are plain strings, not f-strings, so braces stay as the
    language wrote them. Values arrive through the __PLACEHOLDER__ markers
    below - substituted in dependency order, since JS is injected into SHELL
    and carries placeholders of its own.
    """
    compact = []
    for it in items:
        compact.append({
            'id': it.get('ID'),
            'pa': it.get('Parent') if it.get('Parent') not in (None, '') else None,
            'c': str(it.get('Code', '')),
            't': str(it.get('Title', '')),
            's': str(it.get('Status', 'No Status') or 'No Status'),
            'p': str(it.get('Priority', '') or ''),
            'e': it.get('Estimated Effort (h)', 0) or 0,
            'sp': str(it.get('Sprint Planned', '') or ''),
            'se': str(it.get('Sprint Ended', '') or ''),
            'ty': str(it.get('Type', '') or ''),
            'cl': str(it.get('Class', '') or ''),
            'na': str(it.get('Nature', '') or ''),
            'dl': str(it.get('Delivers', '') or ''),
            'kd': str(it.get('Key Deliverable', '') or ''),
            'hz': str(it.get('Horizon', '') or ''),
            'cat': str(it.get('Category', '') or ''),
            'o': str(it.get('Owner', '') or ''),
        })

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    for row in compact:
        entry = (schedule or {}).get(str(row['id']))
        if entry:
            row.update(entry)
    js = (JS.replace('__SPRINTS__', json.dumps(sprints or []))
            .replace('__ITEMS__', json.dumps(compact))
            .replace('__STATS__', json.dumps({
                'total': stats['total'], 'done': stats['done'],
                'implementing': stats['implementing'],
                'not_started': stats['not_started'],
                'backlog': stats['backlog'], 'funnel': stats['funnel'],
                'cancelled': stats['cancelled'], 'no_status': stats['no_status'],
                'total_effort': stats['total_effort'],
                'statuses': stats['statuses'], 'priorities': stats['priorities'],
                'types': stats['types'],
            }))
            .replace('__TIMESTAMP__', timestamp))
    return (SHELL.replace('__CSS__', CSS)
                 .replace('__JS__', js)
                 .replace('__PROJECT__', project_name)
                 .replace('__TIMESTAMP__', timestamp))


def main():
    if len(sys.argv) < 4:
        print("Usage: refresh_wbs.py <register.json> <output-html-path> <project-name>")
        sys.exit(1)

    register_path = sys.argv[1]
    html_path = sys.argv[2]
    project_name = sys.argv[3]

    register = R.load(register_path)
    # JSON rows omit their empty fields; the dashboard wants a rectangular table.
    rows = R.rows(register, "items")
    fields = []
    for row in rows:
        for name in row:
            if name not in fields:
                fields.append(name)
    items = [dict((f, row[f]) for f in fields if row.get(f) is not None)
             for row in rows]
    stats = compute_stats(items)
    schedule = build_schedule(items, register.get('schedule_log'))
    sprints = [s for s in (register.get('sprints') or [])
               if s.get('Starts') and s.get('Ends')]
    sprints.sort(key=lambda s: s['Starts'])
    html = generate_html(project_name, items, stats, schedule, sprints)

    html = html.replace('__HASH__', register['meta'].get('values_hash',''))
    Path(html_path).write_text(html, encoding='utf-8')
    print(f"Dashboard generated: {html_path}")
    dated = sum(1 for e in schedule.values() if e.get('d'))
    print(f"  Items: {stats['total']}, Done: {stats['done']}, "
          f"Sprints: {len(stats['sprints'])}")
    print(f"  Calendar: {len(sprints)} sprint(s) | {dated} item(s) with dates")


if __name__ == '__main__':
    main()
