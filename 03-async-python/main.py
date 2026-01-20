"""
Async Python Demo Runner
========================
Run all async demonstrations.
"""

import asyncio

from basics import run_basics_demo
from tasks import run_tasks_demo
from patterns import run_patterns_demo


async def main():
    """Run all async demos."""
    print("=" * 60)
    print("     ASYNC PYTHON - COMPREHENSIVE DEMO")
    print("=" * 60)
    
    # Basics
    await run_basics_demo()
    
    print("\n")
    
    # Tasks
    await run_tasks_demo()
    
    print("\n")
    
    # Patterns
    await run_patterns_demo()
    
    print("\n")
    print("=" * 60)
    print("     ALL DEMOS COMPLETED!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
