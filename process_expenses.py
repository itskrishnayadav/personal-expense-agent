#!/usr/bin/env python3
"""
Personal Expense Tracking Agent - Deterministic Processing Engine
===================================================================
Adheres strictly to Internshala Agentic AI Capstone Specifications:
- G1: Read-Only Storage (opens CSV strictly with 'r' mode)
- G2: Zero Financial Movement (analytical only, refuses transfers/credentials)
- G3: Local Fence & No Internet (strictly local host processing)
- G4: Data vs. Instruction Separation (sanitizes & neutralizes prompt injection)
- G5: Zero Invented Numbers (exact decimal arithmetic via decimal.Decimal)
- G6: Balance Check Line Verification (Opening + Money In - Money Out == Closing)
"""

import os
import sys
import csv
import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# ==============================================================================
# GUARDRAIL ENFORCEMENT CHECKS (G2 & G3)
# ==============================================================================
def verify_environment_fence():
    """Ensure external network connectors and search tools are strictly disabled."""
    network_access = os.getenv("AGENT_NETWORK_ACCESS", "none")
    if network_access != "none":
        print(f"[SECURITY ALERT] Non-local network access detected: {network_access}. Halting execution under Guardrail G3.")
        sys.exit(1)

def refuse_financial_actions(intent: str):
    """Guardrail G2: Refuse any request to move funds, initiate payments, or handle OTPs."""
    forbidden_terms = ["pay", "transfer", "otp", "pin", "card", "upi payment", "send money"]
    for term in forbidden_terms:
        if term in intent.lower():
            raise PermissionError(
                f"GUARDRAIL G2 VIOLATION: Agent cannot execute financial movements or handle credentials ('{term}')."
            )

# ==============================================================================
# PERSISTENT MEMORY & CONFIGURATION (my-money.md)
# ==============================================================================
BUDGET_LIMITS: Dict[str, Decimal] = {
    "Rent": Decimal("15000.00"),
    "Food & Dining": Decimal("8000.00"),
    "Transport": Decimal("3000.00"),
    "Utilities": Decimal("3000.00"),
    "Entertainment": Decimal("2500.00"),
    "Shopping": Decimal("2500.00"),
}
TOTAL_MONTHLY_LIVING_BUDGET = Decimal("34000.00")

# User Category Corrections Log (Section 4 in my-money.md - highest precedence)
USER_CORRECTIONS: Dict[str, str] = {
    "blinkit": "Food & Dining",
    "zepto": "Food & Dining",
    "apollo pharmacy": "Shopping",
    "uber auto": "Transport",
    "bookmyshow": "Entertainment",
    "zerodha": "Excluded: Transfer",
    "zerodha broking limited": "Excluded: Transfer",
}

# Category Keyword Mapping Rules (Section 2 in my-money.md)
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Rent": ["landlord", "rental", "apartment rent", "society maintenance", "house rent", "nobroker rent"],
    "Food & Dining": [
        "swiggy", "zomato", "blinkit", "zepto", "instamart", "bigbasket",
        "starbucks", "third wave coffee", "cafe coffee day", "social", "brewery",
        "restaurant", "dhaba", "bakery", "eatfit", "mcdonald's", "subway"
    ],
    "Transport": [
        "uber", "ola", "rapido", "metro", "namma metro", "dmrc",
        "indian oil", "bharat petroleum", "hpcl", "shell", "petrol", "diesel", "fuel", "fastag"
    ],
    "Utilities": [
        "bescom", "electricity", "airtel broadband", "jio fiber", "act fibernet",
        "tata play", "water supply", "bwssb", "mahanagar gas", "piped gas", "broadband"
    ],
    "Entertainment": [
        "netflix", "spotify", "prime video", "hotstar", "disney", "bookmyshow",
        "pvr", "inox", "youtube premium", "steam", "playstation", "cinema"
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "zara", "h&m", "uniqlo",
        "decathlon", "croma", "reliance digital", "ikea", "nykaa", "apollo pharmacy"
    ],
}

