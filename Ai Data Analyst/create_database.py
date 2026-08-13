import sqlite3

conn = sqlite3.connect("amazon.db")
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_keys = ON")

# Clean start
cursor.execute("DROP TABLE IF EXISTS order_items")
cursor.execute("DROP TABLE IF EXISTS orders")
cursor.execute("DROP TABLE IF EXISTS products")
cursor.execute("DROP TABLE IF EXISTS customers")

print("✅ Old tables removed")

# Create Tables
cursor.execute("""
CREATE TABLE customers(
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    city TEXT,
    join_date TEXT
)
""")

cursor.execute("""
CREATE TABLE products(
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT,
    price REAL NOT NULL
)
""")

cursor.execute("""
CREATE TABLE orders(
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    order_date TEXT,
    total_amount REAL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
)
""")

cursor.execute("""
CREATE TABLE order_items(
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER NOT NULL,
    subtotal REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
)
""")

print("✅ Tables created successfully!")

# ====================== REALISTIC DATA ======================
customers_data = [
    ("Alice Johnson", "alice.j@example.com", "New York", "2023-01-15"),
    ("Bob Smith", "bob.s@example.com", "London", "2023-03-20"),
    ("Carol Davis", "carol.d@example.com", "Sydney", "2023-06-10"),
    ("David Wilson", "david.w@example.com", "Toronto", "2023-09-05"),
    ("Eve Brown", "eve.b@example.com", "Lahore", "2024-01-12")
]
cursor.executemany("INSERT INTO customers (name, email, city, join_date) VALUES (?, ?, ?, ?)", customers_data)

products_data = [
    ("Smartphone X", "Electronics", 699.99),
    ("Laptop Pro", "Electronics", 1299.99),
    ("Wireless Headphones", "Electronics", 199.99),
    ("Python Programming Guide", "Books", 24.99),
    ("Cotton T-Shirt", "Clothing", 19.99),
    ("Slim Fit Jeans", "Clothing", 49.99),
    ("Coffee Maker", "Home & Kitchen", 89.99),
    ("Blender", "Home & Kitchen", 59.99)
]
cursor.executemany("INSERT INTO products (name, category, price) VALUES (?, ?, ?)", products_data)

# Orders with realistic totals (multiple items each)
orders_data = [
    (1, "2024-02-01", 939.96),   # Alice - 3 items
    (2, "2024-02-15", 1499.98),  # Bob - 2 items
    (3, "2024-03-01", 119.96),   # Carol - 3 items
    (4, "2024-02-20", 174.97),   # David - 3 items
    (5, "2024-03-10", 259.94)    # Eve (Lahore) - 4 items
]
cursor.executemany("INSERT INTO orders (customer_id, order_date, total_amount) VALUES (?, ?, ?)", orders_data)

# Order Items - Multiple products per order + some quantity > 1
order_items_data = [
    # Order 1: Alice
    (1, 1, 1, 699.99),   # Smartphone X
    (1, 3, 1, 199.99),   # Wireless Headphones
    (1, 5, 2, 39.98),    # 2 × Cotton T-Shirt

    # Order 2: Bob
    (2, 2, 1, 1299.99),  # Laptop Pro
    (2, 3, 1, 199.99),   # Wireless Headphones

    # Order 3: Carol
    (3, 4, 2, 49.98),    # 2 × Python Book
    (3, 5, 1, 19.99),    # Cotton T-Shirt
    (3, 6, 1, 49.99),    # Slim Fit Jeans

    # Order 4: David
    (4, 8, 1, 59.99),    # Blender
    (4, 7, 1, 89.99),    # Coffee Maker
    (4, 4, 1, 24.99),    # Python Book

    # Order 5: Eve from Lahore (most items)
    (5, 6, 1, 49.99),    # Slim Fit Jeans
    (5, 7, 1, 89.99),    # Coffee Maker
    (5, 5, 3, 59.97),    # 3 × Cotton T-Shirt
    (5, 8, 1, 59.99)     # Blender
]
cursor.executemany("INSERT INTO order_items (order_id, product_id, quantity, subtotal) VALUES (?, ?, ?, ?)", order_items_data)

conn.commit()

# Show summary
cursor.execute("SELECT COUNT(*) FROM customers"); print(f"Customers     : {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM products");  print(f"Products      : {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM orders");    print(f"Orders        : {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM order_items"); print(f"Order Items   : {cursor.fetchone()[0]}")

conn.close()

print("\n🎉 SUCCESS! amazon.db is now ready with REALISTIC data.")