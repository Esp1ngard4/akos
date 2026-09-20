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
                # Every instant a descendant occupies, not just its starts and
                # ends taken separately. A child holding only "Q4-26" still
                # occupies all of October to December, and a parent whose span
                # ignored that collapsed to a sliver on 31 December.
                marks = [b[k] for b in below for k in (start_key, end_key) if k in b]
                if marks:
                    lo = min(m["s"] for m in marks)
                    hi = max(m["e"] for m in marks)
                    got[start_key] = {"t": "", "s": lo, "e": lo, "p": "day", "d": 1}
                    got[end_key] = {"t": "", "s": hi, "e": hi, "p": "day", "d": 1}
        # Progress over the leaves at or below this row. Only leaves carry
        # effort that is really theirs - counting a parent's own estimate too
        # would double-count the work it contains. Cancelled work is left out
        # of both halves: it is not work that will be done, so dragging the
        # denominator with it would understate real progress.
        family = [row] if not kids.get(rid) else [
            c for c in descend(row.get("ID")) if not kids.get(str(c.get("ID")))]
        family = [c for c in family if c.get("Status") != "Cancelled"]
        total = len(family)
        done = sum(1 for c in family if c.get("Status") == "Done")
        effort = sum(c.get("Estimated Effort (h)") or 0 for c in family)
        effort_done = sum(c.get("Estimated Effort (h)") or 0
                          for c in family if c.get("Status") == "Done")
        entry = {"d": got}
        if total:
            entry["pg"] = {"n": total, "dn": done,
                           "et": round(effort, 2), "eh": round(effort_done, 2)}
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
/* Freezing the date header needs the pane to own the vertical scroll as well.
   A box that scrolls horizontally is a scroll container on both axes, so a
   sticky header inside it can never stick to the page - it can only stick to
   this pane. Hence the height: the header and the name columns stay, the
   grid moves under them. */
