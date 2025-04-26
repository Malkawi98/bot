from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.db.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, ProductList
from app.services.product import ProductService
from app.services.product_embedding import ProductEmbeddingService
from app.api.deps import get_current_user

router = APIRouter(tags=["products"])


@router.post("/products", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    """Create a new product."""
    try:
        product_service = ProductService(db)
        db_product = product_service.create_product(product)
        
        # Manually create the response dictionary with empty alternatives
        response_dict = {
            "id": db_product.id,
            "name": db_product.name,
            "description": db_product.description,
            "price": db_product.price,
            "currency": db_product.currency,
            "stock_quantity": db_product.stock_quantity,
            "image_url": db_product.image_url,
            "category": db_product.category,
            "language": db_product.language,
            "is_active": db_product.is_active,
            "created_at": db_product.created_at,
            "updated_at": db_product.updated_at,
            "alternative_to_id": db_product.alternative_to_id,
            "alternatives": []  # Always set alternatives to empty list
        }
        
        # Create a ProductResponse from the dictionary
        return ProductResponse.model_validate(response_dict)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in create_product: {str(e)}\n{error_trace}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error creating product: {str(e)}"},
        )


@router.get("/products")
def get_products(
    skip: int = 0,
    limit: int = 10,
    category: Optional[str] = None,
    language: Optional[str] = Query(None, description="Filter by language (e.g., 'en', 'ar')"),
    search: Optional[str] = Query(None, description="Search term for product name or description"),
    db: Session = Depends(get_db)
):
    """Get a list of products with optional filtering and search."""
    try:
        print(f"DEBUG: Initializing ProductService with db: {db}")
        product_service = ProductService(db)
        
        print(f"DEBUG: Getting products with skip={skip}, limit={limit}, category={category}, language={language}")
        # Get products with filtering
        products = product_service.get_products(skip, limit, category, language)
        print(f"DEBUG: Retrieved {len(products) if products else 0} products")
        
        total = product_service.get_product_count(category, language)
        print(f"DEBUG: Total product count: {total}")
        
        # If search term is provided, use the ProductEmbeddingService for better search
        if search and search.strip():
            search_term = search.lower().strip()
            print(f"DEBUG: Searching products with term: {search_term}")
            
            # Use the ProductEmbeddingService for more advanced search
            try:
                embedding_service = ProductEmbeddingService(db)
                search_results = embedding_service.search_products(
                    query=search_term,
                    top_k=limit,
                    language=language
                )
                
                if search_results:
                    print(f"DEBUG: Found {len(search_results)} products via embedding search")
                    
                    # Get the product IDs from the search results
                    product_ids = [result.get('product_id') for result in search_results if result.get('product_id')]
                    
                    # Fetch the actual product objects from the database
                    if product_ids:
                        products = product_service.get_products_by_ids(product_ids)
                        total = len(products)
                    else:
                        products = []
                        total = 0
                else:
                    # Fallback to simple search if embedding search returns no results
                    filtered_products = [p for p in products if 
                                        search_term in p.name.lower() or 
                                        (p.description and search_term in p.description.lower())]
                    total = len(filtered_products)
                    products = filtered_products
            except Exception as search_error:
                print(f"DEBUG: Error in embedding search: {search_error}, falling back to simple search")
                # Fallback to simple search
                filtered_products = [p for p in products if 
                                    search_term in p.name.lower() or 
                                    (p.description and search_term in p.description.lower())]
                total = len(filtered_products)
                products = filtered_products
                
            print(f"DEBUG: After search, {len(products)} products remain")
        
        # Manually convert products to dictionaries with proper structure
        product_dicts = []
        for p in products:
            product_dict = {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "currency": p.currency,
                "stock_quantity": p.stock_quantity,
                "image_url": p.image_url,
                "category": p.category,
                "language": p.language,
                "is_active": p.is_active,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "alternative_to_id": p.alternative_to_id,
                "alternatives": []  # Always set alternatives to empty list
            }
            product_dicts.append(product_dict)
        
        return {
            "total": total,
            "products": product_dicts
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in get_products: {str(e)}\n{error_trace}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving products: {str(e)}"},
        )


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Get a product by ID."""
    try:
        product_service = ProductService(db)
        db_product = product_service.get_product(product_id)
        
        if db_product is None:
            return JSONResponse(
                status_code=404,
                content={"detail": "Product not found"}
            )
        
        # Get alternatives for this product
        alternatives = product_service.get_product_alternatives(product_id)
        
        # Create response with alternatives
        response = ProductResponse.model_validate(db_product)
        response.alternatives = alternatives
        
        return response
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error retrieving product: {str(e)}"}
        )


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing product."""
    product_service = ProductService(db)
    db_product = product_service.update_product(product_id, product_update)
    
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return db_product


@router.delete("/products/{product_id}", response_model=dict)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Soft delete a product."""
    product_service = ProductService(db)
    success = product_service.delete_product(product_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"success": True, "message": "Product deleted successfully"}
