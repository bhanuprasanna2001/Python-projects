# Project 2: SQLAlchemy ORM

## 🎯 Learning Objectives
- Understand ORM concepts and SQLAlchemy architecture
- Define models with relationships (one-to-many, many-to-many)
- Master session management and transactions
- Build complex queries with filtering, joining, aggregation
- Implement async SQLAlchemy patterns

## 📁 Project Structure
```
02-sqlalchemy/
├── models.py           # ORM model definitions
├── database.py         # Engine and session configuration
├── crud.py             # CRUD operations
├── queries.py          # Advanced query examples
├── relationships.py    # Relationship demonstrations
├── async_example.py    # Async SQLAlchemy
├── main.py             # Interactive demo
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## 🔑 Key Concepts

### SQLAlchemy Architecture
```
┌─────────────────────────────────────────┐
│              Your Code                  │
├─────────────────────────────────────────┤
│              ORM Layer                  │
│    (Models, Sessions, Relationships)    │
├─────────────────────────────────────────┤
│            Core Layer                   │
│    (Engine, Connection, Dialect)        │
├─────────────────────────────────────────┤
│           Database (PostgreSQL)         │
└─────────────────────────────────────────┘
```

### Session Lifecycle
1. Create session
2. Perform operations (add, query, update, delete)
3. Commit or rollback
4. Close session

## 📚 Topics Covered
- Declarative models
- Relationships (1:1, 1:N, M:N)
- Session management
- Query building
- Eager vs lazy loading
- Connection pooling
- Async SQLAlchemy 2.0
