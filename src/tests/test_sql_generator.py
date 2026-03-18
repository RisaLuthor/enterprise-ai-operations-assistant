from src.services.sql_generator import generate_safe_sql


def test_generate_safe_sql_returns_select():
    plan = generate_safe_sql(
        user_text="Show active employees from the last 90 days",
        top_n=25,
        schema_name="hr_demo",
    )
    assert "SELECT TOP (25)" in plan.query
    assert "FROM dbo.Employees" in plan.query
    assert "WHERE" in plan.query


def test_sensitive_columns_filtered():
    plan = generate_safe_sql(
        user_text="Show employees",
        top_n=10,
        schema_name="hr_demo",
    )
    assert "EmailAddress" not in plan.query


def test_placeholder_used_when_no_schema():
    plan = generate_safe_sql(
        user_text="Show employees",
        top_n=10,
        schema_name=None,
    )
    assert "dbo.YourTable" in plan.query