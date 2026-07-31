import sqlglot

sql = "SELECT order_id FROM olist_orders_dataset"
tree = sqlglot.parse_one(sql)
print(isinstance(tree, sqlglot.exp.Select))
print([t.name for t in tree.find_all(sqlglot.exp.Table)])

bad_sql = "DELETE FROM olist_orders_dataset WHERE order_id = '123'"
bad_tree = sqlglot.parse_one(bad_sql)
print(isinstance(bad_tree, sqlglot.exp.Select))
print(type(bad_tree))

join_sql = "SELECT o.order_id FROM olist_orders_dataset o JOIN olist_order_items_dataset i ON o.order_id = i.order_id"
join_tree = sqlglot.parse_one(join_sql)
print([t.name for t in join_tree.find_all(sqlglot.exp.Table)])

from validator import validate_sql, ValidationError

tests = [
    "SELECT order_id FROM olist_orders_dataset",
    "DELETE FROM olist_orders_dataset WHERE order_id = '123'",
    "SELECT * FROM secret_table",
    "SELECT o.order_id FROM olist_orders_dataset o JOIN olist_order_items_dataset i ON o.order_id = i.order_id",
]

for sql in tests:
    try:
        print("OK:", validate_sql(sql))
    except ValidationError as e:
        print("BLOCKED:", e)