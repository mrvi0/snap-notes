"""
Модели данных для приложения заметок.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Note:
    """Класс для представления заметки."""
    id: Optional[int]
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> dict:
        """Преобразует заметку в словарь для сериализации."""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Note':
        """Создает заметку из словаря."""
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            content=data.get('content', ''),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )

