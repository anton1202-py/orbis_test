from datetime import datetime
import os
from fastapi import HTTPException, UploadFile
from models import NewFileInfo
from typing import List, Optional
from sqlalchemy.orm import Session
from integrations import SyncFileWithDb


class FileInfoView(SyncFileWithDb):
    def __init__(self, db: Session):
        self.db = db

    def synch_files(self, directory_name: str, offset: int = 0, limit: int = 100):
        """Синхронизация выбранной папки с базой данных"""
        self.sync_local_storage_with_db(directory_name)
        return (
            self.db.query(NewFileInfo)
            .filter(NewFileInfo.path_file.like(f"%{directory_name}%"))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_items(self, offset: int = 0, limit: int = 100) -> List[NewFileInfo]:
        """Выдает данные по всем файлам"""
        return self.db.query(NewFileInfo).offset(offset).limit(limit).all()

    def get_item(self, file_id: int) -> NewFileInfo:
        """Получает информацию по одному файлу"""
        file_obj = (
            self.db.query(NewFileInfo).filter(NewFileInfo.file_id == file_id).first()
        )
        if file_obj is None:
            raise HTTPException(status_code=404, detail="Файл не найден")
        return file_obj

    def get_items_by_folder(
        self, directory_name: str, offset: int = 0, limit: int = 100
    ) -> List[NewFileInfo]:
        """Выдает файлы из запрошенной папки"""
        return (
            self.db.query(NewFileInfo)
            .filter(NewFileInfo.path_file.like(f"%{directory_name}%"))
            .offset(offset)
            .limit(limit)
            .all()
        )


class FileUpdateUploadDelView:
    def __init__(self, db: Session):
        self.db = db

    def update_item(
        self,
        file_id: int,
        new_name: Optional[str] = None,
        new_path_file: Optional[str] = None,
        new_comment: Optional[str] = None,
    ):
        """Обновляет информацию о файле"""
        file_obj = (
            self.db.query(NewFileInfo).filter(NewFileInfo.file_id == file_id).first()
        )
        if file_obj is None:
            raise HTTPException(status_code=404, detail="Файл не найден")

        old_file_path = f"{file_obj.path_file}/{file_obj.name}{file_obj.extension}"
        update_name = file_obj.name
        update_path = file_obj.path_file
        update_comment = file_obj.comment
        # Обновляем поля, если есть чем
        if new_name:
            update_name = new_name
        if new_comment:
            update_comment = new_comment
        if new_path_file:
            update_path = new_path_file

        file_obj.name = update_name
        file_obj.path_file = update_path
        file_obj.comment = update_comment
        if update_name == new_name or update_path == new_path_file:
            file_obj.date_change = datetime.now()  # Обновляем дату изменения
        # Сохраняем изменения в базе данных
        self.db.commit()
        # Путь к новому файлу
        new_file_path = f"{file_obj.path_file}/{file_obj.name}{file_obj.extension}"
        # Переименовываем или перемещаем файл в файловой системе
        if os.path.exists(old_file_path):
            os.rename(old_file_path, new_file_path)  # Перемещаем файл
        else:
            raise HTTPException(status_code=404, detail="Файл не найден")

        return file_obj

    def upload_file(self, file: UploadFile, upload_path: str) -> NewFileInfo:
        """Загружаем файл на сервер и сохраняем информацию в базе данных"""
        # Определите путь для сохранения файла
        if not upload_path:
            upload_path = "C:/upload/"
        os.makedirs(upload_path, exist_ok=True)

        # Сохраните файл на сервере
        file_location = os.path.join(upload_path, file.filename)
        with open(file_location, "wb+") as file_object:
            file_object.write(file.file.read())

        # Создайте объект NewFileInfo и заполните его данными
        new_file_info = NewFileInfo(
            name=file.filename,
            path_file=upload_path,
            extension=os.path.splitext(file.filename)[1],
            size=os.path.getsize(file_location),  # Получаем размер файла
        )

        # Сохраните информацию о файле в базе данных
        self.db.add(new_file_info)
        self.db.commit()
        self.db.refresh(new_file_info)

        return new_file_info

    def delete_item(self, file_id: int):
        """Удаляем файл из базы данных и файлового хранилища"""
        file_obj = (
            self.db.query(NewFileInfo).filter(NewFileInfo.file_id == file_id).first()
        )
        if file_obj is None:
            raise HTTPException(status_code=404, detail="Файл не найден")

        # Удаляем файл из файлового хранилища
        file_path = f"{file_obj.path_file}/{file_obj.name}{file_obj.extension}"
        if os.path.exists(file_path):
            os.remove(file_path)  # Удаляем файл с диска
        else:
            raise HTTPException(status_code=404, detail="Файл не найден а базе данных")

        # Удаляем запись из базы данных
        self.db.delete(file_obj)
        self.db.commit()
