from sqlalchemy import Column, Index, String, Float, DateTime, BigInteger
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


Base = declarative_base()


class NewFileInfo(Base):

    __tablename__ = "new_file_info"

    file_id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    extension = Column(String, nullable=False)
    path_file = Column(String, nullable=False)
    size = Column(Float, nullable=False)
    date_create = Column(DateTime, default=datetime.now())
    date_change = Column(DateTime, nullable=True)
    comment = Column(String, nullable=True)

    class Config:
        arbitrary_types_allowed = True


Index("ix_file_name_path_new", NewFileInfo.name, NewFileInfo.path_file)


class FileInfoResponse(BaseModel):
    file_id: int = Field(..., description="ID файла в базе данных")
    name: str = Field(..., description="Название файла")
    extension: str = Field(..., description="Расширение файла")
    path_file: str = Field(..., description="Путь до файла")
    size: float = Field(..., description="Размер файла")
    date_create: datetime = Field(..., description="Дата создания записи в БД")
    date_change: Optional[datetime] = Field(None, description="Дата изменения файла")
    comment: Optional[str] = Field(None, description="Комментарий к файлу")

    class Config:
        orm_mode = True
        from_attributes = True


class FileInfoListResponse(BaseModel):
    file_amount: int = Field(
        description="Количество файлов",
    )
    total_size: float = Field(
        description="Общий размер файлов",
    )
    items: List[FileInfoResponse]

    class Config:
        from_attributes = True


class DirectoryRequest(BaseModel):
    directory_name: str = Field(
        description="Папка с файлами",
    )

    class Config:
        from_attributes = True


class FileInfoUpdate(BaseModel):
    file_id: int = Field(..., description="ID файла в базе данных")
    new_name: Optional[str] = Field(
        None,
        description="Новое имя файла",
    )
    new_path_file: Optional[str] = Field(
        None,
        description="Новый путь, где будет сохранен файл (если требуется изменить)",
    )
    comment: Optional[str] = Field(
        None,
        description="Комментарий к файлу",
    )

    class Config:
        from_attributes = True
