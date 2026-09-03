import sys
import os
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.csv_parser import parse_ml_dataset_csv, match_ml_columns, normalize_header_name


def test_case_a_standard():
    csv_data = (
        "Description,Merchant,Amount,Payment Method,Category\n"
        "Swiggy food order,Swiggy,450.00,UPI,Food\n"
        "Uber ride,Uber,250.50,UPI,Transport\n"
    ).encode("utf-8")
    res = parse_ml_dataset_csv(csv_data)
    assert res["valid_count"] == 2
    assert res["invalid_count"] == 0
    assert "Food" in res["categories_detected"]
    assert "Transport" in res["categories_detected"]
    print("Test Case A (Standard): PASSED")


def test_case_b_amount_inr():
    csv_data = (
        "Description,Merchant,Amount (INR),Payment Method,Category\n"
        "Amazon purchase,Amazon,1299,Card,Shopping\n"
        "Electricity bill,TNEB,850.75,Net Banking,Bills\n"
    ).encode("utf-8")
    res = parse_ml_dataset_csv(csv_data)
    assert res["valid_count"] == 2
    assert res["invalid_count"] == 0
    assert "Shopping" in res["categories_detected"]
    assert "Bills" in res["categories_detected"]
    print("Test Case B (Amount INR): PASSED")


def test_case_c_snake_case_variations():
    csv_data = (
        "transaction_description,merchant_name,amount_inr,payment_method,transaction_category\n"
        "Starbucks coffee,Starbucks,380.00,UPI,Food\n"
        "Apollo pharmacy,Apollo,620.00,Card,Healthcare\n"
    ).encode("utf-8")
    res = parse_ml_dataset_csv(csv_data)
    assert res["valid_count"] == 2
    assert res["invalid_count"] == 0
    assert "Food" in res["categories_detected"]
    assert "Healthcare" in res["categories_detected"]
    print("Test Case C (Snake Case Aliases): PASSED")


def test_case_d_extra_columns():
    csv_data = (
        "Date,Description,Merchant,Amount (INR),Payment Method,Category,Transaction ID\n"
        "2026-09-01,Netflix subscription,Netflix,499.00,Card,Subscriptions,TXN10001\n"
        "2026-09-02,Flight ticket,IndiGo,4500.00,UPI,Travel,TXN10002\n"
    ).encode("utf-8")
    res = parse_ml_dataset_csv(csv_data)
    assert res["valid_count"] == 2
    assert res["invalid_count"] == 0
    assert "Subscriptions" in res["categories_detected"]
    assert "Travel" in res["categories_detected"]
    print("Test Case D (Extra Columns Allowed): PASSED")


def test_missing_column_error():
    # Missing Category
    csv_data = (
        "Description,Merchant,Amount,Payment Method\n"
        "Swiggy food order,Swiggy,450.00,UPI\n"
    ).encode("utf-8")
    try:
        parse_ml_dataset_csv(csv_data)
        assert False, "Should have raised ValueError for missing Category"
    except ValueError as e:
        assert "Missing required ML column: Category" in str(e)
        print("Test Missing Column Error: PASSED (Error:", str(e), ")")


def test_amount_and_category_cleaning():
    csv_data = (
        'Description,Merchant,Amount,Payment Method,Category\n'
        'Order 1,Store A,"₹1,250.50",UPI,Food\n'
        'Order 2,Store B,₹100,Card,  Transport  \n'
        'Order 3,Store C,"1,250",Net Banking,utilities\n'
        'Order 4,Store D,invalid_amount,UPI,Food\n'
        'Order 5,Store E,500.00,UPI,\n'
    ).encode("utf-8")
    res = parse_ml_dataset_csv(csv_data)
    # Order 4 has invalid amount, Order 5 has empty category
    assert res["valid_count"] == 3
    assert res["invalid_count"] == 2
    assert res["valid_rows_data"][0]["amount"] == "1250.50"
    assert res["valid_rows_data"][1]["amount"] == "100.00"
    assert res["valid_rows_data"][2]["amount"] == "1250.00"
    # Category 'utilities' normalized to 'Bills'
    assert "Bills" in res["categories_detected"]
    print("Test Amount and Category Cleaning: PASSED")


def test_utf8_sig_bom_and_intro_rows():
    csv_data = (
        "\ufeffFinSense Dataset Export\n"
        "Generated on 2026-09-01\n"
        "\n"
        "Description,Merchant,Amount,Payment Method,Category\n"
        "Lunch,Cafe,200.00,Cash,Food\n"
    ).encode("utf-8-sig")
    res = parse_ml_dataset_csv(csv_data)
    assert res["valid_count"] == 1
    assert "Food" in res["categories_detected"]
    print("Test UTF-8-SIG BOM and Intro Rows: PASSED")


def test_real_upi_dataset_if_exists():
    possible_paths = [
        Path(r"d:\finance ai\FinSense_UPI_Dataset_Under_5MB.csv"),
        Path(r"C:\Users\ggaja\Downloads\FinSense_UPI_Dataset_Under_5MB.csv"),
    ]
    found_path = None
    for p in possible_paths:
        if p.exists():
            found_path = p
            break

    if found_path is None:
        print("FinSense_UPI_Dataset_Under_5MB.csv not found in expected locations, skipping real file test.")
        return

    print(f"\n--- Testing Real File: {found_path.name} ---")
    with open(found_path, "rb") as f:
        raw_bytes = f.read()

    # Read original columns without parsing all rows first
    import pandas as pd
    import io
    df_sample = pd.read_csv(io.BytesIO(raw_bytes[:10000]), nrows=2)
    detected_cols = df_sample.columns.tolist()
    col_mapping, missing = match_ml_columns([str(c) for c in detected_cols])

    print(f"Detected original columns: {detected_cols}")
    mapped_summary = {target: detected_cols[idx] for target, idx in col_mapping.items()}
    print(f"Mapped ML columns: {mapped_summary}")

    res = parse_ml_dataset_csv(raw_bytes)
    print(f"Number of valid rows: {res['valid_count']}")
    print(f"Number of rejected rows: {res['invalid_count']}")
    print(f"Categories detected: {res['categories_detected']}")

    assert res["valid_count"] > 0
    assert "Missing" not in str(missing)
    print("Real UPI Dataset Test: PASSED")


if __name__ == "__main__":
    test_case_a_standard()
    test_case_b_amount_inr()
    test_case_c_snake_case_variations()
    test_case_d_extra_columns()
    test_missing_column_error()
    test_amount_and_category_cleaning()
    test_utf8_sig_bom_and_intro_rows()
    test_real_upi_dataset_if_exists()
    print("\nALL ML DATASET PARSER TESTS PASSED 100%!")
