from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["order"])

class OrderStatusResponse(BaseModel):
    order_id: int
    status: str
    status_description: str
    tracking_number: str
    estimated_delivery: str | None

# Mock data for orders 1–6
MOCK_ORDERS = {
    1: {
        "status": "Processing",
        "status_description": "Your order is being processed.",
        "tracking_number": "TRK10001",
        "estimated_delivery": "2024-06-10"
    },
    2: {
        "status": "Shipped",
        "status_description": "Your order has been shipped.",
        "tracking_number": "TRK10002",
        "estimated_delivery": "2024-06-11"
    },
    3: {
        "status": "Delivered",
        "status_description": "Your order was delivered.",
        "tracking_number": "TRK10003",
        "estimated_delivery": "2024-06-05"
    },
    4: {
        "status": "Cancelled",
        "status_description": "Your order was cancelled.",
        "tracking_number": "TRK10004",
        "estimated_delivery": None
    },
    5: {
        "status": "Returned",
        "status_description": "Your order was returned.",
        "tracking_number": "TRK10005",
        "estimated_delivery": None
    },
    6: {
        "status": "Delayed",
        "status_description": "Your order is delayed.",
        "tracking_number": "TRK10006",
        "estimated_delivery": "2024-06-15"
    }
}

@router.get("/order/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(order_id: int):
    if order_id in MOCK_ORDERS:
        order = MOCK_ORDERS[order_id]
        return OrderStatusResponse(
            order_id=order_id,
            status=order["status"],
            status_description=order["status_description"],
            tracking_number=order["tracking_number"],
            estimated_delivery=order["estimated_delivery"]
        )
    else:
        raise HTTPException(status_code=404, detail="Order not found") 