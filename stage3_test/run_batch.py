import json, subprocess, sys, os, re
sys.path.insert(0,"/Users/jesseliu/Desktop")
from test_sandbox.engine import loader
HERE="/Users/jesseliu/Desktop/test_sandbox"
ids=[l.strip() for l in open("/tmp/stage3_ids.txt") if l.strip()]
LIVE={"salesforce","jira","jira_service_desk","slack","slack_bot","google_sheets"}
def conn_of(rid):
    try: r=json.load(open(os.path.join(HERE,"recipes_clean",rid+".json")))["recipe"]
    except: return "?"
    p={s.get("provider") for s in loader.iter_steps(r)}
    if "google_sheets" in p: return "sheets"
    if p&{"jira","jira_service_desk"}: return "jira"
    if p&{"slack","slack_bot"}: return "slack"
    if "salesforce" in p: return "sf"
    return "?"
out=open("/tmp/stage3_results.jsonl","w")
done=0
for rid in ids:
    conn=conn_of(rid)
    rec={"id":rid,"conn":conn}
    try:
        p=subprocess.run(["python3","run.py",rid,"--live","--reset","--trace"],
                         cwd=HERE,capture_output=True,text=True,timeout=75)
        d=json.loads(p.stdout)
    except subprocess.TimeoutExpired:
        rec.update(result="TIMEOUT"); out.write(json.dumps(rec)+"\n"); out.flush(); done+=1; continue
    except Exception as e:
        rec.update(result="CRASH",reason=str(e)[:50]); out.write(json.dumps(rec)+"\n"); out.flush(); done+=1; continue
    status=d.get("status"); ses=d.get("side_effects",[])
    wrote=False; eff=[]
    for se in ses:
        pr=se.get("provider")
        if pr not in LIVE: continue
        data=se.get("data",{}) if isinstance(se.get("data"),dict) else {}
        op=se.get("operation","")
        if pr in("jira","jira_service_desk"):
            ok=bool(data.get("key")) and not data.get("__jira_error__") and data.get("success")!=False
        elif pr in("slack","slack_bot"):
            ok=data.get("ok") is True
        elif pr=="google_sheets":
            ok=(data.get("appended") or 0)>0
        else: ok=True
        wrote=wrote or ok
        eff.append("%s::%s%s"%(pr,op,"" if ok else "(no-effect)"))
    if status=="error":
        reason=""
        for t in d.get("trace",[]):
            if "error" in t:
                m=re.search(r"(INVALID_FIELD|INVALID_TYPE|NOT_FOUND|No such column '[^']+'|sObject type '[^']+'|_Skip|unhashable|400|404|410|channel_not_found|missing_scope)",str(t["error"]))
                reason=m.group(0) if m else str(t["error"])[:45]; break
        rec.update(result="ERROR",reason=reason,eff=eff)
    elif wrote:
        rec.update(result="LIVE-WRITE",eff=eff)
    else:
        rec.update(result="completed-no-write",eff=eff)
    out.write(json.dumps(rec)+"\n"); out.flush(); done+=1
out.close()
print("DONE %d recipes"%done)
