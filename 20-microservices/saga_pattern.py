"""
Saga Pattern
============
Distributed transaction management across services.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from abc import ABC, abstractmethod
import uuid
import traceback


# =============================================================================
# Saga State
# =============================================================================

class SagaState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"


class StepState(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Saga Step
# =============================================================================

@dataclass
class SagaStep:
    """
    Represents a single step in a saga.
    Each step has an action and a compensation.
    """
    name: str
    action: Callable[[Dict], Awaitable[Dict]]
    compensation: Callable[[Dict], Awaitable[None]]
    state: StepState = StepState.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    executed_at: Optional[datetime] = None
    compensated_at: Optional[datetime] = None
    
    async def execute(self, context: Dict) -> Dict:
        """Execute the step action."""
        self.state = StepState.EXECUTING
        self.executed_at = datetime.now(timezone.utc)
        
        try:
            self.result = await self.action(context)
            self.state = StepState.COMPLETED
            return self.result
        except Exception as e:
            self.state = StepState.FAILED
            self.error = str(e)
            raise
    
    async def compensate(self, context: Dict):
        """Execute the step compensation."""
        if self.state not in [StepState.COMPLETED, StepState.FAILED]:
            self.state = StepState.SKIPPED
            return
        
        self.state = StepState.COMPENSATING
        self.compensated_at = datetime.now(timezone.utc)
        
        try:
            await self.compensation(context)
            self.state = StepState.COMPENSATED
        except Exception as e:
            self.error = f"Compensation failed: {e}"
            raise


# =============================================================================
# Saga
# =============================================================================

@dataclass
class Saga:
    """
    Saga orchestrator for managing distributed transactions.
    
    A saga is a sequence of steps where:
    - If all steps succeed, the transaction is complete
    - If any step fails, all previous steps are compensated
    """
    saga_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    steps: List[SagaStep] = field(default_factory=list)
    state: SagaState = SagaState.PENDING
    context: Dict = field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def add_step(
        self,
        name: str,
        action: Callable[[Dict], Awaitable[Dict]],
        compensation: Callable[[Dict], Awaitable[None]],
    ) -> "Saga":
        """Add a step to the saga."""
        step = SagaStep(
            name=name,
            action=action,
            compensation=compensation,
        )
        self.steps.append(step)
        return self
    
    async def execute(self) -> bool:
        """
        Execute the saga.
        Returns True if all steps succeeded, False if compensation was needed.
        """
        self.state = SagaState.RUNNING
        executed_steps: List[SagaStep] = []
        
        print(f"\n🔄 Starting saga: {self.name}")
        
        try:
            for step in self.steps:
                print(f"  ▶ Executing: {step.name}")
                
                # Execute step
                result = await step.execute(self.context)
                
                # Merge result into context
                if result:
                    self.context.update(result)
                
                executed_steps.append(step)
                print(f"  ✓ Completed: {step.name}")
            
            # All steps succeeded
            self.state = SagaState.COMPLETED
            self.completed_at = datetime.now(timezone.utc)
            print(f"✅ Saga completed: {self.name}")
            
            return True
            
        except Exception as e:
            self.error = str(e)
            print(f"  ✗ Failed: {e}")
            
            # Compensate in reverse order
            await self._compensate(executed_steps)
            
            return False
    
    async def _compensate(self, executed_steps: List[SagaStep]):
        """Compensate executed steps in reverse order."""
        self.state = SagaState.COMPENSATING
        print(f"\n🔙 Compensating saga: {self.name}")
        
        # Reverse order compensation
        for step in reversed(executed_steps):
            try:
                print(f"  ◀ Compensating: {step.name}")
                await step.compensate(self.context)
                print(f"  ✓ Compensated: {step.name}")
            except Exception as e:
                print(f"  ⚠ Compensation failed for {step.name}: {e}")
                # Log but continue compensating other steps
        
        self.state = SagaState.COMPENSATED
        self.completed_at = datetime.now(timezone.utc)
        print(f"🔙 Saga compensated: {self.name}")
    
    def get_status(self) -> Dict:
        """Get saga status."""
        return {
            "saga_id": self.saga_id,
            "name": self.name,
            "state": self.state.value,
            "error": self.error,
            "steps": [
                {
                    "name": step.name,
                    "state": step.state.value,
                    "error": step.error,
                }
                for step in self.steps
            ],
        }


# =============================================================================
# Saga Builder
# =============================================================================

class SagaBuilder:
    """Builder for creating sagas."""
    
    def __init__(self, name: str):
        self.saga = Saga(name=name)
    
    def step(
        self,
        name: str,
        action: Callable[[Dict], Awaitable[Dict]],
        compensation: Callable[[Dict], Awaitable[None]],
    ) -> "SagaBuilder":
        """Add a step."""
        self.saga.add_step(name, action, compensation)
        return self
    
    def with_context(self, context: Dict) -> "SagaBuilder":
        """Set initial context."""
        self.saga.context = context
        return self
    
    def build(self) -> Saga:
        """Build the saga."""
        return self.saga


# =============================================================================
# Example: Order Saga
# =============================================================================

class OrderSagaService:
    """
    Example service demonstrating order creation saga.
    
    Steps:
    1. Reserve inventory
    2. Create order
    3. Process payment
    4. Send notification
    
    If any step fails, all previous steps are compensated.
    """
    
    def __init__(self):
        self._inventory: Dict[str, int] = {
            "PROD-001": 100,
            "PROD-002": 50,
        }
        self._orders: Dict[str, Dict] = {}
        self._payments: Dict[str, Dict] = {}
    
    # Step 1: Reserve Inventory
    async def reserve_inventory(self, context: Dict) -> Dict:
        """Reserve inventory for order items."""
        items = context.get("items", [])
        reserved = []
        
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            
            if product_id not in self._inventory:
                raise Exception(f"Product {product_id} not found")
            
            if self._inventory[product_id] < quantity:
                raise Exception(f"Insufficient inventory for {product_id}")
            
            self._inventory[product_id] -= quantity
            reserved.append({
                "product_id": product_id,
                "quantity": quantity,
            })
        
        # Simulate delay
        await asyncio.sleep(0.1)
        
        return {"reserved_items": reserved}
    
    async def release_inventory(self, context: Dict):
        """Release reserved inventory."""
        reserved = context.get("reserved_items", [])
        
        for item in reserved:
            product_id = item["product_id"]
            quantity = item["quantity"]
            self._inventory[product_id] += quantity
        
        await asyncio.sleep(0.1)
    
    # Step 2: Create Order
    async def create_order(self, context: Dict) -> Dict:
        """Create order record."""
        order_id = str(uuid.uuid4())[:8]
        
        order = {
            "id": order_id,
            "user_id": context.get("user_id"),
            "items": context.get("items"),
            "status": "created",
            "total": sum(
                item["quantity"] * item.get("price", 0)
                for item in context.get("items", [])
            ),
        }
        
        self._orders[order_id] = order
        await asyncio.sleep(0.1)
        
        return {"order_id": order_id, "order": order}
    
    async def cancel_order(self, context: Dict):
        """Cancel created order."""
        order_id = context.get("order_id")
        
        if order_id and order_id in self._orders:
            self._orders[order_id]["status"] = "cancelled"
        
        await asyncio.sleep(0.1)
    
    # Step 3: Process Payment
    async def process_payment(self, context: Dict) -> Dict:
        """Process payment."""
        order = context.get("order", {})
        payment_method = context.get("payment_method", "credit_card")
        
        # Simulate payment failure for demo
        if context.get("simulate_payment_failure"):
            raise Exception("Payment declined by provider")
        
        payment_id = str(uuid.uuid4())[:8]
        
        payment = {
            "id": payment_id,
            "order_id": context.get("order_id"),
            "amount": order.get("total", 0),
            "method": payment_method,
            "status": "completed",
        }
        
        self._payments[payment_id] = payment
        await asyncio.sleep(0.2)  # Payment takes longer
        
        return {"payment_id": payment_id, "payment": payment}
    
    async def refund_payment(self, context: Dict):
        """Refund payment."""
        payment_id = context.get("payment_id")
        
        if payment_id and payment_id in self._payments:
            self._payments[payment_id]["status"] = "refunded"
        
        await asyncio.sleep(0.2)
    
    # Step 4: Send Notification
    async def send_notification(self, context: Dict) -> Dict:
        """Send order confirmation notification."""
        user_id = context.get("user_id")
        order_id = context.get("order_id")
        
        print(f"    📧 Notification sent to user {user_id} for order {order_id}")
        await asyncio.sleep(0.1)
        
        return {"notification_sent": True}
    
    async def no_compensation(self, context: Dict):
        """No compensation needed for notification."""
        pass
    
    def create_order_saga(
        self,
        user_id: int,
        items: List[Dict],
        payment_method: str = "credit_card",
        simulate_failure: bool = False,
    ) -> Saga:
        """Create an order saga."""
        
        return (
            SagaBuilder("CreateOrder")
            .with_context({
                "user_id": user_id,
                "items": items,
                "payment_method": payment_method,
                "simulate_payment_failure": simulate_failure,
            })
            .step(
                name="ReserveInventory",
                action=self.reserve_inventory,
                compensation=self.release_inventory,
            )
            .step(
                name="CreateOrder",
                action=self.create_order,
                compensation=self.cancel_order,
            )
            .step(
                name="ProcessPayment",
                action=self.process_payment,
                compensation=self.refund_payment,
            )
            .step(
                name="SendNotification",
                action=self.send_notification,
                compensation=self.no_compensation,
            )
            .build()
        )


# =============================================================================
# Saga Store (for persistence)
# =============================================================================

class SagaStore:
    """
    Store for persisting saga state.
    In production, use a database.
    """
    
    def __init__(self):
        self._sagas: Dict[str, Saga] = {}
    
    def save(self, saga: Saga):
        """Save saga state."""
        self._sagas[saga.saga_id] = saga
    
    def get(self, saga_id: str) -> Optional[Saga]:
        """Get saga by ID."""
        return self._sagas.get(saga_id)
    
    def get_all(self) -> List[Saga]:
        """Get all sagas."""
        return list(self._sagas.values())
    
    def get_by_state(self, state: SagaState) -> List[Saga]:
        """Get sagas by state."""
        return [s for s in self._sagas.values() if s.state == state]


# =============================================================================
# Demo
# =============================================================================

async def demo():
    """Demonstrate saga pattern."""
    
    print("=" * 60)
    print("Saga Pattern Demo")
    print("=" * 60)
    
    service = OrderSagaService()
    store = SagaStore()
    
    # 1. Successful saga
    print("\n1. Successful Order Saga")
    print("-" * 40)
    
    saga = service.create_order_saga(
        user_id=1,
        items=[
            {"product_id": "PROD-001", "quantity": 2, "price": 29.99},
            {"product_id": "PROD-002", "quantity": 1, "price": 49.99},
        ],
    )
    
    store.save(saga)
    
    success = await saga.execute()
    
    print(f"\nSaga result: {'Success' if success else 'Failed'}")
    print(f"Order ID: {saga.context.get('order_id')}")
    print(f"Payment ID: {saga.context.get('payment_id')}")
    
    # 2. Failed saga (payment failure)
    print("\n2. Failed Order Saga (with compensation)")
    print("-" * 40)
    
    failed_saga = service.create_order_saga(
        user_id=2,
        items=[
            {"product_id": "PROD-001", "quantity": 1, "price": 29.99},
        ],
        simulate_failure=True,  # This will cause payment to fail
    )
    
    store.save(failed_saga)
    
    success = await failed_saga.execute()
    
    print(f"\nSaga result: {'Success' if success else 'Failed (Compensated)'}")
    print(f"Error: {failed_saga.error}")
    
    # 3. Check inventory
    print("\n3. Inventory Check")
    print("-" * 40)
    
    print(f"PROD-001: {service._inventory['PROD-001']} units")
    print(f"PROD-002: {service._inventory['PROD-002']} units")
    
    # Note: Inventory should be restored after failed saga compensation
    
    # 4. Saga status
    print("\n4. Saga Status")
    print("-" * 40)
    
    for s in store.get_all():
        status = s.get_status()
        print(f"\nSaga: {status['name']} ({status['saga_id'][:8]}...)")
        print(f"State: {status['state']}")
        
        for step in status['steps']:
            icon = "✓" if step['state'] == "completed" else "◀" if step['state'] == "compensated" else "✗"
            print(f"  {icon} {step['name']}: {step['state']}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("""
    ================================================
    Saga Pattern
    ================================================
    
    The Saga pattern manages distributed transactions:
    
    1. Sequence of Steps
       - Each step has an action and compensation
       - Steps execute in order
    
    2. Compensation
       - If any step fails, previous steps are compensated
       - Compensations run in reverse order
    
    3. State Tracking
       - Track saga and step states
       - Persist for recovery
    
    Example: Order Creation Saga
    
    Step 1: Reserve Inventory
            Compensation: Release Inventory
    
    Step 2: Create Order
            Compensation: Cancel Order
    
    Step 3: Process Payment  <- If this fails
            Compensation: Refund Payment
    
    Step 4: Send Notification
            Compensation: (none needed)
    
    If Step 3 fails:
    - Step 2 is compensated (order cancelled)
    - Step 1 is compensated (inventory released)
    
    Benefits:
    - Eventual consistency across services
    - Automatic rollback on failure
    - Clear audit trail
    
    Challenges:
    - Complexity in compensation logic
    - Need for idempotent operations
    - Handling compensation failures
    ================================================
    """)
    
    asyncio.run(demo())
