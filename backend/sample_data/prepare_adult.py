import os
import sys
import json
import requests

# Add backend directory to sys.path so we can import services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.preprocessor import DataPreprocessor

def main():
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
    print(f"Downloading data from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    raw_bytes = response.content
    
    print("Initializing DataPreprocessor...")
    preprocessor = DataPreprocessor()
    
    print("Processing adult.data...")
    df, report = preprocessor.process(raw_bytes, "adult.data")
    
    output_path = os.path.join(os.path.dirname(__file__), "adult_income.csv")
    print(f"Saving cleaned dataset to {output_path}...")
    df.to_csv(output_path, index=False)
    
    print("\n--- Preprocessing Report ---")
    print(json.dumps(report, indent=2))
    print("----------------------------")
    print(f"Successfully generated {output_path} with {len(df)} rows and {len(df.columns)} columns.")

if __name__ == "__main__":
    main()
