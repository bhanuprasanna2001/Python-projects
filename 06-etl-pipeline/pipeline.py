"""
ETL Pipeline
============
Main pipeline orchestrator that combines extractors, transformers, and loaders.
"""

from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class PipelineResult:
    """Result of a pipeline run."""
    status: PipelineStatus
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    started_at: datetime = None
    completed_at: datetime = None
    
    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0


class ETLPipeline:
    """
    Generic ETL Pipeline.
    
    Usage:
        pipeline = ETLPipeline("user_pipeline")
        pipeline.add_extractor(csv_extractor)
        pipeline.add_transformer(clean_data)
        pipeline.add_transformer(validate_data)
        pipeline.add_loader(db_loader)
        result = pipeline.run()
    """
    
    def __init__(self, name: str):
        self.name = name
        self.extractors: List[Callable] = []
        self.transformers: List[Callable] = []
        self.loaders: List[Callable] = []
        self.error_handlers: List[Callable] = []
    
    def add_extractor(self, extractor: Callable) -> 'ETLPipeline':
        """Add an extractor function."""
        self.extractors.append(extractor)
        return self
    
    def add_transformer(self, transformer: Callable) -> 'ETLPipeline':
        """Add a transformer function."""
        self.transformers.append(transformer)
        return self
    
    def add_loader(self, loader: Callable) -> 'ETLPipeline':
        """Add a loader function."""
        self.loaders.append(loader)
        return self
    
    def add_error_handler(self, handler: Callable) -> 'ETLPipeline':
        """Add an error handler."""
        self.error_handlers.append(handler)
        return self
    
    def run(self, **kwargs) -> PipelineResult:
        """Execute the pipeline."""
        result = PipelineResult(
            status=PipelineStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        logger.info(f"Starting pipeline: {self.name}")
        
        try:
            # EXTRACT
            data = []
            for extractor in self.extractors:
                try:
                    extracted = extractor(**kwargs)
                    if isinstance(extracted, list):
                        data.extend(extracted)
                    else:
                        data.append(extracted)
                except Exception as e:
                    logger.error(f"Extraction error: {e}")
                    result.errors.append(f"Extract: {str(e)}")
            
            result.records_extracted = len(data)
            logger.info(f"Extracted {len(data)} records")
            
            # TRANSFORM
            for transformer in self.transformers:
                try:
                    data = transformer(data)
                except Exception as e:
                    logger.error(f"Transformation error: {e}")
                    result.errors.append(f"Transform: {str(e)}")
            
            result.records_transformed = len(data)
            logger.info(f"Transformed {len(data)} records")
            
            # LOAD
            loaded_count = 0
            for loader in self.loaders:
                try:
                    count = loader(data)
                    loaded_count += count if count else len(data)
                except Exception as e:
                    logger.error(f"Loading error: {e}")
                    result.errors.append(f"Load: {str(e)}")
            
            result.records_loaded = loaded_count
            logger.info(f"Loaded {loaded_count} records")
            
            # Determine status
            if result.errors:
                result.status = PipelineStatus.PARTIAL if loaded_count > 0 else PipelineStatus.FAILED
            else:
                result.status = PipelineStatus.SUCCESS
                
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result.errors.append(str(e))
            result.status = PipelineStatus.FAILED
            
            # Call error handlers
            for handler in self.error_handlers:
                try:
                    handler(e, result)
                except:
                    pass
        
        result.completed_at = datetime.utcnow()
        logger.info(f"Pipeline completed: {result.status.value} in {result.duration_seconds:.2f}s")
        
        return result


# ============================================================
# Sample Extractors
# ============================================================

def csv_extractor(file_path: str) -> List[Dict]:
    """Extract data from CSV file."""
    import csv
    
    data = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))
    
    return data


def api_extractor(url: str, headers: dict = None) -> List[Dict]:
    """Extract data from API endpoint."""
    import requests
    
    response = requests.get(url, headers=headers or {})
    response.raise_for_status()
    
    data = response.json()
    return data if isinstance(data, list) else [data]


# ============================================================
# Sample Transformers
# ============================================================

def clean_nulls(data: List[Dict]) -> List[Dict]:
    """Replace None/empty strings with default values."""
    cleaned = []
    for record in data:
        cleaned_record = {}
        for key, value in record.items():
            if value is None or value == '':
                cleaned_record[key] = None
            else:
                cleaned_record[key] = value
        cleaned.append(cleaned_record)
    return cleaned


def validate_emails(data: List[Dict], email_field: str = 'email') -> List[Dict]:
    """Filter records with valid emails."""
    import re
    email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    
    return [
        record for record in data
        if email_field in record and email_pattern.match(str(record[email_field]))
    ]


def normalize_names(data: List[Dict], name_fields: List[str] = None) -> List[Dict]:
    """Normalize name fields to title case."""
    name_fields = name_fields or ['name', 'first_name', 'last_name']
    
    for record in data:
        for field in name_fields:
            if field in record and record[field]:
                record[field] = str(record[field]).strip().title()
    
    return data


def add_timestamps(data: List[Dict]) -> List[Dict]:
    """Add processing timestamp to records."""
    timestamp = datetime.utcnow().isoformat()
    
    for record in data:
        record['processed_at'] = timestamp
    
    return data


# ============================================================
# Sample Loaders
# ============================================================

def json_loader(data: List[Dict], output_path: str) -> int:
    """Load data to JSON file."""
    import json
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    return len(data)


def print_loader(data: List[Dict]) -> int:
    """Print data (for debugging)."""
    for record in data:
        print(record)
    return len(data)


# ============================================================
# Demo
# ============================================================

if __name__ == "__main__":
    # Create sample data
    sample_data = [
        {"id": 1, "name": "john doe", "email": "john@example.com", "age": 30},
        {"id": 2, "name": "jane smith", "email": "jane@example.com", "age": 25},
        {"id": 3, "name": "bob wilson", "email": "invalid-email", "age": 35},
    ]
    
    # Create pipeline
    pipeline = ETLPipeline("demo_pipeline")
    
    # Add components
    pipeline.add_extractor(lambda: sample_data)
    pipeline.add_transformer(normalize_names)
    pipeline.add_transformer(validate_emails)
    pipeline.add_transformer(add_timestamps)
    pipeline.add_loader(lambda data: print_loader(data))
    
    # Run
    result = pipeline.run()
    
    print(f"\nPipeline Result:")
    print(f"  Status: {result.status.value}")
    print(f"  Extracted: {result.records_extracted}")
    print(f"  Transformed: {result.records_transformed}")
    print(f"  Loaded: {result.records_loaded}")
    print(f"  Errors: {result.errors}")
