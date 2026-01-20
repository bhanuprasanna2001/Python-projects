"""
RabbitMQ Work Queue Pattern
===========================
Task distribution across multiple workers with acknowledgment.
"""

import pika
import json
import time
import random
import sys
from typing import Callable


# =============================================================================
# Connection Helper
# =============================================================================

def get_connection():
    """Create RabbitMQ connection."""
    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        credentials=credentials,
    )
    return pika.BlockingConnection(parameters)


# =============================================================================
# Producer
# =============================================================================

class TaskProducer:
    """Produces tasks to the work queue."""
    
    def __init__(self, queue_name: str = "task_queue"):
        self.queue_name = queue_name
        self.connection = get_connection()
        self.channel = self.connection.channel()
        
        # Declare durable queue
        self.channel.queue_declare(
            queue=queue_name,
            durable=True  # Queue survives broker restart
        )
    
    def send_task(self, task_data: dict, priority: int = 0) -> None:
        """Send a task to the queue."""
        message = json.dumps(task_data)
        
        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent message
                priority=priority,
                content_type='application/json',
            )
        )
        
        print(f"[x] Sent task: {task_data.get('task_id', 'unknown')}")
    
    def close(self):
        self.connection.close()


# =============================================================================
# Consumer (Worker)
# =============================================================================

class TaskWorker:
    """Consumes and processes tasks from the work queue."""
    
    def __init__(
        self,
        queue_name: str = "task_queue",
        worker_id: str = "worker-1",
        prefetch_count: int = 1
    ):
        self.queue_name = queue_name
        self.worker_id = worker_id
        self.connection = get_connection()
        self.channel = self.connection.channel()
        
        # Declare queue (same settings as producer)
        self.channel.queue_declare(
            queue=queue_name,
            durable=True
        )
        
        # Fair dispatch - don't give more than N unacked messages
        self.channel.basic_qos(prefetch_count=prefetch_count)
    
    def process_task(self, task_data: dict) -> bool:
        """
        Process a single task.
        Override this method for custom processing.
        Returns True on success, False on failure.
        """
        task_id = task_data.get('task_id', 'unknown')
        duration = task_data.get('duration', 1)
        
        print(f"[{self.worker_id}] Processing task {task_id} ({duration}s)")
        
        # Simulate work
        time.sleep(duration)
        
        # Simulate occasional failure
        if random.random() < 0.1:
            print(f"[{self.worker_id}] Task {task_id} FAILED")
            return False
        
        print(f"[{self.worker_id}] Task {task_id} DONE")
        return True
    
    def _callback(self, ch, method, properties, body):
        """Message callback handler."""
        task_data = json.loads(body)
        
        try:
            success = self.process_task(task_data)
            
            if success:
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
            else:
                # Reject and requeue
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True
                )
        except Exception as e:
            print(f"[{self.worker_id}] Error: {e}")
            # Reject and don't requeue (send to DLQ if configured)
            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False
            )
    
    def start(self):
        """Start consuming messages."""
        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self._callback,
            auto_ack=False  # Manual acknowledgment
        )
        
        print(f"[{self.worker_id}] Waiting for tasks. Press CTRL+C to exit.")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        
        self.connection.close()


# =============================================================================
# Dead Letter Queue
# =============================================================================

def setup_with_dlq():
    """Setup queue with dead letter exchange for failed messages."""
    connection = get_connection()
    channel = connection.channel()
    
    # Dead letter exchange and queue
    channel.exchange_declare(exchange='dlx', exchange_type='direct')
    channel.queue_declare(queue='failed_tasks', durable=True)
    channel.queue_bind(queue='failed_tasks', exchange='dlx', routing_key='task_queue')
    
    # Main queue with DLX
    args = {
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'task_queue',
        'x-message-ttl': 300000,  # 5 minute TTL
    }
    channel.queue_declare(queue='task_queue_dlq', durable=True, arguments=args)
    
    connection.close()
    print("Queue with DLQ configured")


# =============================================================================
# Priority Queue
# =============================================================================

def setup_priority_queue():
    """Setup queue with priority support."""
    connection = get_connection()
    channel = connection.channel()
    
    # Queue with priority support (max priority 10)
    args = {'x-max-priority': 10}
    channel.queue_declare(queue='priority_tasks', durable=True, arguments=args)
    
    connection.close()
    print("Priority queue configured")


# =============================================================================
# Demo
# =============================================================================

def run_producer():
    """Run the producer demo."""
    producer = TaskProducer()
    
    # Send some tasks
    for i in range(10):
        task = {
            'task_id': f'task-{i}',
            'type': 'process_data',
            'duration': random.randint(1, 3),
            'data': {'item_id': i * 100}
        }
        producer.send_task(task, priority=random.randint(0, 5))
    
    producer.close()
    print("\nAll tasks sent!")


def run_worker(worker_id: str = "worker-1"):
    """Run a worker."""
    worker = TaskWorker(worker_id=worker_id)
    worker.start()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "producer":
            run_producer()
        elif sys.argv[1] == "worker":
            worker_id = sys.argv[2] if len(sys.argv) > 2 else "worker-1"
            run_worker(worker_id)
        elif sys.argv[1] == "setup":
            setup_with_dlq()
            setup_priority_queue()
    else:
        print("Usage:")
        print("  python work_queue.py setup    - Setup queues")
        print("  python work_queue.py producer - Send tasks")
        print("  python work_queue.py worker [id] - Start worker")
