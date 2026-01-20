# Project 6: ETL Data Pipeline

## 🎯 Learning Objectives
- Understand ETL (Extract, Transform, Load) concepts
- Build data extraction from multiple sources
- Implement data transformation and validation
- Load data to various destinations
- Handle errors and implement logging

## 📁 Project Structure
```
06-etl-pipeline/
├── extractors/
│   ├── csv_extractor.py
│   ├── api_extractor.py
│   └── db_extractor.py
├── transformers/
│   ├── cleaners.py
│   ├── validators.py
│   └── enrichers.py
├── loaders/
│   ├── db_loader.py
│   └── file_loader.py
├── pipeline.py          # Main pipeline orchestrator
├── config.py            # Configuration
├── main.py              # Demo runner
├── sample_data/
│   └── users.csv
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## 🔑 Key Concepts

### ETL Flow
```
┌──────────┐    ┌─────────────┐    ┌────────┐
│ EXTRACT  │ -> │  TRANSFORM  │ -> │  LOAD  │
│          │    │             │    │        │
│ - CSV    │    │ - Clean     │    │ - DB   │
│ - API    │    │ - Validate  │    │ - File │
│ - DB     │    │ - Enrich    │    │ - API  │
└──────────┘    └─────────────┘    └────────┘
```

## 📚 Topics Covered
- Data extraction patterns
- Transformation functions
- Data validation
- Batch processing
- Error handling
- Incremental loads
