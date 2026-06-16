import json
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.types import TypeDecorator, String

# Создаем базовый класс для моделей
Base = declarative_base()

# Класс для работы с JSON полями
class JSONColumn(TypeDecorator):
    """Позволяет хранить JSON в SQLite"""
    impl = String
    
    def process_bind_param(self, value, dialect):
        """Сериализует Python объект в JSON строку перед сохранением"""
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return None
    
    def process_result_value(self, value, dialect):
        """Десериализует JSON строку в Python объект при чтении"""
        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {}
        return {}
    
    def copy(self, **kwargs):
        return JSONColumn()


# Модели
class Repo(Base):
    __tablename__ = 'repos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rid = Column(String(50), nullable=False, unique=True)
    url = Column(String(500), nullable=False, unique=True)
    repo_metadata = Column(JSONColumn, nullable=False, default={})
    
    # Связи с другими таблицами
    packages = relationship("Package", back_populates="repo", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Repo(id={self.id}, url={self.url})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'url': self.url
        }


class InstalledPackage(Base):
    __tablename__ = 'installed_packages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    package = Column(String(255), nullable=False, unique=True)
    package_metadata = Column(JSONColumn, nullable=False, default={})
    
    def __repr__(self):
        return f"<InstalledPackage(id={self.id}, package={self.package})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'package': self.package,
            'metadata': self.package_metadata
        }
    
    def get_metadata_value(self, key: str, default=None):
        """Получить значение из JSON метаданных"""
        return self.package_metadata.get(key, default)
    
    def set_metadata_value(self, key: str, value: Any):
        """Установить значение в JSON метаданные"""
        self.package_metadata[key] = value


class Package(Base):
    __tablename__ = 'packages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey('repos.id', ondelete='CASCADE'), nullable=False)
    pid = Column(String(50), nullable=False, unique=True)
    package_metadata = Column(JSONColumn, nullable=False, default={})
    
    # Связи
    repo = relationship("Repo", back_populates="packages")
    
    def __repr__(self):
        return f"<Package(id={self.id}, repo_id={self.repo_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'repo_id': self.repo_id,
            'metadata': self.package_metadata
        }
    
    def get_metadata_value(self, key: str, default=None):
        """Получить значение из JSON метаданных"""
        return self.package_metadata.get(key, default)
    
    def set_metadata_value(self, key: str, value: Any):
        """Установить значение в JSON метаданные"""
        self.package_metadata[key] = value


# Класс для управления базой данных
class Database:
    def __init__(self, db_url: str = "sqlite:///packages.db"):
        """
        Инициализация базы данных
        
        Args:
            db_url: URL подключения к БД (по умолчанию SQLite)
                   Примеры:
                   - SQLite: sqlite:///packages.db
                   - PostgreSQL: postgresql://user:pass@localhost/dbname
                   - MySQL: mysql+pymysql://user:pass@localhost/dbname
        """
        self.engine = create_engine(
            db_url,
            echo=False,  # SQL логирование
            pool_pre_ping=True  # Проверка соединения
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Создаем таблицы если их нет
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self) -> Session:
        """Получить новую сессию"""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """
        Контекстный менеджер для работы с сессией.
        Автоматически закрывает сессию и откатывает при ошибке.
        
        Использование:
        with db.session_scope() as session:
            session.query(Repo).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def init_db(self):
        """Создать все таблицы (если не существуют)"""
        Base.metadata.create_all(bind=self.engine)