.rm-scroll{overflow:auto;position:relative;max-height:72vh;border:1px solid #eef2f7;border-radius:6px}
.rm-inner{position:relative}
.rm-grid{position:absolute;right:0;top:0;bottom:0;pointer-events:none;z-index:0}
.rm-grid i{position:absolute;top:0;bottom:0;width:1px;background:#eef2f7}
/* The eye travels a long way from a name to its bars, and a hairline does not
   survive that trip. The band does the work; the rule just closes it off. */
.rm-row{display:flex;align-items:center;border-bottom:1px solid #eef2f7;min-height:30px;position:relative;z-index:1;background:#fff}
.rm-row.alt{background:#f6f8fb}
.rm-row:hover{background:#e8f0ff}
.rm-row:hover .rm-label{color:#1d4ed8}
.rm-label{width:286px;flex:none;font-size:12px;padding:4px 8px 4px 6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;position:sticky;left:4px;background:inherit;z-index:3}
.rm-track{flex:1;position:relative;height:26px;overflow:hidden}
.rm-lane{position:relative;height:7px;margin-top:1.5px;z-index:1}
.rm-bar{position:absolute;height:7px;border-radius:2px;font-size:9px;line-height:7px;color:#fff;padding-left:3px;overflow:hidden;white-space:nowrap}
.rm-bar.b-base{background:#cbd5e1;color:#475569}
.rm-bar.b-plan{background:#4472C4}
.rm-bar.b-act{background:#22c55e}
.rm-bar.derived{background:#c7d2fe;border:1px dashed #6366f1;color:#3730a3}
.rm-bar.b-act.derived{background:#bbf7d0;border-color:#16a34a;color:#166534}
.rm-bar.open{border-right:2px dotted #1a1a2e;border-top-right-radius:0;border-bottom-right-radius:0}
/* The slip band sits under the bars, spanning promised-end to actual-end.
   `from` is the dotted edge where it was promised; `to` is the arrow where
   it now lands. */
.rm-band{position:absolute;top:0;bottom:0;z-index:0;border-radius:2px}
.rm-band.late{background:repeating-linear-gradient(135deg,rgba(220,38,38,.13) 0 5px,rgba(220,38,38,.05) 5px 10px)}
.rm-band.early{background:repeating-linear-gradient(135deg,rgba(22,163,74,.13) 0 5px,rgba(22,163,74,.05) 5px 10px)}
.rm-band i{position:absolute;top:0;bottom:0;width:0}
.rm-band .from{left:0;border-left:1px dashed currentColor}
.rm-band .to{right:0;border-left:1px solid currentColor}
.rm-band .to:after{content:'';position:absolute;right:-1px;top:50%;margin-top:-3px;
  border:3px solid transparent;border-right:0;border-left:4px solid currentColor}
.rm-band.late{color:#dc2626}.rm-band.early{color:#16a34a}
.rm-band b{position:absolute;right:6px;top:50%;margin-top:-6px;font-size:9px;font-weight:700;
  line-height:12px;padding:0 3px;border-radius:6px;background:currentColor;color:#fff;opacity:.85}
.rm-band.early .to:after{right:auto;left:-1px;border-right:4px solid currentColor;border-left:0}
.rm-band.early .to{right:auto;left:0}
.rm-band.early .from{left:auto;right:0}
.sw-slip{background:repeating-linear-gradient(135deg,rgba(220,38,38,.35) 0 4px,rgba(220,38,38,.12) 4px 8px)}
.rm-st{width:4px;flex:none;align-self:stretch;position:sticky;left:0;z-index:4}
.rm-st.leg{display:inline-block;width:9px;height:9px;border-radius:2px;align-self:auto;position:static;margin:0 2px 0 8px}
.rm-pg{width:112px;flex:none;position:sticky;left:290px;background:inherit;z-index:3;padding-right:8px}
.pg{display:flex;flex-direction:column;gap:1px}
.pg-bar{height:5px;background:#eef2f7;border-radius:3px;overflow:hidden}
.pg-fill{display:block;height:100%;background:#4472C4;border-radius:3px}
.pg-fill.full{background:#22c55e}
.pg-num{font-size:11px;font-weight:700;color:#4472C4;line-height:1.1}
.pg-num.full{color:#16a34a}
.pg-sub{font-size:9px;color:#9ca3af;line-height:1.1}
.rm-done{position:absolute;left:0;top:0;bottom:0;background:rgba(255,255,255,.55);border-right:1px solid rgba(255,255,255,.9)}
.rm-sum{display:flex;align-items:center;gap:12px;margin:10px 0 6px;padding:10px 14px;border:1px solid #e5e7eb;border-radius:8px;background:#fafbfc}
.rm-sum-bar{flex:none;width:220px;height:10px;background:#eef2f7;border-radius:5px;overflow:hidden}
.rm-sum-bar i{display:block;height:100%;background:linear-gradient(90deg,#22c55e,#4472C4)}
.rm-sum-txt{font-size:13px}.rm-sum-txt b{font-size:17px;color:#4472C4}
.rm-head{position:sticky;top:0;z-index:5;background:#fff;box-shadow:0 1px 0 #4472C4,0 3px 6px -4px rgba(0,0,0,.35)}
.rm-head .rm-label,.rm-head .rm-pg{font-weight:700;color:#4472C4;font-size:11px;z-index:6;background:#fff}
.rm-head{background:#fff}.rm-head:hover{background:#fff}
.rm-head .rm-st{z-index:7;background:#fff}
.rm-head .rm-track{background:transparent}
/* The pinned columns need an edge too, or bars slide under them invisibly. */
.rm-pg{box-shadow:6px 0 6px -6px rgba(0,0,0,.25)}
.slip{font-weight:600}.slip-late{color:#dc2626}.slip-early{color:#16a34a}.slip-ok{color:#6b7280}
.slip-n{color:#b45309;font-weight:700}
.hz{display:inline-block;padding:1px 6px;border-radius:8px;background:#eef2ff;color:#4338ca;font-size:10px;font-weight:600;margin-right:4px}
.rm-head .rm-track{height:20px}
.rm-tick{position:absolute;top:0;height:20px;border-left:1px solid #e5e7eb;font-size:10px;color:#6b7280}
.rm-tick span{padding-left:4px;white-space:nowrap}
.rm-nowline{position:absolute;right:0;top:0;bottom:0;pointer-events:none;z-index:2}
.rm-nowline i{position:absolute;top:0;bottom:0;width:0;border-left:2px dashed #0f766e;opacity:.75}
.rm-now-lab{position:absolute;top:1px;transform:translateX(-50%);font-size:9px;font-weight:700;
  color:#fff;background:#0f766e;padding:1px 5px;border-radius:7px;white-space:nowrap;z-index:2}
.rm-undated .rm-row{padding-right:8px}
.rm-empty{display:flex;align-items:center;gap:4px;padding-left:8px;color:#cbd5e1}
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
const PIN=4+286+112;   // stripe + label + progress, all pinned left
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

const SCOL={'Done':'#22c55e','Implementing':'#3b82f6','Not Started':'#9ca3af',
  'Portfolio Backlog':'#f59e0b','Funnel':'#ec4899','Cancelled':'#d1d5db'};

/* Effort where it is estimated, count where it is not. Saying "3 of 7 items"
   on a row whose hours are unknown is honest; inventing hours to get a
   percentage is not. */
function progress(d){
  const g=d.pg; if(!g)return null;
  const byEffort=g.et>0;
  const frac=byEffort?(g.et?g.eh/g.et:0):(g.n?g.dn/g.n:0);
  return {frac:frac,byEffort:byEffort,done:g.dn,n:g.n,eh:g.eh,et:g.et};
}
function progressCell(d){
  const p=progress(d); if(!p)return '';
  const pc=Math.round(p.frac*100);
  const detail=p.byEffort?`${p.eh}h of ${p.et}h`:`${p.done} of ${p.n}`;
  const full=pc===100?' full':'';
  return `<div class="pg" title="${p.done} of ${p.n} item${p.n===1?'':'s'} done`
    +(p.byEffort?` · ${p.eh}h of ${p.et}h estimated`:' · no effort estimates, counting items')+`">
    <div class="pg-bar"><i class="pg-fill${full}" style="width:${pc}%"></i></div>
    <span class="pg-num${full}">${pc}%</span><span class="pg-sub">${detail}</span></div>`;
}

function slipText(d){
  if(!d.v)return '';
  const n=d.v.a,unit=d.v.u+(Math.abs(n)===1?'':'s');
  const txt=n===0?'on plan':`${Math.abs(n)} ${unit} ${n>0?'late':'early'}`;
  return txt+(d.sl?` · moved ${d.sl} time${d.sl===1?'':'s'}`:'');
}

/* The slip drawn as the distance it is: a band from where it was promised to
   where it now lands. Nothing to read in a column, and nothing at all on a
   row that never had a baseline to miss. */
function slipBand(d,s,pct,num,DAY){
  if(!d.v||d.v.a===0||!s.be||!s.pe)return '';
  const late=d.v.a>0;
  const a=num(late?s.be.e:s.pe.e)+DAY, b=num(late?s.pe.e:s.be.e)+DAY;
  const l=pct(Math.min(a,b)), w=Math.max(pct(Math.max(a,b))-l,0.3);
  const n=d.sl>1?`<b>${d.sl}×</b>`:'';
  return `<div class="rm-band ${late?'late':'early'}" style="left:${l}%;width:${w}%"
    title="${slipText(d)}"><i class="from"></i><i class="to"></i>${n}</div>`;
}

function renderRoadmap(){
  const span=roadmapSpan();
  if(!span)return '<p class="muted">No dates yet. Set Baseline, Planned or Actual dates to see a roadmap.</p>';
  const pct=ms=>(ms-span.lo)/(span.hi-span.lo)*100;
  const zoomBtns=['day','month','quarter','sprint'].map(z=>
    `<span class="btn${zoom===z?' on':''}" onclick="zoom='${z}';render()">${z[0].toUpperCase()+z.slice(1)}</span>`).join('');
  let h=treeControls(`<span class="sep"></span>${zoomBtns}`);
  /* The question a roadmap gets asked second, after "when": how much of it
     is actually done. Summed over visible leaves, so nothing double-counts
     and cancelled work neither helps nor hurts. */
  let tn=0,td=0,te=0,teh=0;
  DATA.filter(d=>visible(d)&&!hasKids(d)&&d.pg).forEach(d=>{
    tn+=d.pg.n;td+=d.pg.dn;te+=d.pg.et;teh+=d.pg.eh;});
  const opc=te>0?Math.round(teh/te*100):(tn?Math.round(td/tn*100):0);
  h+=`<div class="rm-sum">
    <div class="rm-sum-bar"><i style="width:${opc}%"></i></div>
    <div class="rm-sum-txt"><b>${opc}%</b> of planned work done
      <span class="muted">— ${td} of ${tn} items${te>0?`, ${Math.round(teh)}h of ${Math.round(te)}h estimated`:''}</span></div></div>`;

  h+=`<div class="legend"><b>Bars</b>
    <span class="sw sw-base"></span> Baseline
    <span class="sw sw-plan"></span> Planned
    <span class="sw sw-derived"></span> Rolled up
    <span class="sw sw-act"></span> Actual
    <span class="sw sw-slip"></span> Slip vs baseline
    <span class="sep"></span><b>Status</b>
    ${Object.keys(SCOL).filter(k=>showCancelled||k!=='Cancelled')
      .map(k=>`<i class="rm-st leg" style="background:${SCOL[k]}"></i>${k}`).join(' ')}</div>`;

  /* A tick needs room for its own label. At day or sprint zoom that is more
     room than the page has, so the track grows and scrolls rather than
     crushing the labels into each other - the name and the slip stay pinned. */
  const tk=ticks(span);
  const PER={day:58,month:84,quarter:112,sprint:78}[zoom];
  const trackW=Math.max(tk.length*PER,560);
  h+=`<div class="rm-scroll"><div class="rm-inner" style="width:${PIN+trackW}px">`;
  h+=`<div class="rm-grid" style="left:${PIN}px">`+tk.map(t=>`<i style="left:${pct(t.at)}%"></i>`).join('')+`</div>`;
  /* Where "now" falls is the reference every other bar is read against, so it
     gets its own layer rather than becoming one more gridline. */
  const now=Date.now();
  const showNow=now>=span.lo&&now<=span.hi;
  if(showNow)h+=`<div class="rm-nowline" style="left:${PIN}px"><i style="left:${pct(now)}%"></i></div>`;
  h+=`<div class="rm-row rm-head"><i class="rm-st" style="background:transparent"></i><div class="rm-label">Work Item</div><div class="rm-pg">Progress</div><div class="rm-track">`;
  tk.forEach(t=>{h+=`<div class="rm-tick" style="left:${pct(t.at)}%"><span>${t.label}</span></div>`;});
  if(showNow)h+=`<div class="rm-now-lab" style="left:${pct(now)}%">Today</div>`;
  h+=`</div></div>`;

  /* A pair may be half-present, and both halves mean something. "Deliver by
     Q1-26" is an end with no start - the commonest shape a commitment takes -
     and it draws across the quarter it was promised in, because that is
     exactly how precise the promise was. A start with no end is work under
     way, drawn open-ended. */
  const lane=(a,b,cls,title,pgFrac)=>{
    if(!a&&!b)return '';
    const fill=(pgFrac!==undefined&&pgFrac>0)?`<i class="rm-done" style="width:${Math.round(pgFrac*100)}%"></i>`:'';
    const from=num(a?a.s:b.s),to=num(b?b.e:a.e);
    const l=pct(from),w=Math.max(pct(to+DAY)-l,0.6);
    const derived=(a&&a.d)||(b&&b.d);
    const open=a&&!b?' open':'';
    const text=(b&&b.t)||(a&&a.t)||'';
    const tip=title+(text?': '+text:' (derived from children)')
              +(open?' — started, no end date':'');
    return `<div class="rm-bar ${cls}${derived?' derived':''}${open}" style="left:${l}%;width:${w}%" title="${tip}">${fill}${text}</div>`;
  };

  const undated=[];
  let rowi=0;
  walk((d,depth)=>{
    if(!dated(d)){undated.push(d);return;}
    const s=d.d;
    h+=`<div class="rm-row${(rowi++%2)?' alt':''}"><i class="rm-st" style="background:${SCOL[d.s]||'#e5e7eb'}" title="${d.s}"></i>
      <div class="rm-label" style="padding-left:${depth*14}px" title="${(d.t||'').replace(/"/g,'')} — ${d.s}">${twisty(d)} ${d.c}. ${d.t||''}</div>
      <div class="rm-pg">${progressCell(d)}</div>
      <div class="rm-track">${slipBand(d,s,pct,num,DAY)}
        <div class="rm-lane">${lane(s.bs,s.be,'b-base','Baseline')}</div>
        <div class="rm-lane">${lane(s.ps,s.pe,'b-plan','Planned',(progress(d)||{}).frac)}</div>
        <div class="rm-lane">${lane(s.as,s.ae,'b-act','Actual')}</div>
      </div></div>`;
  });

  /* An undated row in a roadmap is a gap to fix, and hiding it hides the gap. */
  /* Inside the pane, not after it: one scroll surface, and the undated rows
     line up under the same columns as everything else. */
  if(undated.length){
    h+=`<div class="rm-undated"><h3>No dates yet — ${undated.length} item${undated.length===1?'':'s'}</h3>`;
    undated.forEach(d=>{
      const hz=d.hz?`<span class="hz">${d.hz}</span>`:'';
      h+=`<div class="rm-row${(rowi++%2)?' alt':''}"><i class="rm-st" style="background:${SCOL[d.s]||'#e5e7eb'}" title="${d.s}"></i>
        <div class="rm-label">${d.c}. ${d.t||''}</div><div class="rm-pg">${progressCell(d)}</div>
        <div class="rm-track rm-empty">${hz}${badge(d.s)}</div></div>`;
    });
    h+=`</div>`;
  }
  h+=`</div></div>`;
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
