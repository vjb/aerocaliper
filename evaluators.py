import json

def evaluate_finops_compliance(deployment_payload: dict) -> str:
    """
    A deterministic Code Evaluator designed to run within Arize Phoenix.
    
    It analyzes the deployment trace payload and scores it based on 
    strict FinOps infrastructure guardrails.
    
    Returns:
        str: 'PASSED' if compliant, 'FAILED' if a budget violation occurs.
    """
    target_cluster = deployment_payload.get("target_cluster", "")
    budget_tag = deployment_payload.get("budget_tag", "")
    workload_type = deployment_payload.get("workload_type", "").lower()
    use_spot = deployment_payload.get("use_spot", True)
    
    # 🚨 GUARDRAIL: If deploying to c3-standard-88, budget_tag MUST be 'approved'
    if "c3-standard" in target_cluster:
        if budget_tag != "approved":
            return "FAILED"
            
    # 🚨 GUARDRAIL: Batch/training workloads must use spot instances
    if any(word in workload_type for word in ["batch", "training", "experiment"]):
        if not use_spot:
            return "FAILED: Batch/training workloads on massive GPU clusters must utilize Spot instances to optimize costs. use_spot was set to False."
            
    return "PASSED"
