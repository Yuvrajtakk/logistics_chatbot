import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

ALLOWED_TABLES = {
    "olist_customers_dataset",
    "olist_orders_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_order_reviews_dataset",
    "olist_products_dataset",
    "olist_sellers_dataset",
    "olist_geolocation_dataset",
    "product_category_name_translation",
}

MAX_ROWS = 1000


class ValidationError(Exception):
    pass


def validate_sql(sql: str) -> str:
    try:
        tree = sqlglot.parse_one(sql)
    except ParseError as e:
        # sqlglot couldn't parse the string at all -- it's not valid SQL.
        # Re-raise as ValidationError so every caller sees a consistent
        # exception type. This catches REFUSE: responses from the LLM too,
        # but run_sql_pipeline() checks for REFUSE before calling here.
        raise ValidationError(f"SQL parsing failed: {e}")

    if not isinstance(tree, exp.Select):
        raise ValidationError(f"Only SELECT statements are allowed, got {type(tree).__name__}")

    cte_names = {cte.alias for cte in tree.find_all(exp.CTE)}

    tables_used = {t.name for t in tree.find_all(exp.Table)}
    tables_used -= cte_names

    disallowed = tables_used - ALLOWED_TABLES
    if disallowed:
        raise ValidationError(f"Query touches disallowed table(s): {disallowed}")

    tree = tree.limit(MAX_ROWS)

    return tree.sql()