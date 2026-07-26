
"""
09_agent_planner.py

Agent Orchestrator for AML Detection

Run:
    python 09_agent_planner.py

This script demonstrates an agentic planner that parses a natural
language request, decides which AML tools are required, and invokes
them selectively. Replace the stub functions with your FastAPI calls
or direct function calls as your project evolves.
"""

import re
from datetime import datetime

# -------------------------------
# Tool Stubs (replace later)
# -------------------------------

def eda_tool(filters):
    return {"tool":"EDA","status":"executed","summary":"Generated basic statistics and visualizations."}

def feature_tool(filters):
    return {"tool":"Feature Engineering","status":"executed","summary":"Computed AML features on filtered data."}

def ml_tool(filters):
    return {"tool":"Hybrid ML","status":"executed","summary":"Ran XGBoost + Isolation Forest risk scoring."}

def rule_tool(filters):
    return {"tool":"Rule Engine","status":"executed","summary":"Applied threshold and aggregation rules."}

def explanation_tool():
    return {"tool":"Explainability","status":"executed","summary":"Generated analyst-friendly explanations."}

# -------------------------------
# Intent Detection
# -------------------------------

def detect_intent(query: str):
    q = query.lower()

    if "structuring" in q or "smurf" in q:
        return "STRUCTURING"

    if "customer" in q and ("suspicious" in q or "risk" in q):
        return "CUSTOMER_LOOKUP"

    if "10+" in q or "under" in q:
        return "RULE_QUERY"

    if "analyse" in q or "analyze" in q or "dataset" in q:
        return "FULL_ANALYSIS"

    return "GENERAL"

# -------------------------------
# Filter Extraction
# -------------------------------

def extract_filters(query: str):
    filters = {}

    m = re.search(r'last\s+(\d+)\s+days', query.lower())
    if m:
        filters["days"] = int(m.group(1))

    m = re.search(r'customer\s*(?:id)?\s*(\d+)', query.lower())
    if m:
        filters["customer_id"] = m.group(1)

    return filters

# -------------------------------
# Planner
# -------------------------------

def build_plan(intent):
    if intent == "STRUCTURING":
        return [
            "Filter Data",
            "Feature Engineering",
            "Hybrid ML",
            "Explainability"
        ]

    if intent == "RULE_QUERY":
        return [
            "Rule Engine"
        ]

    if intent == "CUSTOMER_LOOKUP":
        return [
            "Customer Lookup",
            "Hybrid ML",
            "Explainability"
        ]

    return [
        "EDA",
        "Feature Engineering",
        "Hybrid ML",
        "Explainability"
    ]

# -------------------------------
# Execute
# -------------------------------

def execute(plan, filters):
    results=[]

    for step in plan:

        if step=="EDA":
            results.append(eda_tool(filters))

        elif step=="Feature Engineering":
            results.append(feature_tool(filters))

        elif step=="Hybrid ML":
            results.append(ml_tool(filters))

        elif step=="Rule Engine":
            results.append(rule_tool(filters))

        elif step=="Explainability":
            results.append(explanation_tool())

        elif step=="Filter Data":
            results.append({
                "tool":"Filter",
                "status":"executed",
                "summary":f"Applied filters: {filters}"
            })

        elif step=="Customer Lookup":
            results.append({
                "tool":"Customer Lookup",
                "status":"executed",
                "summary":f"Fetched customer {filters.get('customer_id','Unknown')}"
            })

    return results

# -------------------------------
# Main
# -------------------------------

if __name__ == "__main__":

    print("="*70)
    print("AI AML AGENT PLANNER")
    print("="*70)

    query = input("\nEnter your AML query:\n> ")

    intent = detect_intent(query)
    filters = extract_filters(query)
    plan = build_plan(intent)

    print("\nExecution Summary")
    print("-"*70)
    print("Query      :", query)
    print("Intent     :", intent)
    print("Filters    :", filters if filters else "None")
    print("Timestamp  :", datetime.now())

    print("\nExecution Plan")
    for i, step in enumerate(plan,1):
        print(f"{i}. {step}")

    print("\nRunning...\n")

    outputs = execute(plan, filters)

    print("Tool Results")
    print("-"*70)

    for out in outputs:
        print(f"[{out['tool']}]")
        print(out["summary"])
        print()

    print("="*70)
    print("Agent completed successfully.")
    print("="*70)
