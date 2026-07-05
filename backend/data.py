
from datasets import load_dataset

# 1. Download the dataset
dataset = load_dataset("bharatgenai/BhashaBench-Ayur","Hindi",token="your_token_here",)

# 2. Save to your D:\ayush1 folder as CSV
for split_name, split_data in dataset.items():
    split_data.to_csv(f"D:/ayush1/{split_name}_data.csv")

print("Saved successfully as CSV files!")


