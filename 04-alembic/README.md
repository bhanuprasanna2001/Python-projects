# Project 4: Alembic Database Migrations

## 🎯 Learning Objectives
- Understand database migration concepts
- Set up Alembic with SQLAlchemy
- Create and manage migration scripts
- Handle upgrade and downgrade operations
- Implement data migrations

## 📁 Project Structure
```
04-alembic/
├── alembic/
│   ├── versions/       # Migration scripts
│   ├── env.py          # Migration environment
│   └── script.py.mako  # Template for migrations
├── alembic.ini         # Alembic configuration
├── models.py           # SQLAlchemy models
├── database.py         # Database connection
├── seed.py             # Seed data script
├── commands.md         # Common Alembic commands
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize Alembic (already done)
# alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Create users table"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## 🔑 Key Concepts

### Migration Workflow
```
┌────────────┐     ┌────────────┐     ┌────────────┐
│   Model    │ --> │ Autogenerate│ --> │ Migration  │
│   Change   │     │   Script   │     │   Apply    │
└────────────┘     └────────────┘     └────────────┘
                          │
                          v
              ┌──────────────────────┐
              │ Review & Edit Script │
              └──────────────────────┘
```

### Version Control
- Each migration has a unique revision ID
- Migrations form a linked chain
- Can upgrade/downgrade to any version

## 📚 Topics Covered
- Alembic configuration
- Auto-generating migrations
- Manual migration scripts
- Data migrations
- Batch operations
- Multi-database migrations
