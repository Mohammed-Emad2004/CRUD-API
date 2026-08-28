import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["LLM_STUB"] = "0"
os.environ["LLM_ENABLED"] = "true"

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def run_evaluation():
    cases_path = PROJECT_ROOT / "evals" / "cases.json"
    if not cases_path.exists():
        print(f"Error: {cases_path} not found.")
        sys.exit(1)

    with open(cases_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total_cases = len(cases)
    passed_cases = 0
    category_matches = 0
    quality_matches = 0

    results = []

    print(f"Running evaluation on {total_cases} cases...")
    print("-" * 60)

    for i, case in enumerate(cases, 1):
        case_id = case["case_id"]
        inp = case["input"]
        expected = case["expected"]

        response = client.post("/enrich", json=inp)
        status_code = response.status_code

        if status_code != 200:
            print(f"[{i}/{total_cases}] {case_id} -> HTTP {status_code}: {response.text}")
            results.append({
                "case_id": case_id,
                "status_code": status_code,
                "passed": False,
                "error": response.text,
            })
            continue

        actual = response.json()
        actual_category = actual.get("category")
        actual_flags = sorted(actual.get("quality_flags", []))
        expected_flags = sorted(expected.get("quality_flags", []))
        actual_summary = actual.get("summary", "")

        cat_pass = actual_category == expected["category"]
        qual_pass = actual_flags == expected_flags
        summary_pass = bool(actual_summary and isinstance(actual_summary, str))

        case_passed = cat_pass and qual_pass and summary_pass

        if cat_pass:
            category_matches += 1
        if qual_pass:
            quality_matches += 1
        if case_passed:
            passed_cases += 1

        print(f"[{i}/{total_cases}] {case_id}: {'PASS' if case_passed else 'FAIL'}")
        print(f"   Expected Category: {expected['category']} | Actual: {actual_category}")
        print(f"   Expected Flags:    {expected_flags} | Actual: {actual_flags}")
        print(f"   Summary:           {actual_summary}")
        print("-" * 60)

        results.append({
            "case_id": case_id,
            "passed": case_passed,
            "expected": expected,
            "actual": actual,
        })

    failed_cases = total_cases - passed_cases
    overall_pass_rate = passed_cases / total_cases
    category_accuracy = category_matches / total_cases
    quality_accuracy = quality_matches / total_cases

    summary_report = {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "overall_pass_rate": overall_pass_rate,
        "category_accuracy": category_accuracy,
        "quality_accuracy": quality_accuracy,
        "results": results,
    }

    results_path = PROJECT_ROOT / "evals" / "latest_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY REPORT")
    print("=" * 60)
    print(f"Total Cases:         {total_cases}")
    print(f"Passed Cases:        {passed_cases}")
    print(f"Failed Cases:        {failed_cases}")
    print(f"Overall Pass Rate:   {overall_pass_rate * 100:.1f}%")
    print(f"Category Accuracy:   {category_accuracy * 100:.1f}%")
    print(f"Quality Flag Accuracy: {quality_accuracy * 100:.1f}%")
    print(f"Detailed results saved to: {results_path}")
    print("=" * 60)


if __name__ == "__main__":
    run_evaluation()
