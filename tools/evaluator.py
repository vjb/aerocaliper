import csv
import json
import google.genai
import os
from dotenv import load_dotenv
from evaluators import evaluate_finops_compliance, evaluate_hr_compliance

load_dotenv()

def run_empirical_backtest(candidate_prompt: str, domain: str) -> str:
    """
    Run the empirical backtest against the golden dataset using the candidate system prompt.
    Returns the results of the evaluation, including any failed test cases.
    """
    # Load dataset locally as fallback
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dataset_path = os.path.join(base_dir, "golden_dataset.csv")
        with open(dataset_path, "r", encoding="utf-8") as f:
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
        px_dataset = px_client.datasets.get_dataset(dataset=dataset_name)
        
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

    # Run Local Evaluation Loop in Parallel
    async def evaluate_all():
        async def evaluate_one(row):
            test_request = f"System Instructions: {candidate_prompt}\n\nUser Request: {row['llm.user_prompt']}\n\nReturn ONLY valid JSON."
            try:
                # Use client.aio for async content generation
                response = await client.aio.models.generate_content(
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
                return row['llm.user_prompt'], res, simulation_output
            except Exception as e:
                return row['llm.user_prompt'], f"Simulation parse/run error: {e}", "No valid JSON output"

        tasks = [evaluate_one(row) for row in filtered_cases]
        return await asyncio.gather(*tasks)

    # Run the event loop synchronously inside a separate thread to avoid event loop conflicts
    try:
        import threading
        results = None
        exception = None
        
        def run_evals():
            nonlocal results, exception
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(evaluate_all())
                loop.close()
            except Exception as ex:
                exception = ex

        thread = threading.Thread(target=run_evals)
        thread.start()
        thread.join()
        
        if exception:
            raise exception
    except Exception as e:
        # Fallback to sync sequential loop if loop fails
        results = []
        for row in filtered_cases:
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
                results.append((row['llm.user_prompt'], res, simulation_output))
            except Exception as ex:
                results.append((row['llm.user_prompt'], f"Simulation error: {ex}", "No valid JSON output"))

    for prompt, res, output in results:
        if res.startswith("PASSED"):
            passed_cases += 1
        else:
            failed_cases_info.append({
                "user_prompt": prompt,
                "verdict": res,
                "output": output
            })

    pass_rate = (passed_cases / len(filtered_cases)) * 100 if filtered_cases else 0
    
    if pass_rate == 100:
        return f"SUCCESS: 100% PASS ({passed_cases}/{len(filtered_cases)} cases). The prompt is fully compliant."
    else:
        return f"FAIL: {pass_rate:.0f}% PASS ({passed_cases}/{len(filtered_cases)} cases). The candidate prompt failed the following cases:\n" + json.dumps(failed_cases_info, indent=2)
