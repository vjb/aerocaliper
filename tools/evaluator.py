import csv
import json
import google.genai
import os
from evaluators import evaluate_finops_compliance, evaluate_hr_compliance

def run_empirical_backtest(candidate_prompt: str, domain: str) -> str:
    """
    Run the empirical backtest against the golden dataset using the candidate system prompt.
    Returns the results of the evaluation, including any failed test cases.
    """
    # Load dataset locally as fallback
    try:
        with open("golden_dataset.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            test_cases = list(reader)
    except FileNotFoundError:
        return "FAIL: golden_dataset.csv not found."

    filtered_cases = []
    
    # Filter the dataset based on the active policy domain
    for row in test_cases:
        is_hr_case = any(x in row.get("evaluation_detail", "").lower() or x in row.get("llm.user_prompt", "").lower() for x in ["pii", "salary", "contractor", "draft", "payroll", "offer letter", "health", "hr"])
        if (domain == "hr" and not is_hr_case) or (domain == "finops" and is_hr_case):
            continue
        filtered_cases.append(row)

    if not filtered_cases:
        return "FAIL: No test cases matched the domain."

    passed_cases = 0
    failed_cases_info = []

    client = google.genai.Client(vertexai=True, api_key=os.environ.get("GOOGLE_AGENT_PLATFORM_API_KEY"))

    # Optional: Try to run via Phoenix Experiments for hackathon UI points
    try:
        from phoenix.client import Client as PhoenixClient
        px_client = PhoenixClient()
        dataset_name = "AeroCaliper HR Golden" if domain == "hr" else "AeroCaliper FinOps Golden"
        px_dataset = px_client.datasets.get_dataset(name=dataset_name)
        
        def px_task(input):
            test_request = f"System Instructions: {candidate_prompt}\n\nUser Request: {input}\n\nReturn ONLY valid JSON."
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=test_request,
            )
            return response.text.strip()
            
        def px_evaluator(output):
            cleaned_output = output.replace("```json", "").replace("```", "").strip()
            try:
                payload = json.loads(cleaned_output)
                res = evaluate_hr_compliance(payload) if domain == "hr" else evaluate_finops_compliance(payload)
                return 1.0 if res.startswith("PASSED") else 0.0
            except Exception:
                return 0.0
                
        # This will natively log the experiment in the Phoenix UI!
        px_client.experiments.run_experiment(
            dataset=px_dataset,
            task=px_task,
            evaluators=[px_evaluator],
            experiment_name=f"auto-remediation-backtest-{domain}"
        )
        print(f"✅ Successfully logged autonomous backtest to Phoenix Experiments for {dataset_name}")
    except Exception as e:
        print(f"ℹ️ Phoenix Experiments sync skipped (falling back to local evaluation): {e}")

    # Run Local Evaluation Loop
    for idx, row in enumerate(filtered_cases, 1):
        test_request = f"System Instructions: {candidate_prompt}\n\nUser Request: {row['llm.user_prompt']}\n\nReturn ONLY valid JSON."
        
        try:
            response = client.models.generate_content(
                model="gemini-3.1-pro-preview",
                contents=test_request,
            )
            simulation_output = response.text.strip()
            
            cleaned_output = simulation_output.replace("```json", "").replace("```", "").strip()
            payload = json.loads(cleaned_output)
            
            if domain == "hr":
                res = evaluate_hr_compliance(payload)
            else:
                res = evaluate_finops_compliance(payload)
                
            if res.startswith("PASSED"):
                passed_cases += 1
            else:
                failed_cases_info.append({
                    "user_prompt": row['llm.user_prompt'],
                    "verdict": res,
                    "output": simulation_output
                })
        except Exception as e:
            failed_cases_info.append({
                "user_prompt": row['llm.user_prompt'],
                "verdict": f"Simulation parse/run error: {e}",
                "output": "No valid JSON output"
            })
            
    pass_rate = (passed_cases / len(filtered_cases)) * 100 if filtered_cases else 0
    
    if pass_rate == 100:
        return f"SUCCESS: 100% PASS ({passed_cases}/{len(filtered_cases)} cases). The prompt is fully compliant."
    else:
        return f"FAIL: {pass_rate:.0f}% PASS ({passed_cases}/{len(filtered_cases)} cases). The candidate prompt failed the following cases:\n" + json.dumps(failed_cases_info, indent=2)