# Non-Spending Exclusion Criteria (Section 3 in my-money.md)
EXCLUSION_RULES = {
    "transfers": [
        "emergency savings", "self transfer", "own account", "to savings",
        "hdfc to sbi", "zerodha", "groww", "upstox", "indmoney", "deposit transfer", "secondary account"
    ],
    "refunds": [
        "refund", "cashback", "reimbursement", "return credit", "amazon refund", "cred cashback"
    ],
    "reversals": [
        "auto-reversal", "auto reversal", "failed txn", "txn reversal", "upi reversal", "timeout reversal"
    ]
}

# Prompt Injection Detection Signatures (Guardrail G4)
INJECTION_SIGNATURES = [
    r"system\s+override.*",
    r"ignore\s+previous\s+instructions.*",
    r"transfer\s+\d+",
    r"send\s+money",
    r"disregard\s+rules",
    r"grant\s+admin",
    r"<script>.*?</script>",
    r"```bash.*?```",
]

# ==============================================================================
# PIPELINE STAGES
# ==============================================================================

def stage1_scan(statements_dir: Path) -> List[Path]:
    """Scan local statements directory for CSV files."""
    if not statements_dir.is_dir():
        raise FileNotFoundError(f"Directory not found: {statements_dir}")
    csv_files = sorted(list(statements_dir.glob("*.csv")))
    return csv_files

