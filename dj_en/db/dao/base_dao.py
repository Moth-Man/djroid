from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.orm import Session
from ..session import Base
import uuid

ModelType = TypeVar('ModelType', bound=Base)

class BaseDAO(ABC, Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: uuid.UUID) -> Optional[ModelType]:
        """Get a single record by ID"""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def update(self, id: uuid.UUID, attrs: dict) -> ModelType:
        """Update an existing record with new data"""
        db_obj = self.get(id)
        if not db_obj:
            raise ValueError(f"Record with id {id} not found")
        
        valid_fields = db_obj.__table__.columns.keys()
        for field, value in attrs.items():
            if field not in valid_fields:
                raise ValueError(f"Invalid field: {field}")
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID"""
        obj = self.db.query(self.model).filter(self.model.id == id).first()
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

    @abstractmethod        
    def create(self) -> ModelType:
        """CreaModelTypee a new record"""
        pass