"""Weekly refresh: writes data.json that biotech-dashboard.html reads.
Run:  pip install yfinance requests anthropic ; python update_data.py
Needs env var ANTHROPIC_API_KEY (only for the AI summaries).
Hand-set fields (odds p, upside u, downside d, event dates dt) are never overwritten.
"""
import json, os, datetime, requests, yfinance as yf

TICKERS = ["MLYS","COGT","CORT","ANAB","ALT","CNTB","NGEN","VKTX","KURA","SVRA"]
NAMES = {"MLYS":"Mineralys","COGT":"Cogent","CORT":"Corcept","ANAB":"AnaptysBio","ALT":"Altimmune",
         "CNTB":"Connect Biopharma","NGEN":"NervGen","VKTX":"Viking","KURA":"Kura Oncology","SVRA":"Savara"}

def price(t):
    h = yf.Ticker(t).history(period="5d")
    return round(float(h["Close"].iloc[-1]), 2) if len(h) else None

def trials(name):
    r = requests.get("https://clinicaltrials.gov/api/v2/studies", timeout=30, params={
        "query.spons": name, "filter.overallStatus": "RECRUITING|ACTIVE_NOT_RECRUITING|NOT_YET_RECRUITING",
        "pageSize": 20, "fields": "NCTId,BriefTitle,Phase,PrimaryCompletionDate"})
    return [{"id": s["protocolSection"]["identificationModule"]["nctId"],
             "title": s["protocolSection"]["identificationModule"]["briefTitle"],
             "phase": s["protocolSection"].get("designModule", {}).get("phases", []),
             "done": s["protocolSection"].get("statusModule", {}).get("primaryCompletionDate", {}).get("date")}
            for s in r.json().get("studies", [])]

def summarize(name, tr):
    if not os.getenv("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    msg = anthropic.Anthropic().messages.create(model="claude-sonnet-4-6", max_tokens=400, messages=[{
        "role": "user", "content": f"In 3 plain sentences, where are {name}'s trials headed? Active trials: {json.dumps(tr)[:3000]}"}])
    return msg.content[0].text

out = {"asof": datetime.date.today().strftime("%b %d, %Y"), "co": []}
for t in TICKERS:
    try:
        tr = trials(NAMES[t])
        out["co"].append({"s": t, "px": price(t), "pd": out["asof"], "trials": tr,
                          **({"hd": s} if (s := summarize(NAMES[t], tr)) else {})})
    except Exception as e:
        print(t, "failed:", e)
json.dump(out, open("data.json", "w"), indent=1)
