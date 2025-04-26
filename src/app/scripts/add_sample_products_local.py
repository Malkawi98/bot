#!/usr/bin/env python
"""
Script to add sample products to the database for testing the product management feature.
Includes products in both English and Arabic to support multilingual requirements.
"""
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent.parent
sys.path.append(str(src_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.models.product import Product
from datetime import datetime

# Create a direct connection to the database
DATABASE_URL = "postgresql://user:pass@localhost:5432/db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Sample products in English
english_products = [
    {
        "name": "Smartphone X Pro",
        "description": "Latest smartphone with advanced camera and long battery life",
        "price": 799.99,
        "currency": "USD",
        "stock_quantity": 25,
        "category": "Electronics",
        "language": "en"
    },
    {
        "name": "Wireless Noise-Cancelling Headphones",
        "description": "Premium headphones with active noise cancellation",
        "price": 249.99,
        "currency": "USD",
        "stock_quantity": 15,
        "category": "Electronics",
        "language": "en"
    },
    {
        "name": "Cotton T-Shirt",
        "description": "Comfortable 100% cotton t-shirt",
        "price": 24.99,
        "currency": "USD",
        "stock_quantity": 100,
        "category": "Clothing",
        "language": "en"
    },
    {
        "name": "Smart Watch",
        "description": "Fitness tracker and smartwatch with heart rate monitoring",
        "price": 199.99,
        "currency": "USD",
        "stock_quantity": 0,  # Out of stock
        "category": "Electronics",
        "language": "en"
    }
]

# Sample products in Arabic
arabic_products = [
    {
        "name": "هاتف ذكي برو",
        "description": "أحدث هاتف ذكي مع كاميرا متطورة وعمر بطارية طويل",
        "price": 799.99,
        "currency": "USD",
        "stock_quantity": 20,
        "category": "Electronics",
        "language": "ar"
    },
    {
        "name": "سماعات لاسلكية مانعة للضوضاء",
        "description": "سماعات رأس متميزة مع إلغاء الضوضاء النشط",
        "price": 249.99,
        "currency": "USD",
        "stock_quantity": 10,
        "category": "Electronics",
        "language": "ar"
    },
    {
        "name": "قميص قطني",
        "description": "قميص مريح من القطن 100%",
        "price": 24.99,
        "currency": "USD",
        "stock_quantity": 80,
        "category": "Clothing",
        "language": "ar"
    },
    {
        "name": "ساعة ذكية",
        "description": "جهاز تتبع اللياقة البدنية وساعة ذكية مع مراقبة معدل ضربات القلب",
        "price": 199.99,
        "currency": "USD",
        "stock_quantity": 0,  # Out of stock
        "category": "Electronics",
        "language": "ar"
    }
]

def add_sample_products():
    """Add sample products to the database."""
    db = SessionLocal()
    try:
        # Check if products already exist
        existing_count = db.query(Product).count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} products. Skipping sample data creation.")
            return
        
        # Add English products
        for product_data in english_products:
            product = Product()
            product.name = product_data['name']
            product.description = product_data['description']
            product.price = product_data['price']
            product.currency = product_data['currency']
            product.stock_quantity = product_data['stock_quantity']
            product.category = product_data['category']
            product.language = product_data['language']
            product.is_active = True
            product.created_at = datetime.now().isoformat()
            product.updated_at = datetime.now().isoformat()
            db.add(product)
        
        # Add Arabic products
        for product_data in arabic_products:
            product = Product()
            product.name = product_data['name']
            product.description = product_data['description']
            product.price = product_data['price']
            product.currency = product_data['currency']
            product.stock_quantity = product_data['stock_quantity']
            product.category = product_data['category']
            product.language = product_data['language']
            product.is_active = True
            product.created_at = datetime.now().isoformat()
            product.updated_at = datetime.now().isoformat()
            db.add(product)
        
        # Set up alternative product relationships
        # After committing to get IDs
        db.commit()
        
        # Get products to set up alternatives
        en_smartphone = db.query(Product).filter(Product.name == "Smartphone X Pro").first()
        ar_smartphone = db.query(Product).filter(Product.name == "هاتف ذكي برو").first()
        
        en_headphones = db.query(Product).filter(Product.name == "Wireless Noise-Cancelling Headphones").first()
        ar_headphones = db.query(Product).filter(Product.name == "سماعات لاسلكية مانعة للضوضاء").first()
        
        en_tshirt = db.query(Product).filter(Product.name == "Cotton T-Shirt").first()
        ar_tshirt = db.query(Product).filter(Product.name == "قميص قطني").first()
        
        en_watch = db.query(Product).filter(Product.name == "Smart Watch").first()
        ar_watch = db.query(Product).filter(Product.name == "ساعة ذكية").first()
        
        # Set alternatives (English -> Arabic)
        if en_smartphone and ar_smartphone:
            ar_smartphone.alternative_to_id = en_smartphone.id
        
        if en_headphones and ar_headphones:
            ar_headphones.alternative_to_id = en_headphones.id
        
        if en_tshirt and ar_tshirt:
            ar_tshirt.alternative_to_id = en_tshirt.id
        
        if en_watch and ar_watch:
            ar_watch.alternative_to_id = en_watch.id
        
        db.commit()
        print(f"Successfully added {len(english_products) + len(arabic_products)} sample products to the database.")
        
    except Exception as e:
        db.rollback()
        print(f"Error adding sample products: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_products()
