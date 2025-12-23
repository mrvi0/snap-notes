"""
Модели данных для приложения заметок.

Markdown - единственный канонический формат хранения.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Note:
    """
    Класс для представления заметки.
    
    Все заметки хранятся в формате Markdown.
    HTML не используется ни для хранения, ни как промежуточный формат.
    """
    id: Optional[int]
    title: str
    markdown_content: str  # Всегда Markdown, никогда HTML
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> dict:
        """Преобразует заметку в словарь для сериализации."""
        return {
            'id': self.id,
            'title': self.title,
            'markdown_content': self.markdown_content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Note':
        """Создает заметку из словаря."""
        return cls(
            id=data.get('id'),
            title=data.get('title', ''),
            markdown_content=data.get('markdown_content', ''),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            updated_at=datetime.fromisoformat(data.get('updated_at', datetime.now().isoformat()))
        )
