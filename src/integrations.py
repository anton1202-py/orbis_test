import os
from pathlib import Path
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from database import DATABASE_URL
from models import NewFileInfo

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class SyncFileWithDb:
    """Синхронизация файлов с базой данных"""

    def __init__(self):
        self.db = SessionLocal()

    def _add_files(self, directory: str) -> None:
        """Добавлет файлы в БД"""

        files_to_insert = []
        for root, dirs, files in os.walk(directory):
            # Сравниваю, есть ли в файловой системе файлы, которые есть в БД.
            # Если нет - удаляю из БД
            data = (
                self.db.query(NewFileInfo)
                .filter(NewFileInfo.path_file == str(root).replace("\\", "/"))
                .all()
            )
            if data:
                for file_obj in data:
                    common_file_path = (
                        f"{file_obj.path_file}/{file_obj.name}{file_obj.extension}"
                    )
                    if not os.path.exists(common_file_path):
                        self.db.delete(file_obj)

            # Записываю в БД файлы, которые еще не записаны
            for i, file in enumerate(files):
                common_file_data = Path(file)
                path_with_file_and_extension = os.path.join(root, file)

                file_path = str(Path(path_with_file_and_extension).parent).replace(
                    "\\", "/"
                )
                file_name = common_file_data.stem
                file_extension = common_file_data.suffix
                file_size = round(
                    os.path.getsize(path_with_file_and_extension) / 1024, 2
                )

                if (
                    not self.db.query(NewFileInfo)
                    .filter(
                        NewFileInfo.name == str(file_name),
                        NewFileInfo.path_file == file_path,
                    )
                    .first()
                ):
                    db_file_info = NewFileInfo(
                        name=str(file_name),
                        extension=str(file_extension),
                        path_file=file_path,
                        size=file_size,
                    )
                    files_to_insert.append(db_file_info)
                if (len(files_to_insert) >= 7000 and i < (len(files) - 2)) or (
                    i == (len(files) - 1) and files_to_insert
                ):
                    self.db.bulk_save_objects(files_to_insert)
                    self.db.commit()
                    files_to_insert = []

    def _del_files_from_db(self, directory: str) -> None:
        """Удаляет файлы из БД, если нет в файловом хранилище"""
        for root, dirs, files in os.walk(directory):
            # Сравниваю, есть ли в файловой системе файлы, которые есть в БД.
            # Если нет - удаляю из БД
            data = (
                self.db.query(NewFileInfo)
                .filter(NewFileInfo.path_file == str(root).replace("\\", "/"))
                .all()
            )
            if data:
                for file_obj in data:
                    common_file_path = (
                        f"{file_obj.path_file}/{file_obj.name}{file_obj.extension}"
                    )
                    if not os.path.exists(common_file_path):
                        self.db.delete(file_obj)
                        self.db.commit()

    def sync_local_storage_with_db(self, directory):
        """Синхронизирует локальное хранилище файлов с базой данных"""
        self._add_files(directory)
        self._del_files_from_db(directory)
