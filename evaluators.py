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
    
    # 🚨 GUARDRAIL: If deploying to X5, budget_tag MUST be 'approved'
    if "X5" in target_cluster:
        if budget_tag != "approved":
            return "FAILED"
            
    return "PASSED"
