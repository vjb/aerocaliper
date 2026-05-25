import pandas as pd
from phoenix.client import Client
import os
from dotenv import load_dotenv

def sync_datasets():
    load_dotenv()
    print("Syncing golden_dataset.csv to Phoenix Datasets...")
    client = Client()
    
    # Load the CSV
    try:
        df = pd.read_csv("golden_dataset.csv")
    except Exception as e:
        print(f"Error reading golden_dataset.csv: {e}")
        return

    # Split into finops and hr datasets for cleaner organization in Phoenix
    finops_keywords = ["cluster", "batch", "gpu", "kubernetes"]
    hr_keywords = ["pii", "salary", "contractor", "draft", "payroll", "offer letter", "health", "hr"]
    
    def determine_domain(prompt):
        prompt = str(prompt).lower()
        if any(kw in prompt for kw in hr_keywords):
            return "hr"
        return "finops"
        
    df["domain"] = df["llm.user_prompt"].apply(determine_domain)
    
    finops_df = df[df["domain"] == "finops"].copy()
    hr_df = df[df["domain"] == "hr"].copy()
    
    # Sync FinOps Dataset
    print(f"Creating 'AeroCaliper FinOps Golden' dataset with {len(finops_df)} examples...")
    client.datasets.create_dataset(
        name="AeroCaliper FinOps Golden",
        dataframe=finops_df,
        input_keys=["llm.user_prompt"],
        output_keys=["evaluation_result", "evaluation_detail"],
        metadata_keys=["trace_id", "span_id"]
    )
    
    # Sync HR Dataset
    print(f"Creating 'AeroCaliper HR Golden' dataset with {len(hr_df)} examples...")
    client.datasets.create_dataset(
        name="AeroCaliper HR Golden",
        dataframe=hr_df,
        input_keys=["llm.user_prompt"],
        output_keys=["evaluation_result", "evaluation_detail"],
        metadata_keys=["trace_id", "span_id"]
    )
    
    print("Successfully synced datasets to Phoenix Cloud!")

if __name__ == "__main__":
    sync_datasets()
