"""
Service Discovery
=================
Service registration, discovery, and health checking.
"""

import asyncio
import httpx
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import random
import hashlib
import time


# =============================================================================
# Health Status
# =============================================================================

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    MAINTENANCE = "maintenance"


@dataclass
class ServiceInstance:
    """Represents a service instance."""
    service_name: str
    instance_id: str
    host: str
    port: int
    metadata: Dict[str, str] = field(default_factory=dict)
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_heartbeat: Optional[datetime] = None
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"
    
    @property
    def url(self) -> str:
        return f"http://{self.address}"
    
    def is_available(self) -> bool:
        return self.health_status == HealthStatus.HEALTHY


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """
    In-memory service registry.
    In production, use Consul, etcd, Zookeeper, or Kubernetes.
    """
    
    def __init__(self, heartbeat_timeout: timedelta = timedelta(seconds=30)):
        self._instances: Dict[str, Dict[str, ServiceInstance]] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._listeners: List[Callable] = []
    
    def register(
        self,
        service_name: str,
        host: str,
        port: int,
        instance_id: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ServiceInstance:
        """Register a service instance."""
        
        if instance_id is None:
            # Generate unique instance ID
            unique_str = f"{service_name}-{host}-{port}-{time.time()}"
            instance_id = hashlib.md5(unique_str.encode()).hexdigest()[:12]
        
        instance = ServiceInstance(
            service_name=service_name,
            instance_id=instance_id,
            host=host,
            port=port,
            metadata=metadata or {},
            health_status=HealthStatus.HEALTHY,
            last_heartbeat=datetime.now(timezone.utc),
        )
        
        if service_name not in self._instances:
            self._instances[service_name] = {}
        
        self._instances[service_name][instance_id] = instance
        
        print(f"✅ Registered: {service_name}/{instance_id} at {instance.address}")
        self._notify_listeners("register", instance)
        
        return instance
    
    def deregister(self, service_name: str, instance_id: str) -> bool:
        """Deregister a service instance."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                instance = self._instances[service_name].pop(instance_id)
                print(f"❌ Deregistered: {service_name}/{instance_id}")
                self._notify_listeners("deregister", instance)
                return True
        return False
    
    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Update heartbeat for an instance."""
        if service_name in self._instances:
            if instance_id in self._instances[service_name]:
                instance = self._instances[service_name][instance_id]
                instance.last_heartbeat = datetime.now(timezone.utc)
                return True
        return False
    
    def get_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get all instances of a service."""
        if service_name not in self._instances:
            return []
        return list(self._instances[service_name].values())
    
    def get_healthy_instances(self, service_name: str) -> List[ServiceInstance]:
        """Get only healthy instances."""
        return [
            inst for inst in self.get_instances(service_name)
            if inst.is_available()
        ]
    
    def get_instance(
        self,
        service_name: str,
        instance_id: str,
    ) -> Optional[ServiceInstance]:
        """Get a specific instance."""
        if service_name in self._instances:
            return self._instances[service_name].get(instance_id)
        return None
    
    def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services."""
        return {
            name: list(instances.values())
            for name, instances in self._instances.items()
        }
    
    def update_health(
        self,
        service_name: str,
        instance_id: str,
        status: HealthStatus,
    ) -> bool:
        """Update health status of an instance."""
        instance = self.get_instance(service_name, instance_id)
        if instance:
            old_status = instance.health_status
            instance.health_status = status
            
            if old_status != status:
                print(f"🔄 Health changed: {service_name}/{instance_id} "
                      f"{old_status.value} -> {status.value}")
                self._notify_listeners("health_change", instance)
            
            return True
        return False
    
    def cleanup_stale(self) -> List[ServiceInstance]:
        """Remove instances that haven't sent heartbeat."""
        now = datetime.now(timezone.utc)
        stale = []
        
        for service_name in list(self._instances.keys()):
            for instance_id in list(self._instances[service_name].keys()):
                instance = self._instances[service_name][instance_id]
                
                if instance.last_heartbeat:
                    age = now - instance.last_heartbeat
                    if age > self._heartbeat_timeout:
                        stale.append(instance)
                        self.deregister(service_name, instance_id)
        
        return stale
    
    def add_listener(self, callback: Callable):
        """Add listener for registry events."""
        self._listeners.append(callback)
    
    def _notify_listeners(self, event: str, instance: ServiceInstance):
        """Notify all listeners of an event."""
        for listener in self._listeners:
            try:
                listener(event, instance)
            except Exception as e:
                print(f"Listener error: {e}")


# =============================================================================
# Load Balancers
# =============================================================================

class LoadBalancer:
    """Base load balancer."""
    
    def select(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        raise NotImplementedError


class RoundRobinLoadBalancer(LoadBalancer):
    """Round-robin load balancing."""
    
    def __init__(self):
        self._counters: Dict[str, int] = {}
    
    def select(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        # Use first instance's service name as key
        key = instances[0].service_name
        
        counter = self._counters.get(key, 0)
        instance = instances[counter % len(instances)]
        
        self._counters[key] = counter + 1
        
        return instance


class RandomLoadBalancer(LoadBalancer):
    """Random load balancing."""
    
    def select(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        if not instances:
            return None
        return random.choice(instances)


class WeightedLoadBalancer(LoadBalancer):
    """Weighted load balancing based on metadata."""
    
    def select(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        # Get weights from metadata (default to 1)
        weights = [
            int(inst.metadata.get("weight", 1))
            for inst in instances
        ]
        
        total = sum(weights)
        r = random.randint(1, total)
        
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return instances[i]
        
        return instances[-1]


class LeastConnectionsLoadBalancer(LoadBalancer):
    """Select instance with least active connections."""
    
    def __init__(self):
        self._connections: Dict[str, int] = {}
    
    def select(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        if not instances:
            return None
        
        # Find instance with minimum connections
        min_instance = min(
            instances,
            key=lambda i: self._connections.get(i.instance_id, 0)
        )
        
        return min_instance
    
    def increment(self, instance_id: str):
        self._connections[instance_id] = self._connections.get(instance_id, 0) + 1
    
    def decrement(self, instance_id: str):
        if instance_id in self._connections:
            self._connections[instance_id] = max(0, self._connections[instance_id] - 1)


# =============================================================================
# Service Discovery Client
# =============================================================================

class DiscoveryClient:
    """
    Client for service discovery with load balancing.
    """
    
    def __init__(
        self,
        registry: ServiceRegistry,
        load_balancer: Optional[LoadBalancer] = None,
    ):
        self.registry = registry
        self.load_balancer = load_balancer or RoundRobinLoadBalancer()
        self._cache: Dict[str, List[ServiceInstance]] = {}
        self._cache_ttl = timedelta(seconds=30)
        self._cache_updated: Dict[str, datetime] = {}
    
    def discover(
        self,
        service_name: str,
        healthy_only: bool = True,
    ) -> List[ServiceInstance]:
        """Discover service instances."""
        # Check cache
        now = datetime.now(timezone.utc)
        
        if service_name in self._cache:
            cache_age = now - self._cache_updated.get(
                service_name,
                datetime.min.replace(tzinfo=timezone.utc)
            )
            
            if cache_age < self._cache_ttl:
                instances = self._cache[service_name]
                if healthy_only:
                    return [i for i in instances if i.is_available()]
                return instances
        
        # Fetch from registry
        if healthy_only:
            instances = self.registry.get_healthy_instances(service_name)
        else:
            instances = self.registry.get_instances(service_name)
        
        # Update cache
        self._cache[service_name] = instances
        self._cache_updated[service_name] = now
        
        return instances
    
    def get_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Get a single instance using load balancer."""
        instances = self.discover(service_name, healthy_only=True)
        return self.load_balancer.select(instances)
    
    def get_url(self, service_name: str) -> Optional[str]:
        """Get URL for a service."""
        instance = self.get_instance(service_name)
        return instance.url if instance else None
    
    def invalidate_cache(self, service_name: Optional[str] = None):
        """Invalidate discovery cache."""
        if service_name:
            self._cache.pop(service_name, None)
            self._cache_updated.pop(service_name, None)
        else:
            self._cache.clear()
            self._cache_updated.clear()


# =============================================================================
# Health Checker
# =============================================================================

class HealthChecker:
    """
    Periodically checks health of registered services.
    """
    
    def __init__(
        self,
        registry: ServiceRegistry,
        check_interval: float = 10.0,
        timeout: float = 5.0,
    ):
        self.registry = registry
        self.check_interval = check_interval
        self.timeout = timeout
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def check_instance(self, instance: ServiceInstance) -> HealthStatus:
        """Check health of a single instance."""
        health_url = f"{instance.url}/health"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(health_url)
                
                if response.status_code == 200:
                    return HealthStatus.HEALTHY
                else:
                    return HealthStatus.UNHEALTHY
                    
        except httpx.TimeoutException:
            return HealthStatus.UNHEALTHY
        except Exception:
            return HealthStatus.UNKNOWN
    
    async def check_all(self):
        """Check all registered instances."""
        all_services = self.registry.get_all_services()
        
        for service_name, instances in all_services.items():
            for instance in instances:
                status = await self.check_instance(instance)
                self.registry.update_health(
                    service_name,
                    instance.instance_id,
                    status,
                )
    
    async def _run_loop(self):
        """Run health check loop."""
        while self._running:
            try:
                await self.check_all()
            except Exception as e:
                print(f"Health check error: {e}")
            
            await asyncio.sleep(self.check_interval)
    
    async def start(self):
        """Start health checker."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        print("🏥 Health checker started")
    
    async def stop(self):
        """Stop health checker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("🏥 Health checker stopped")


# =============================================================================
# Self Registration
# =============================================================================

class ServiceRegistrationManager:
    """
    Manages self-registration for a service.
    """
    
    def __init__(
        self,
        registry: ServiceRegistry,
        service_name: str,
        host: str,
        port: int,
        heartbeat_interval: float = 10.0,
    ):
        self.registry = registry
        self.service_name = service_name
        self.host = host
        self.port = port
        self.heartbeat_interval = heartbeat_interval
        
        self._instance: Optional[ServiceInstance] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def register(self, metadata: Optional[Dict] = None) -> ServiceInstance:
        """Register this service."""
        self._instance = self.registry.register(
            service_name=self.service_name,
            host=self.host,
            port=self.port,
            metadata=metadata,
        )
        
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        
        return self._instance
    
    async def deregister(self):
        """Deregister this service."""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        if self._instance:
            self.registry.deregister(
                self.service_name,
                self._instance.instance_id,
            )
            self._instance = None
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        while self._running and self._instance:
            try:
                self.registry.heartbeat(
                    self.service_name,
                    self._instance.instance_id,
                )
            except Exception as e:
                print(f"Heartbeat error: {e}")
            
            await asyncio.sleep(self.heartbeat_interval)


# =============================================================================
# Demo
# =============================================================================

async def demo():
    """Demonstrate service discovery."""
    
    print("=" * 60)
    print("Service Discovery Demo")
    print("=" * 60)
    
    # Create registry
    registry = ServiceRegistry(heartbeat_timeout=timedelta(seconds=15))
    
    # 1. Register services
    print("\n1. Registering Services")
    print("-" * 40)
    
    # Register multiple instances
    registry.register("user-service", "localhost", 8001, metadata={"weight": "3"})
    registry.register("user-service", "localhost", 8011, metadata={"weight": "1"})
    registry.register("order-service", "localhost", 8002)
    registry.register("notification-service", "localhost", 8003)
    
    # 2. Discovery
    print("\n2. Service Discovery")
    print("-" * 40)
    
    client = DiscoveryClient(registry)
    
    # Discover all instances
    user_instances = client.discover("user-service")
    print(f"Found {len(user_instances)} user-service instances:")
    for inst in user_instances:
        print(f"  - {inst.instance_id}: {inst.address} (weight: {inst.metadata.get('weight', '1')})")
    
    # 3. Load balancing
    print("\n3. Load Balancing")
    print("-" * 40)
    
    # Round-robin
    print("Round-robin selection:")
    rr_client = DiscoveryClient(registry, RoundRobinLoadBalancer())
    for i in range(4):
        inst = rr_client.get_instance("user-service")
        print(f"  {i+1}: {inst.address if inst else 'None'}")
    
    # Weighted
    print("\nWeighted selection (5 requests):")
    weighted_client = DiscoveryClient(registry, WeightedLoadBalancer())
    counts = {}
    for _ in range(100):
        inst = weighted_client.get_instance("user-service")
        if inst:
            counts[inst.address] = counts.get(inst.address, 0) + 1
    
    for addr, count in counts.items():
        print(f"  {addr}: {count}%")
    
    # 4. Health checking
    print("\n4. Health Status Updates")
    print("-" * 40)
    
    # Mark one unhealthy
    user_instances = registry.get_instances("user-service")
    if user_instances:
        registry.update_health(
            "user-service",
            user_instances[0].instance_id,
            HealthStatus.UNHEALTHY,
        )
    
    # Now discovery should return fewer instances
    healthy = client.discover("user-service", healthy_only=True)
    print(f"Healthy instances: {len(healthy)}")
    
    all_instances = client.discover("user-service", healthy_only=False)
    print(f"All instances: {len(all_instances)}")
    
    # 5. Self-registration
    print("\n5. Self-Registration Pattern")
    print("-" * 40)
    
    manager = ServiceRegistrationManager(
        registry=registry,
        service_name="new-service",
        host="localhost",
        port=9000,
        heartbeat_interval=5.0,
    )
    
    instance = await manager.register({"version": "1.0.0"})
    print(f"Self-registered: {instance.service_name}/{instance.instance_id}")
    
    # Simulate heartbeat
    await asyncio.sleep(0.1)
    
    # Deregister
    await manager.deregister()
    print("Self-deregistered")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("""
    ================================================
    Service Discovery
    ================================================
    
    This module demonstrates:
    
    1. Service Registry
       - Registration/deregistration
       - Heartbeat mechanism
       - Health tracking
    
    2. Load Balancing Strategies
       - Round-robin
       - Random
       - Weighted
       - Least connections
    
    3. Discovery Client
       - Instance caching
       - Health-aware selection
    
    4. Health Checking
       - Periodic health checks
       - Status updates
    
    5. Self-Registration
       - Auto-registration on startup
       - Heartbeat management
       - Graceful deregistration
    
    In production, use:
    - Consul (HashiCorp)
    - etcd
    - Kubernetes DNS/Services
    - Netflix Eureka
    ================================================
    """)
    
    asyncio.run(demo())
