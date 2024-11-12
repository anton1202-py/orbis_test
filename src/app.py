import os
from fastapi import APIRouter, Depends, FastAPI, Form, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from database import DATABASE_URL
from models import (
    DirectoryRequest,
    FileInfoListResponse,
    FileInfoResponse,
    FileInfoUpdate,
    NewFileInfo,
)
from views import FileUpdateUploadDelView, FileInfoView
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine

app = FastAPI()
router = APIRouter()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post(
    "/sync",
    response_model=FileInfoListResponse,
    summary="Синхронизация базы данных с папкой",
    description="""
    Показывает файлы, которые есть в введенной папке. Если файлы из этой папки
    есть в базе, но нет в локальном хранилище - они удалятся из базы
    """,
)
def sync_files(
    request: DirectoryRequest,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    try:
        file_view = FileInfoView(db)
        files = file_view.synch_files(
            request.directory_name, offset=offset, limit=limit
        )
        file_amount = (
            db.query(NewFileInfo)
            .filter(NewFileInfo.path_file.like(f"%{request.directory_name}%"))
            .count()
        )
        # Подсчитываем общий объем файлов
        # Предполагается, что у вас есть поле size в NewFileInfo
        total_size = sum(file.size for file in files)
        # Преобразуем объекты NewFileInfo в FileInfoResponse
        file_info_responses = [FileInfoResponse.model_validate(file) for file in files]

        return FileInfoListResponse(
            file_amount=file_amount, total_size=total_size, items=file_info_responses
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/files/",
    response_model=FileInfoListResponse,
    summary="Информация по всем файлам",
    description="""
        Для получения полного списка файлов используйте 
        пагинацию с помощью **limit** и **offset**.  
        **limit** - число строк, выдаваемое на странице  
        **offset** - пропустить количество строк  
    """,
)
def read_items(offset: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        file_view = FileInfoView(db)
        # Получаем список файлов
        files = file_view.get_items(offset=offset, limit=limit)
        # Подсчитываем общее количество файлов
        file_amount = db.query(NewFileInfo).count()
        # Подсчитываем общий объем файлов
        # Предполагается, что у вас есть поле size в NewFileInfo
        total_size = sum(file.size for file in files)
        # Преобразуем объекты NewFileInfo в FileInfoResponse
        file_info_responses = [FileInfoResponse.model_validate(file) for file in files]
        return FileInfoListResponse(
            file_amount=file_amount, total_size=total_size, items=file_info_responses
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/files/{file_id}",
    response_model=FileInfoResponse,
    summary="Информация по одному файлу",
)
def read_item(file_id: int, db: Session = Depends(get_db)):
    try:
        file_view = FileInfoView(db)
        file = file_view.get_item(file_id)
        return FileInfoResponse.model_validate(file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/file/{file_id}/download",
    response_class=FileResponse,
    summary="Скачивание файла в локальное хранилище",
)
def download_file(file_id: int, db: Session = Depends(get_db)):
    """Скачивание файла по ссылке"""
    try:
        file_data = FileInfoView(db)
        file = file_data.get_item(file_id)
        file_path = f"{file.path_file}/{file.name}{file.extension}"

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/octet-stream",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/file/upload/",
    response_model=FileInfoResponse,
    summary="Загрузка файла",
    description="""
    Загружает файл в файловую ситему и базу данных.  
    **upload_path** - путь до папки, в которую нужно загрузить файл.
    По умолчанию загружается в C:/upload/
    """,
)
def upload_file(
    file: UploadFile = File(...),
    upload_path: str = Form("C:/upload/"),
    db: Session = Depends(get_db),
):
    try:
        file_view = FileUpdateUploadDelView(db)
        uploaded_file_info = file_view.upload_file(file, upload_path)
        return FileInfoResponse.model_validate(uploaded_file_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/files/by_directory/",
    response_model=FileInfoListResponse,
    summary="Получение информации по всем файлам в указанной папке",
    description="""
    Показывает файлы, которые есть в введенной папке (все файлы, дочерние тоже)
    **directory_name** - путь до папки.
    """,
)
def read_items_by_directory(
    request: DirectoryRequest,
    offset: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    try:
        directory_name = request.directory_name
        file_view = FileInfoView(db)
        # Получаем список файлов по названию папки
        files = file_view.get_items_by_folder(
            directory_name, offset=offset, limit=limit
        )
        # Подсчитываем общее количество файлов в этой папке
        file_amount = (
            db.query(NewFileInfo)
            .filter(NewFileInfo.path_file.like(f"%{directory_name}%"))
            .count()
        )
        # Подсчитываем общий объем файлов в этой папке
        # Предполагается, что у вас есть поле size в NewFileInfo
        total_size = sum(file.size for file in files)
        # Преобразуем объекты NewFileInfo в FileInfoResponse
        file_info_responses = [FileInfoResponse.model_validate(file) for file in files]

        return FileInfoListResponse(
            file_amount=file_amount, total_size=total_size, items=file_info_responses
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/files/",
    response_model=FileInfoResponse,
    summary="Обновление информации о файле",
)
def update_file(update_request: FileInfoUpdate, db: Session = Depends(get_db)):
    try:
        file_info_view = FileUpdateUploadDelView(db)
        updated_file = file_info_view.update_item(
            file_id=update_request.file_id,
            new_name=update_request.new_name,
            new_comment=update_request.comment,
            new_path_file=update_request.new_path_file,
        )
        return updated_file
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/files/{file_id}",
    response_model=dict,
    summary="Удаление файла",
    description="""
    Удаляет файл из базы данных и из файловой системы.  
    """,
)
def delete_item(file_id: int, db: Session = Depends(get_db)):
    try:
        file_data = FileUpdateUploadDelView(db)
        file_data.delete_item(file_id)
        return {"detail": "Файл успешно удален"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Подключаем маршруты из класса представления
app.include_router(router)
