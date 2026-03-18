from __future__ import annotations

from typing import Dict, Optional


SCHEMA_REGISTRY: Dict[str, Dict] = {
    "hr_demo": {
        "tables": {
            "dbo.Employees": [
                "EmployeeID",
                "Status",
                "HireDate",
                "FirstName",
                "LastName",
                "Department",
                "Title",
                "EmailAddress",
            ],
            "dbo.Departments": [
                "DepartmentID",
                "DepartmentName",
                "Status",
                "CreatedDate",
            ],
        }
    },
    "time_demo": {
        "tables": {
            "dbo.TimeEntries": [
                "TimeEntryID",
                "EmployeeID",
                "WorkDate",
                "HoursWorked",
                "Status",
            ]
        }
    },
}


def get_schema_by_name(schema_name: Optional[str]) -> Optional[Dict]:
    if not schema_name:
        return None
    return SCHEMA_REGISTRY.get(schema_name)