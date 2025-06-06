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

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all records with pagination"""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def update(self, db_obj: T, obj_in: dict) -> ModelType:
        """Update an existing record with new data"""
        for field, value in obj_in.items():
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