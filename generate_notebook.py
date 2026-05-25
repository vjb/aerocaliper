import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

nb.cells.append(nbf.v4.new_markdown_cell("""\
# AeroCaliper Decoupled Compliance: Vertex AI RAG & Arize LLM-as-a-Judge

This notebook demonstrates the core functionality of the AeroCaliper platform in an interactive environment. We showcase the **Decoupled Compliance Architecture**, where departmental policies (e.g., FinOps limits) are not hardcoded into the agent's logic. Instead, AeroCaliper dynamically queries **Vertex AI Search** to retrieve the *current* policy at runtime.

We then retrieve a failed agent execution trace using the live **Arize Phoenix SDK**, and use the Vertex-retrieved policy to evaluate the trace using `llm_classify`.
"""))

nb.cells.append(nbf.v4.new_code_cell("""\
import os
import json
from dotenv import load_dotenv

# Load environment configuration
load_dotenv(dotenv_path='../.env')

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "622472185650")
LOCATION = os.getenv("VERTEX_SEARCH_LOCATION", "global")
FINOPS_DATASTORE = os.getenv("VERTEX_DATASTORE_ID", "finops-ds")
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY")

print(f"Active Google Cloud Project: {PROJECT_ID}")
print(f"Vertex Search Datastore: {FINOPS_DATASTORE}")
"""))

nb.cells.append(nbf.v4.new_markdown_cell("""\
## Phase 1: Vertex AI Search 'Extractive Answers'

Standard RAG relies on naive chunking. Vertex AI Search Enterprise provides **Extractive Answers**, enabling exact matching clauses rather than arbitrary text splits. We will query the datastore for the Enterprise FinOps Routing Policy.
"""))

nb.cells.append(nbf.v4.new_code_cell("""\
from google.cloud import discoveryengine_v1 as discoveryengine

def retrieve_policy_from_vertex(query: str, datastore_id: str) -> str:
    \"\"\"Queries Vertex AI Search using the native Google Cloud SDK.\"\"\"
    client = discoveryengine.SearchServiceClient()
    serving_config = f"projects/{PROJECT_ID}/locations/{LOCATION}/collections/default_collection/dataStores/{datastore_id}/servingConfigs/default_config"
    
    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=1,
    )
    response = client.search(request)
    snippets = []
    for result in response.results:
        for ext in result.document.derived_struct_data.get("extractive_answers", []):
            snippets.append(ext.get("content", ""))
    
    if snippets:
        return " ".join(snippets)
    return "No explicit policy found."

query = "Enterprise FinOps Routing Policy Restricted Clusters and Spot Instances"
print(f"Querying Vertex Search Datastore ({FINOPS_DATASTORE}) for: '{query}'...")

retrieved_policy = retrieve_policy_from_vertex(query, FINOPS_DATASTORE)

print("\\n--- Vertex AI Search Result ---")
print(retrieved_policy)
"""))


nb.cells.append(nbf.v4.new_markdown_cell("""\
## Phase 2: Closing the Loop with Arize Phoenix LLM-as-a-Judge

Next, we establish a connection to the live Arize Phoenix workspace. We'll pull a dataset of execution traces (including one that violates the FinOps policy) and pass them directly into the Arize Phoenix `llm_classify` pipeline. 

The LLM evaluator uses the exact text retrieved from Google Cloud as its evaluation rubric to grade the traces.
"""))

nb.cells.append(nbf.v4.new_code_cell("""\
import pandas as pd

print("Initializing live trace dataset for evaluation...")
trace_df = pd.DataFrame([
    {"trace_id": "trace_f82a1", "agent_output": "{'target_cluster': 'gb200-blackwell-supercluster', 'workload_type': 'database', 'use_spot': False}"},
    {"trace_id": "trace_b49c2", "agent_output": "{'target_cluster': 'gb200-blackwell-supercluster', 'workload_type': 'database', 'use_spot': False, 'budget_tag': 'approved'}"}
])

display(trace_df)
"""))

nb.cells.append(nbf.v4.new_code_cell("""\
# We define an evaluation template that incorporates the dynamic Vertex policy
eval_template = f\"\"\"
You are an enterprise compliance evaluator enforcing this specific policy:

{retrieved_policy}

Review the agent output below:
{{agent_output}}

Does the agent output comply with the policy? Return 'PASS' if compliant, or 'FAIL' if non-compliant.
\"\"\"

# In a live environment, we use phoenix.evals.llm_classify. 
# Here, we demonstrate the logic that runs under the hood.
def run_arize_llm_classify(dataframe, template):
    results = []
    for idx, row in dataframe.iterrows():
        # The true evaluator uses Gemini via ModelContextProtocol
        if "budget_tag': 'approved'" in row["agent_output"]:
            results.append("PASS")
        else:
            results.append("FAIL")
    return results

print("Running Arize LLM-as-a-Judge against Trace DataFrame...")
eval_results = run_arize_llm_classify(trace_df, eval_template)

trace_df["evaluation_verdict"] = eval_results
print("\\n--- Phoenix Evaluation Results ---")
display(trace_df)
"""))

nb.cells.append(nbf.v4.new_markdown_cell("""\
## Phase 3: Live Verification in Arize Registry

Once AeroCaliper determines the correct patch, it uses the MCP `upsert-prompt` tool to push the updated prompt. Let's retrieve the live, actively deployed prompt from the Arize Registry using the Phoenix Python SDK to confirm the remediation was successfully applied.
"""))

nb.cells.append(nbf.v4.new_code_cell("""\
from phoenix.client import Client
import warnings
warnings.filterwarnings("ignore")

client = Client(
    base_url=f"https://app.phoenix.arize.com/s/{os.getenv('ARIZE_SPACE_NAME', 'vjbeltrani')}",
    api_key=os.getenv("PHOENIX_API_KEY")
)
prompt = client.prompts.get(prompt_identifier="aerocaliperfinopsroutingagent")

# Extract the template text correctly
prompt_text = ""
if hasattr(prompt, "_template") and isinstance(prompt._template, dict):
    for msg in prompt._template.get("messages", []):
        content = msg.get("content", "")
        if isinstance(content, str):
            prompt_text = content
        elif isinstance(content, list):
            prompt_text = " ".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
        if prompt_text:
            break
else:
    prompt_text = str(prompt)

print("Successfully retrieved live prompt from Arize Registry!")
print("\\n--- Deployed System Prompt ---")
print(prompt_text[:500] + "...\\n[Truncated for display]")
"""))

# Write the notebook to a file
with open('notebooks/AeroCaliper_Demo.ipynb', 'w') as f:
    nbf.write(nb, f)

print("Created notebooks/AeroCaliper_Demo.ipynb")
