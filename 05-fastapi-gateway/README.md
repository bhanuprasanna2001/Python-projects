# Project 5: FastAPI & API Gateway

## 🎯 Learning Objectives
- Build RESTful APIs with FastAPI
- Implement request/response validation with Pydantic
- Use dependency injection effectively
- Build an API Gateway pattern
- Handle middleware and CORS

## 📁 Project Structure
```
05-fastapi-gateway/
├── gateway/
│   ├── main.py           # API Gateway service
│   ├── routing.py        # Dynamic routing
│   └── middleware.py     # Gateway middleware
├── services/
│   ├── users/            # User microservice
│   │   └── main.py
│   └── products/         # Product microservice
│       └── main.py
├── shared/
│   ├── models.py         # Shared Pydantic models
│   └── dependencies.py   # Shared dependencies
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Run all services
python -m uvicorn gateway.main:app --port 8000 &
python -m uvicorn services.users.main:app --port 8001 &
python -m uvicorn services.products.main:app --port 8002 &

# Or use docker-compose
docker-compose up
```

## 🔑 Key Concepts

### API Gateway Pattern
```
┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  Client  │ --> │ API Gateway │ --> │ User Service │
└──────────┘     │             │     └──────────────┘
                 │  - Routing  │     ┌──────────────┐
                 │  - Auth     │ --> │Product Service│
                 │  - Rate Limit│    └──────────────┘
                 └─────────────┘
```

## 📚 Topics Covered
- FastAPI fundamentals
- Pydantic models
- Dependency injection
- Middleware
- API Gateway routing
- Service composition
