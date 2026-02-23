from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


DEFAULT_TOP_N = 100

SENSITIVE_COLUMN_HINTS = {
    "password", "passwd", "ssn", "social", "dob", "birth", "email", "mail", "phone", "mobile"
}


@dataclass
class SQLPlan:
    dialect: str
    query: str
    assumptions: List[str]
    safety_notes: List[str]
    suggested_next_inputs: List[str]


def _load_schema(schema_path: Optional[str]) -> Optional[Dict]:
    if not schema_path:
        return None
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_sensitive(col: str) -> bool:
    c = col.lower()
    return any(hint in c for hint in SENSITIVE_COLUMN_HINTS)


def _choose_table(text: str, schema: Optional[Dict]) -> Tuple[str, List[str]]:
    """
    Schema format:
    {
      "tables": {
        "dbo.Employees": ["EmployeeID","Status","HireDate","FirstName","LastName","EmailAddress"],
        ...
      }
    }
    """
    if not schema or "tables" not in schema:
        return "dbo.YourTable", ["*"]

    tables: Dict[str, List[str]] = schema["tables"]
    t = text.lower()

    candidates: List[str] = []
    for table_name in tables.keys():
        name_l = table_name.lower()
        if "employee" in t and "employee" in name_l:
            candidates.append(table_name)
        elif "department" in t and ("department" in name_l or "dept" in name_l):
            candidates.append(table_name)
        elif "time" in t and ("time" in name_l or "labor" in name_l):
            candidates.append(table_name)

    table = candidates[0] if candidates else list(tables.keys())[0]
    cols = tables.get(table) or ["*"]
    return table, cols


def _pick_date_column(cols: List[str]) -> Optional[str]:
    for preferred in ["CreatedDate", "CreateDate", "HireDate", "EffectiveDate", "EFFDT"]:
        if preferred in cols:
            return preferred
    for c in cols:
        if "date" in c.lower():
            return c
    return None


def _build_where(text: str, cols: List[str]) -> str:
    t = text.lower()
    clauses: List[str] = []

    status_col = next((c for c in cols if c.lower() in {"status", "empstatus", "empl_status"}), None)
    if "active" in t and status_col:
        clauses.append(f"{status_col} = 'ACTIVE'")

    if "last 90 days" in t or "past 90 days" in t:
        dt_col = _pick_date_column(cols)
        if dt_col:
            clauses.append(f"{dt_col} >= DATEADD(DAY, -90, GETDATE())")

    if not clauses:
        return ""

    return "WHERE " + " AND ".join(clauses)


def generate_safe_sql(
    user_text: str,
    top_n: int = DEFAULT_TOP_N,
    schema_path: Optional[str] = None,
) -> SQLPlan:
    """
    Schema-aware MVP-safe SQL Server generator:
    - Read-only SELECT
    - TOP (N) guardrail
    - Optional schema file for better table/column selection
    """
    schema = _load_schema(schema_path)
    table, cols = _choose_table(user_text, schema)

    # Choose columns
    if cols == ["*"]:
        select_cols = ["*"]
    else:
        safe_cols = [c for c in cols if not _is_sensitive(c)]
        if len(safe_cols) > 12:
            safe_cols = safe_cols[:12]
        select_cols = safe_cols if safe_cols else ["*"]

    where_clause = "" if cols == ["*"] else _build_where(user_text, cols)
    select_list = ",\n    ".join(select_cols)

    query = f"""SELECT TOP ({int(top_n)})
    {select_list}
FROM {table}
{where_clause}
;""".strip()

    assumptions = [
        "This is a draft SQL Server query intended for review (not execution).",
        f"Row limiting is applied by default (TOP {top_n}) as a guardrail.",
    ]
    if schema_path:
        assumptions.append(f"Schema guidance loaded from: {schema_path}")
    else:
        assumptions.append("No schema file provided; table/columns may be placeholders.")

    safety_notes = [
        f"Read-only SELECT query with TOP ({top_n}) row limit applied.",
        "Avoid selecting sensitive columns (SSN, passwords, personal contact info).",
        "Confirm indexing and filters before running against production tables.",
    ]

    suggested_next_inputs = [
        "Confirm the correct table(s) and key columns for your environment.",
        "Provide exact status codes and date fields used in your system.",
        "Specify ordering and expected row volume (for performance planning).",
    ]

    return SQLPlan(
        dialect="sqlserver",
        query=query,
        assumptions=assumptions,
        safety_notes=safety_notes,
        suggested_next_inputs=suggested_next_inputs,
    )