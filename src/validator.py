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
    """Exception raised when SQL validation fails."""
    pass


def validate_sql(sql: str) -> str:
    """
    Validates a SQL string by parsing its AST using sqlglot.
    Checks that it's a SELECT statement and only touches allowed tables.
    Also appends a LIMIT clause to cap result sizes.

    Args:
        sql (str): The raw SQL query.
        
    Returns:
        str: The validated and limited SQL query.
        
    Raises:
        ValidationError: If the query fails structural or allow-list checks.
    """
    try:
        tree = sqlglot.parse_one(sql)
    except ParseError as e:
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