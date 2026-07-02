# save as inspect_dataset.py, run: python inspect_dataset.py
import csv

REC = r"C:\Users\vsara\Documents\pes-university-projects\PES-U\synthetic_data\dedup_test\dedup_test_records.csv"
GT  = r"C:\Users\vsara\Documents\pes-university-projects\PES-U\synthetic_data\dedup_test\dedup_ground_truth.csv"

total = 0
dup_true = 0
with open(REC, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        total += 1
        if (row.get("is_duplicate") or "").strip().upper() == "TRUE":
            dup_true += 1

gt_pairs = 0
gt_ids = set()
with open(GT, encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        gt_pairs += 1
        gt_ids.add(row["original_id"].strip())
        gt_ids.add(row["duplicate_id"].strip())

print(f"total records:            {total}")
print(f"is_duplicate == TRUE:     {dup_true}")
print(f"ground-truth pairs:       {gt_pairs}")
print(f"unique ids in truth file: {len(gt_ids)}")
print()
print(f"If is_duplicate TRUE ({dup_true}) > ground-truth pairs ({gt_pairs}),")
print("then the base 55k contains duplicates NOT in the answer key.")