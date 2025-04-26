# Enhanced FAQ database with more detailed information
FAQS = {
    "shipping": "We offer free shipping on orders over $50. Standard shipping takes 3-5 business days. Express shipping is available for $9.99 and delivers within 1-2 business days. International shipping varies by country.",
    "return": "You can return any item within 30 days for a full refund. Returns are free if the item is defective or we made a mistake. Otherwise, a $5 return shipping fee applies. Gift returns receive store credit.",
    "payment": "We accept Visa, MasterCard, American Express, Discover, PayPal, Apple Pay, and Google Pay. All transactions are secure and encrypted. We also offer financing options for purchases over $200.",
    "warranty": "All electronics come with a 1-year manufacturer warranty. Extended warranties are available for purchase. Warranty claims require proof of purchase and the original packaging if possible.",
    "price_match": "We offer price matching on identical items from major retailers. Price match requests must be made within 14 days of purchase and require proof of the competitor's current price.",
    "bulk_orders": "Discounts are available for bulk orders of 10+ items. Contact our sales team for a custom quote. Corporate accounts receive additional benefits and dedicated support.",
    "membership": "Our premium membership costs $49/year and includes free shipping on all orders, exclusive discounts, early access to sales, and extended return periods of 60 days.",
}

# Expanded product catalog with more details
PRODUCTS = [
    {"id": "p001", "name": "Wireless Earbuds", "price": 49.99, "category": "Audio", "rating": 4.5, "stock": 120},
    {"id": "p002", "name": "Smart Watch", "price": 129.99, "category": "Wearables", "rating": 4.3, "stock": 85},
    {"id": "p003", "name": "Bluetooth Speaker", "price": 39.99, "category": "Audio", "rating": 4.7, "stock": 200},
    {"id": "p004", "name": "Portable Charger", "price": 19.99, "category": "Accessories", "rating": 4.4, "stock": 300},
    {"id": "p005", "name": "Fitness Tracker", "price": 59.99, "category": "Wearables", "rating": 4.1, "stock": 75},
    {"id": "p006", "name": "Wireless Headphones", "price": 89.99, "category": "Audio", "rating": 4.6, "stock": 95},
    {"id": "p007", "name": "Smart Home Hub", "price": 129.99, "category": "Smart Home", "rating": 4.2, "stock": 60},
    {"id": "p008", "name": "Tablet", "price": 199.99, "category": "Computing", "rating": 4.5, "stock": 40},
    {"id": "p009", "name": "Wireless Keyboard", "price": 49.99, "category": "Computing", "rating": 4.3, "stock": 110},
    {"id": "p010", "name": "Smartphone", "price": 499.99, "category": "Mobile", "rating": 4.8, "stock": 25},
]

# Order status data
ORDER_STATUSES = {
    "ORD12345": {
        "status": "Shipped",
        "order_date": "2025-04-20",
        "estimated_delivery": "2025-04-28",
        "items": ["Wireless Earbuds", "Portable Charger"]
    },
    "ORD67890": {
        "status": "Processing",
        "order_date": "2025-04-25",
        "estimated_delivery": "2025-05-02",
        "items": ["Smart Watch", "Fitness Tracker"]
    },
    "ORD54321": {
        "status": "Delivered",
        "order_date": "2025-04-15",
        "estimated_delivery": "2025-04-22",
        "items": ["Bluetooth Speaker"]
    }
}