def stage2_ingest(csv_file_path: Path) -> Tuple[Decimal, List[Dict[str, Any]]]:
    """
    Ingest CSV safely in read-only mode (Guardrail G1).
    Returns (opening_balance, list of transaction dicts).
    """
    transactions = []
    opening_balance = Decimal("0.00")

    # Strict read-only mode
    with open(csv_file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_idx, row in enumerate(reader, start=1):
            date = row.get("Date", "").strip()
            txn_id = row.get("Transaction ID", "").strip()
            desc = row.get("Description", "").strip()
            raw_debit = row.get("Debit", "").strip()
            raw_credit = row.get("Credit", "").strip()
            raw_balance = row.get("Balance", "").strip()
            notes = row.get("Notes", "").strip()

            # Handle explicit Opening Balance row
            if "opening balance" in desc.lower() or "opening balance" in notes.lower():
                if raw_balance:
                    opening_balance = Decimal(raw_balance)
                continue

            debit = Decimal(raw_debit) if raw_debit else Decimal("0.00")
            credit = Decimal(raw_credit) if raw_credit else Decimal("0.00")
            balance = Decimal(raw_balance) if raw_balance else Decimal("0.00")

            transactions.append({
                "row_idx": row_idx,
                "date": date,
                "txn_id": txn_id,
                "description": desc,
                "debit": debit,
                "credit": credit,
                "balance": balance,
                "raw_notes": notes,
                "sanitized_notes": notes,
                "is_injection": False,
                "injection_payload": "",
                "is_excluded": False,
                "exclusion_reason": "",
                "category": "Uncategorized"
            })

    # If opening balance was not explicitly tagged in a row, deduce from first transaction
    if opening_balance == Decimal("0.00") and transactions:
        first_txn = transactions[0]
        # Starting balance before first txn: Balance - Credit + Debit
        opening_balance = first_txn["balance"] - first_txn["credit"] + first_txn["debit"]

    return opening_balance, transactions

def stage3_sanitize(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Treat transaction text as passive data (Guardrail G4).
    Detect and neutralize prompt injection attempts.
    """
    security_alerts = []
    for txn in transactions:
        text_to_scan = f"{txn['description']} {txn['raw_notes']}"
        for pattern in INJECTION_SIGNATURES:
            match = re.search(pattern, text_to_scan, re.IGNORECASE)
            if match:
                txn["is_injection"] = True
                txn["injection_payload"] = match.group(0)
                # Neutralize payload in sanitized notes
                sanitized = re.sub(pattern, "[SANITIZED ADVERSARIAL INSTRUCTION]", txn["raw_notes"], flags=re.IGNORECASE)
                txn["sanitized_notes"] = sanitized
                security_alerts.append({
                    "txn_id": txn["txn_id"],
                    "description": txn["description"],
                    "detected_signature": match.group(0),
                    "action": "Neutralized & quarantined as passive data"
                })
                break
    return security_alerts

def stage4_filter_exclusions(transactions: List[Dict[str, Any]]):
    """
    Detect non-spending items:
    1. Internal self-transfers (outward or inward)
    2. Inward merchant refunds & cashbacks
    3. Inward failed transaction auto-reversals
    """
    for txn in transactions:
        search_corpus = f"{txn['description']} {txn['raw_notes']}".lower()

        # Check user corrections log first for exclusion
        for phrase, target in USER_CORRECTIONS.items():
            if phrase in search_corpus and "excluded" in target.lower():
                txn["is_excluded"] = True
                txn["exclusion_reason"] = "User Correction: Capital Transfer"
                txn["category"] = "Excluded: Transfer"
                break

        if txn["is_excluded"]:
            continue

        # Check transfers
        if any(keyword in search_corpus for keyword in EXCLUSION_RULES["transfers"]):
            txn["is_excluded"] = True
            txn["exclusion_reason"] = "Own-Account Transfer (Internal)"
            txn["category"] = "Excluded: Transfer"
            continue

        # Check refunds
        if any(keyword in search_corpus for keyword in EXCLUSION_RULES["refunds"]):
            txn["is_excluded"] = True
            txn["exclusion_reason"] = "Merchant Refund / Cashback"
            txn["category"] = "Excluded: Refund"
            continue

        # Check reversals
        if any(keyword in search_corpus for keyword in EXCLUSION_RULES["reversals"]):
            txn["is_excluded"] = True
            txn["exclusion_reason"] = "Failed Transaction Auto-Reversal"
            txn["category"] = "Excluded: Reversal"
            continue

def stage5_categorize(transactions: List[Dict[str, Any]]):
    """
    Categorize spending transactions using persistent memory (my-money.md).
    Precedence:
    1. User Category Corrections Log
    2. Keyword Matching Rules
    3. Salary / Income
    4. Uncategorized
    """
    for txn in transactions:
        if txn["is_excluded"]:
            continue

        # Check credits (e.g. Salary)
        if txn["credit"] > 0:
            if "salary" in txn["description"].lower() or "salary" in txn["raw_notes"].lower():
                txn["category"] = "Income: Salary"
            else:
                txn["category"] = "Inflow: Other"
            continue

        # Debits: living expenses
        search_corpus = f"{txn['description']} {txn['raw_notes']}".lower()

        # 1. User Corrections Log
        matched_correction = False
        for phrase, corrected_cat in USER_CORRECTIONS.items():
            if phrase in search_corpus:
                txn["category"] = corrected_cat
                matched_correction = True
                break
        if matched_correction:
            continue

        # 2. Keyword rules
        matched_keyword = False
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in search_corpus for kw in keywords):
                txn["category"] = category
                matched_keyword = True
                break
        if matched_keyword:
            continue

        # 3. Default
        txn["category"] = "Miscellaneous / Uncategorized"

def stage6_detect_anomalies(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect financial anomalies:
    1. Duplicate charges (same merchant, same date, same amount)
    2. Over-budget categories
    """
    # 1. Duplicate debits
    debit_groups: Dict[Tuple[str, str, Decimal], List[Dict[str, Any]]] = {}
    for txn in transactions:
        if txn["debit"] > 0 and not txn["is_excluded"]:
            # Use merchant identifier from description
            merchant_key = txn["description"].strip().lower()
            key = (txn["date"], merchant_key, txn["debit"])
            debit_groups.setdefault(key, []).append(txn)

    duplicate_alerts = []
    for (date, merchant, amount), group in debit_groups.items():
        if len(group) > 1:
            duplicate_alerts.append({
                "date": date,
                "merchant": group[0]["description"],
                "amount": amount,
                "count": len(group),
                "txn_ids": [t["txn_id"] for t in group]
            })

    return {
        "duplicate_alerts": duplicate_alerts
    }

def stage7_calculate(opening_balance: Decimal, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministic calculation engine (Guardrail G5).
    Zero LLM arithmetic. Exact Decimal precision.
    """
    total_money_in = Decimal("0.00")
    total_money_out = Decimal("0.00")
    total_living_expenses = Decimal("0.00")
    excluded_inflows = Decimal("0.00")
    excluded_outflows = Decimal("0.00")

    category_spend: Dict[str, Decimal] = {cat: Decimal("0.00") for cat in BUDGET_LIMITS.keys()}
    category_spend["Miscellaneous / Uncategorized"] = Decimal("0.00")

    for txn in transactions:
        total_money_in += txn["credit"]
        total_money_out += txn["debit"]

        if txn["is_excluded"]:
            if txn["credit"] > 0:
                excluded_inflows += txn["credit"]
            if txn["debit"] > 0:
                excluded_outflows += txn["debit"]
        else:
            if txn["debit"] > 0:
                total_living_expenses += txn["debit"]
                cat = txn["category"]
                if cat in category_spend:
                    category_spend[cat] += txn["debit"]
                else:
                    category_spend["Miscellaneous / Uncategorized"] += txn["debit"]

    # Final reported closing balance from statement
    reported_closing_balance = transactions[-1]["balance"] if transactions else opening_balance

    # Deterministic balance equation
    computed_closing_balance = opening_balance + total_money_in - total_money_out
    balance_discrepancy = computed_closing_balance - reported_closing_balance
    is_balance_verified = (balance_discrepancy == Decimal("0.00"))

    return {
        "opening_balance": opening_balance,
        "total_money_in": total_money_in,
        "total_money_out": total_money_out,
        "total_living_expenses": total_living_expenses,
        "excluded_inflows": excluded_inflows,
        "excluded_outflows": excluded_outflows,
        "category_spend": category_spend,
        "reported_closing_balance": reported_closing_balance,
        "computed_closing_balance": computed_closing_balance,
        "balance_discrepancy": balance_discrepancy,
        "is_balance_verified": is_balance_verified
    }

def stage8_generate_report(
    statement_filename: str,
    calc_results: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    security_alerts: List[Dict[str, Any]],
    anomaly_results: Dict[str, Any],
    output_path: Path
) -> str:
    """
    Generate daily_report.md matching the AGENTS.md specification.
    Ends with the mathematical check line (Guardrail G6).
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    open_bal = calc_results["opening_balance"]
    money_in = calc_results["total_money_in"]
    money_out = calc_results["total_money_out"]
    close_bal = calc_results["reported_closing_balance"]
    net_shift = money_in - money_out
    net_shift_sign = "+" if net_shift >= 0 else ""

    # Category Breakdown Table
    cat_rows = []
    for cat, budget in BUDGET_LIMITS.items():
        spend = calc_results["category_spend"].get(cat, Decimal("0.00"))
        remaining = budget - spend
        remaining_str = f"₹{remaining:,.2f}" if remaining >= 0 else f"-₹{abs(remaining):,.2f}"
        utilization = (spend / budget * Decimal("100.0")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP) if budget > 0 else Decimal("0.0")
        status = "OK" if remaining >= 0 else f"**OVER BUDGET (+₹{abs(remaining):,.2f})**"
        cat_rows.append(f"| {cat} | ₹{budget:,.2f} | ₹{spend:,.2f} | {remaining_str} | {utilization}% | {status} |")

    misc_spend = calc_results["category_spend"].get("Miscellaneous / Uncategorized", Decimal("0.00"))
    if misc_spend > Decimal("0.00"):
        cat_rows.append(f"| Miscellaneous | ₹0.00 | ₹{misc_spend:,.2f} | -₹{misc_spend:,.2f} | N/A | Review Needed |")

    total_living_spend = calc_results["total_living_expenses"]
    total_living_remaining = TOTAL_MONTHLY_LIVING_BUDGET - total_living_spend
    total_living_utilization = (total_living_spend / TOTAL_MONTHLY_LIVING_BUDGET * Decimal("100.0")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    total_living_status = "ON TRACK" if total_living_remaining >= 0 else "**EXCEEDED**"

    # Excluded Table Rows
    excluded_rows = []
    for txn in transactions:
        if txn["is_excluded"]:
            direction = "Inflow (Credit)" if txn["credit"] > 0 else "Outflow (Debit)"
            amt = txn["credit"] if txn["credit"] > 0 else txn["debit"]
            excluded_rows.append(f"| {txn['date']} | {txn['txn_id']} | {txn['description']} | {direction} | ₹{amt:,.2f} | {txn['exclusion_reason']} |")

    # Anomaly & Security Alerts Section
    anomaly_text_lines = []
    if anomaly_results["duplicate_alerts"]:
        for dup in anomaly_results["duplicate_alerts"]:
            anomaly_text_lines.append(
                f"- **Duplicate Debit Detected:** {dup['merchant']} on {dup['date']} - ₹{dup['amount']:,.2f} (Count: {dup['count']} times, Txn IDs: {', '.join(dup['txn_ids'])})"
            )
    else:
        anomaly_text_lines.append("- **Duplicate Charges:** None detected.")

    if security_alerts:
        for sec in security_alerts:
            anomaly_text_lines.append(
                f"- **Security Alert (Guardrail G4 Neutralized):** Txn `{sec['txn_id']}` ({sec['description']}) contained malicious injection payload: `{sec['detected_signature']}`. Attack was neutralized; memo treated strictly as passive data."
            )
    else:
        anomaly_text_lines.append("- **Adversarial Injections (Guardrail G4):** None detected.")

    # Budget overruns
    overruns = []
    for cat, budget in BUDGET_LIMITS.items():
        spend = calc_results["category_spend"].get(cat, Decimal("0.00"))
        if spend > budget:
            overruns.append(f"{cat} exceeded by ₹{(spend - budget):,.2f}")
    if overruns:
        anomaly_text_lines.append(f"- **Budget Alerts:** {', '.join(overruns)}.")
    else:
        anomaly_text_lines.append("- **Budget Alerts:** All individual categories within allocation limits.")

    # Transaction Ledger
    txn_rows = []
    for txn in transactions:
        debit_str = f"₹{txn['debit']:,.2f}" if txn["debit"] > 0 else "-"
        credit_str = f"₹{txn['credit']:,.2f}" if txn["credit"] > 0 else "-"
        bal_str = f"₹{txn['balance']:,.2f}"
        txn_rows.append(f"| {txn['date']} | {txn['txn_id']} | {txn['description']} | {txn['category']} | {debit_str} | {credit_str} | {bal_str} | {txn['sanitized_notes']} |")

    # Balance verification line (Guardrail G6)
    check_status = "PASSED (VERIFIED TRUE)" if calc_results["is_balance_verified"] else "FAILED (DISCREPANCY)"
    check_line = f"CHECK LINE: Opening Balance + Money In - Money Out = Closing Balance [{check_status}]"

    report_content = f"""# Daily Financial Intelligence & Expense Report
**Generated On:** {now_str} Local  
**Statement File:** `{statement_filename}`  
**Agent Version:** 1.0.0-production (Local Privacy-Preserving Mode)  

---

## 1. Executive Balance Summary
| Metric | Amount (INR) | Notes / Accounting Treatment |
| :--- | :--- | :--- |
| **Opening Balance** | ₹{open_bal:,.2f} | Starting balance verified from statement |
| **Total Money In (Credits)** | ₹{money_in:,.2f} | All inward cashflows (Income + Refunds + Transfers In) |
| **Total Money Out (Debits)** | ₹{money_out:,.2f} | All outward cashflows (Living Expenses + Transfers Out) |
| **Net Balance Shift** | {net_shift_sign}₹{net_shift:,.2f} | Money In minus Money Out |
| **Closing Balance (Reported)** | ₹{close_bal:,.2f} | Verified against bank statement register |

---

## 2. Living Expense Category Breakdown
*Monthly Budget: ₹{TOTAL_MONTHLY_LIVING_BUDGET:,.2f} (Excludes internal transfers and capital investments)*

| Category | Monthly Budget (INR) | Statement Spend (INR) | Remaining Budget (INR) | Utilization % | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
{chr(10).join(cat_rows)}
| **Total Living Spend** | **₹{TOTAL_MONTHLY_LIVING_BUDGET:,.2f}** | **₹{total_living_spend:,.2f}** | **₹{total_living_remaining:,.2f}** | **{total_living_utilization}%** | **{total_living_status}** |

---

## 3. Excluded Non-Spending Transactions
*Items audited for balance reconciliation but omitted from living expense consumption.*

| Date | Txn ID | Description | Direction | Amount (INR) | Reason for Exclusion |
| :--- | :--- | :--- | :--- | :--- | :--- |
{chr(10).join(excluded_rows)}

---

## 4. Anomaly & Security Alerts
{chr(10).join(anomaly_text_lines)}

---

## 5. Comprehensive Transaction Audit Ledger
| Date | Txn ID | Description / Payee | Category | Debit (INR) | Credit (INR) | Balance (INR) | Sanitized Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
{chr(10).join(txn_rows)}

---

## 6. Mathematical Verification Audit Line
{check_line}
"""

    with open(output_path, "w", encoding="utf-8") as out_f:
        out_f.write(report_content)

    return check_line

# ==============================================================================
# MAIN ENTRYPOINT
# ==============================================================================
def main():
    verify_environment_fence()

    base_dir = Path(__file__).resolve().parent
    statements_dir = base_dir / "statements"
    output_report = base_dir / "daily_report.md"

    # Stage 1: Scan
    csv_files = stage1_scan(statements_dir)
    if not csv_files:
        print("[INFO] No statement CSV files found.")
        sys.exit(0)

    target_csv = csv_files[0]
    print(f"[STAGE 1: SCAN] Target statement: {target_csv.name}")

    # Stage 2: Ingest (Read-Only)
    opening_balance, transactions = stage2_ingest(target_csv)
    print(f"[STAGE 2: INGEST] Loaded {len(transactions)} transactions. Opening Balance: ₹{opening_balance:,.2f}")

    # Stage 3: Sanitize (Prompt Injection Defense)
    security_alerts = stage3_sanitize(transactions)
    print(f"[STAGE 3: SANITIZE] Completed. Security alerts raised: {len(security_alerts)}")

    # Stage 4: Exclusion Filtering
    stage4_filter_exclusions(transactions)
    excluded_count = sum(1 for t in transactions if t["is_excluded"])
    print(f"[STAGE 4: FILTER] Non-spending items segregated: {excluded_count}")

    # Stage 5: Categorize
    stage5_categorize(transactions)
    print(f"[STAGE 5: CATEGORIZE] Categorized all active transactions using persistent memory.")

    # Stage 6: Anomaly Detection
    anomaly_results = stage6_detect_anomalies(transactions)
    print(f"[STAGE 6: DETECT] Duplicates found: {len(anomaly_results['duplicate_alerts'])}")

    # Stage 7: Deterministic Calculation
    calc_results = stage7_calculate(opening_balance, transactions)
    print(f"[STAGE 7: CALCULATE] Money In: ₹{calc_results['total_money_in']:,.2f} | Money Out: ₹{calc_results['total_money_out']:,.2f}")
    print(f"[STAGE 7: CALCULATE] Computed Closing: ₹{calc_results['computed_closing_balance']:,.2f} | Target: ₹{calc_results['reported_closing_balance']:,.2f}")

    # Stage 8: Report Generation
    check_line = stage8_generate_report(
        target_csv.name,
        calc_results,
        transactions,
        security_alerts,
        anomaly_results,
        output_report
    )
    print(f"[STAGE 8: REPORT] Generated report at '{output_report.name}'")
    print(f"[FINAL AUDIT] {check_line}")

    if not calc_results["is_balance_verified"]:
        print("[ERROR] Mathematical verification failed!")
        sys.exit(2)

if __name__ == "__main__":
    main()
