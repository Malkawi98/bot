from typing import List, Dict, Any, Optional, Tuple
import re
import random
from datetime import datetime, timedelta
from app.services.rag import RAGService

# Initialize RAG service
rag_service = RAGService()

# Mock data for product catalog and order information
from app.api.v1.bot import MOCK_PRODUCT_CATALOG, PRODUCTS, ORDER_STATUSES, FAQS

class BotService:
    def __init__(self):
        self.rag_service = rag_service
        self.product_catalog = MOCK_PRODUCT_CATALOG
        self.products = PRODUCTS
        self.order_statuses = ORDER_STATUSES
        self.faqs = FAQS
        
    def process_message(self, message: str, session_state: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]], Optional[Dict[str, Any]], float]:
        """
        Process a user message and return a response, quick actions, and additional data
        
        Args:
            message: The user's message
            session_state: The current session state
            
        Returns:
            Tuple containing:
            - reply: The bot's response
            - quick_actions: List of quick action buttons
            - additional_data: Additional data like product info or order details
            - confidence: Confidence score of the response
        """
        message_lower = message.lower()
        confidence = 0.9  # Default high confidence
        additional_data = None
        
        # Track conversation history
        if "history" not in session_state:
            session_state["history"] = []
        
        session_state["history"].append({"role": "user", "content": message})
        
        # Check for FAQ matches first
        for keyword, answer in self.faqs.items():
            if keyword in message_lower:
                reply = answer
                quick_actions = self._get_contextual_quick_actions(message_lower, "faq")
                session_state["history"].append({"role": "bot", "content": reply})
                return reply, quick_actions, None, 0.95
        
        # Check for order tracking
        if self._is_order_tracking_request(message_lower):
            order_number = self._extract_order_number(message)
            if not order_number:
                order_number = self._generate_random_order_number()
            
            order_info, reply = self._get_order_info(order_number)
            quick_actions = self._get_contextual_quick_actions(message_lower, "order")
            session_state["history"].append({"role": "bot", "content": reply})
            return reply, quick_actions, {"order_info": order_info}, 0.9
        
        # Check for product inquiries
        product_match, product_key = self._find_product_match(message_lower)
        if product_match:
            product_info = self.product_catalog[product_key]
            reply = self._format_product_info(product_info)
            quick_actions = self._get_contextual_quick_actions(message_lower, "product", product_key)
            additional_data = {"product_info": product_info}
            session_state["history"].append({"role": "bot", "content": reply})
            return reply, quick_actions, additional_data, 0.9
        
        # Check for product recommendations
        if self._is_recommendation_request(message_lower):
            recommended_products = self._get_product_recommendations(message_lower)
            reply = self._format_product_recommendations(recommended_products)
            quick_actions = self._get_contextual_quick_actions(message_lower, "recommendation")
            additional_data = {"recommended_products": recommended_products}
            session_state["history"].append({"role": "bot", "content": reply})
            return reply, quick_actions, additional_data, 0.85
        
        # Check for return requests
        if self._is_return_request(message_lower):
            reply, return_info = self._process_return_request(message_lower)
            quick_actions = self._get_contextual_quick_actions(message_lower, "return")
            additional_data = {"return_info": return_info}
            session_state["history"].append({"role": "bot", "content": reply})
            return reply, quick_actions, additional_data, 0.9
        
        # Check for human handoff requests
        if self._is_human_handoff_request(message_lower):
            reply = "I'll connect you with a human agent shortly. While you wait, is there anything specific you'd like the agent to know about your issue?"
            quick_actions = [
                {"label": "Just wait for agent", "value": "I'll just wait for the agent"},
                {"label": "Explain my issue", "value": "I'd like to explain my issue"}
            ]
            session_state["human_handoff_requested"] = True
            session_state["history"].append({"role": "bot", "content": reply})
            return reply, quick_actions, None, 0.95
        
        # If no specific intent is matched, use RAG to find a relevant response
        try:
            rag_results = self.rag_service.search_similar(message, top_k=1)
            if rag_results and len(rag_results) > 0:
                rag_response = rag_results[0]
                reply = f"Based on our knowledge base: {rag_response}"
                confidence = 0.7
            else:
                # Fallback response
                reply = "I'm not sure I understand. Could you please rephrase your question or select one of the options below?"
                confidence = 0.5
        except Exception as e:
            # If RAG fails, use a generic response
            reply = "I'm here to help with orders, returns, and product information. How can I assist you today?"
            confidence = 0.6
        
        quick_actions = self._get_contextual_quick_actions(message_lower, "general")
        session_state["history"].append({"role": "bot", "content": reply})
        return reply, quick_actions, None, confidence
    
    def _is_order_tracking_request(self, message: str) -> bool:
        """Check if the message is an order tracking request"""
        tracking_keywords = ["track", "order", "package", "delivery", "shipping", "arrive", "status"]
        return any(keyword in message for keyword in tracking_keywords) and "order" in message
    
    def _extract_order_number(self, message: str) -> Optional[str]:
        """Extract order number from message"""
        # Look for patterns like "order #12345" or "order number 12345"
        order_patterns = [
            r"order\s*#\s*(\d+)",
            r"order\s*number\s*(\d+)",
            r"order\s*id\s*(\d+)",
            r"#(\d{5,})"
        ]
        
        for pattern in order_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _generate_random_order_number(self) -> str:
        """Generate a random order number for demo purposes"""
        return f"{random.randint(10000, 99999)}"
    
    def _get_order_info(self, order_number: str) -> Tuple[Dict[str, Any], str]:
        """Get information about an order"""
        # In a real implementation, this would query a database
        # For demo purposes, we'll generate random information
        
        # Randomly select an order status
        status_obj = random.choice(self.order_statuses)
        status = status_obj["label"]
        status_description = status_obj["description"]
        
        # Generate a random tracking number
        tracking_number = f"TRK{random.randint(1000000, 9999999)}"
        
        # Generate a random estimated delivery date (3-7 days from now)
        days_to_delivery = random.randint(3, 7)
        delivery_date = (datetime.now() + timedelta(days=days_to_delivery)).strftime("%B %d, %Y")
        
        # Create order info object
        order_info = {
            "order_id": order_number,
            "status": status,
            "status_description": status_description,
            "tracking_number": tracking_number,
            "estimated_delivery": delivery_date,
            "items": [random.choice(self.products) for _ in range(random.randint(1, 3))]
        }
        
        # Create reply message
        if status == "Delivered":
            reply = f"Your order #{order_number} has been delivered. Is there anything else you need help with?"
        elif status == "Cancelled":
            reply = f"Your order #{order_number} has been cancelled. If you didn't request this cancellation, please contact our support team."
        else:
            reply = f"I found your order #{order_number}. It's currently {status}. {status_description} The estimated delivery date is {delivery_date}. Your tracking number is {tracking_number}."
        
        return order_info, reply
    
    def _find_product_match(self, message: str) -> Tuple[bool, Optional[str]]:
        """Find if the message contains a product inquiry"""
        for product_key in self.product_catalog.keys():
            if product_key in message:
                return True, product_key
        return False, None
    
    def _format_product_info(self, product_info: Dict[str, Any]) -> str:
        """Format product information into a readable response"""
        name = product_info["name"]
        price = product_info["price"]
        description = product_info["description"]
        features = ", ".join(product_info["features"][:3])  # Show first 3 features
        
        return f"{name} - ${price}\n\n{description}\n\nKey features: {features}\n\nWould you like more information or would you like to add this to your cart?"
    
    def _is_recommendation_request(self, message: str) -> bool:
        """Check if the message is asking for product recommendations"""
        recommendation_keywords = ["recommend", "suggestion", "suggest", "best", "top", "popular"]
        return any(keyword in message for keyword in recommendation_keywords)
    
    def _get_product_recommendations(self, message: str) -> List[Dict[str, Any]]:
        """Get product recommendations based on the message"""
        # In a real implementation, this would use a recommendation algorithm
        # For demo purposes, we'll return random products
        return random.sample(self.products, min(3, len(self.products)))
    
    def _format_product_recommendations(self, products: List[Dict[str, Any]]) -> str:
        """Format product recommendations into a readable response"""
        product_lines = [f"• {p['name']} - ${p['price']} (Rating: {p['rating']})" for p in products]
        products_text = "\n".join(product_lines)
        
        return f"Based on your interests, I recommend these products:\n\n{products_text}\n\nWould you like more details about any of these?"
    
    def _is_return_request(self, message: str) -> bool:
        """Check if the message is about returning a product"""
        return "return" in message or "refund" in message
    
    def _process_return_request(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """Process a return request"""
        # In a real implementation, this would create a return request in a database
        # For demo purposes, we'll generate a random return ID
        return_id = f"RTN{random.randint(10000, 99999)}"
        
        return_info = {
            "return_id": return_id,
            "status": "Initiated",
            "instructions": "Please package the item in its original packaging if possible. Print the return label we've emailed to you and attach it to the package."
        }
        
        reply = f"I've initiated a return request for you. Your return ID is {return_id}. You'll receive an email with a return shipping label shortly. Would you like me to explain the return process?"
        
        return reply, return_info
    
    def _is_human_handoff_request(self, message: str) -> bool:
        """Check if the user is requesting to speak with a human agent"""
        human_keywords = ["human", "agent", "person", "representative", "speak to someone", "talk to someone"]
        return any(keyword in message for keyword in human_keywords)
    
    def _get_contextual_quick_actions(self, message: str, context_type: str, product_key: str = None) -> List[Dict[str, str]]:
        """Get contextual quick action buttons based on the message and context"""
        if context_type == "order":
            return [
                {"label": "Track Another Order", "value": "Track another order"},
                {"label": "Order Issues", "value": "I have an issue with my order"},
                {"label": "Return Item", "value": "I want to return an item"}
            ]
        elif context_type == "product":
            return [
                {"label": "Add to Cart", "value": f"Add {self.product_catalog[product_key]['name']} to cart"},
                {"label": "See Similar Products", "value": f"Show me products similar to {self.product_catalog[product_key]['name']}"},
                {"label": "Check Availability", "value": f"Is {self.product_catalog[product_key]['name']} in stock?"}
            ]
        elif context_type == "recommendation":
            return [
                {"label": "More Recommendations", "value": "Show me more recommendations"},
                {"label": "Filter by Price", "value": "Show me affordable options"},
                {"label": "Best Sellers", "value": "What are your best sellers?"}
            ]
        elif context_type == "return":
            return [
                {"label": "Return Policy", "value": "What's your return policy?"},
                {"label": "Return Status", "value": "Check return status"},
                {"label": "Contact Support", "value": "I need help with my return"}
            ]
        elif context_type == "faq":
            return [
                {"label": "More Questions", "value": "I have more questions"},
                {"label": "Talk to Human", "value": "I want to talk to a human agent"}
            ]
        else:
            # General quick actions
            return [
                {"label": "Track Order", "value": "Track my order"},
                {"label": "Return Item", "value": "I want to return an item"},
                {"label": "Product Help", "value": "Help me find a product"},
                {"label": "Talk to Human", "value": "I want to talk to a human agent"}
            ]
