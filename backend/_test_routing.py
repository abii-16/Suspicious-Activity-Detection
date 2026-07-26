from backend.planner import plan_query

tests = [
    ("Which bank has highest suspicious transactions", "analytics_tool"),
    ("Compare Bank 10 and Bank 70", "comparison_tool"),
    ("How is the risk score calculated", "knowledge_tool"),
    ("Find structuring patterns", "pattern_detection_tool"),
    ("Find rapid transaction patterns", "pattern_detection_tool"),
    ("Investigate customer 436419", "customer_summary"),
    ("Show top 20 suspicious transactions", "top_suspicious_transactions"),
    ("Analyze the dataset", "run_eda"),
]

all_ok = True
for q, expected in tests:
    p = plan_query(q)
    first_tool = p.execution_plan[0].tool if p.execution_plan else "none"
    ok = first_tool == expected
    if not ok:
        all_ok = False
    status = "OK" if ok else "FAIL"
    print(f"  [{status}] {q[:45]} -> {first_tool}")

print()
print("All correct:", all_ok)
