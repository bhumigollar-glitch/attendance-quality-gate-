import os
import uuid
from pathlib import Path
from typing import Tuple
import pandas as pd
from fastapi import UploadFile, HTTPException
from app.config import settings


class FileService:
    """Handles file validation, reading, writing, and storage for spreadsheets."""

    @staticmethod
    def validate_file_metadata(file: UploadFile) -> Tuple[str, str]:
        """
        Validate file extension and basic content type.
        Returns (original_filename, extension).
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

        filename = file.filename.strip()
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext not in settings.ALLOWED_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension '{ext}'. Supported spreadsheet formats are: {allowed}",
            )

        return filename, ext

    @staticmethod
    async def save_raw_file(file: UploadFile, upload_id: str, ext: str) -> Tuple[Path, int]:
        """
        Stream and save raw uploaded file to storage, enforcing file size limits.
        Returns (saved_path, file_size_bytes).
        """
        destination = settings.RAW_STORAGE_DIR / f"{upload_id}{ext}"
        size = 0

        with open(destination, "wb") as buffer:
            while chunk := await file.read(1024 * 64):  # 64KB chunks
                size += len(chunk)
                if size > settings.MAX_FILE_SIZE_BYTES:
                    # Clean up partial file
                    if destination.exists():
                        destination.unlink()
                    max_mb = settings.MAX_FILE_SIZE_BYTES / (1024 * 1024)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds maximum allowed size of {max_mb:.1f} MB.",
                    )
                buffer.write(chunk)

        if size == 0:
            if destination.exists():
                destination.unlink()
            raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

        return destination, size

    @staticmethod
    def parse_file(file_path: Path, ext: str) -> pd.DataFrame:
        """
        Parse CSV or XLSX file into pandas DataFrame with robust encoding and type safety.
        All initial values are treated as string or object to avoid premature coercion.
        """
        try:
            if ext == ".csv":
                # Try UTF-8 first, fallback to latin-1 / ISO-8859-1
                try:
                    df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding="latin-1")
            elif ext == ".xlsx":
                df = pd.read_excel(file_path, dtype=str, keep_default_na=False, engine="openpyxl")
            else:
                raise ValueError(f"Unsupported format: {ext}")

            return df
        except Exception as e:
            raise ValueError(f"Failed to parse spreadsheet file: {str(e)}")

    @staticmethod
    def save_cleaned_file(df: pd.DataFrame, upload_id: str, ext: str) -> Path:
        """
        Save cleaned DataFrame to the cleaned storage directory.
        """
        cleaned_path = settings.CLEANED_STORAGE_DIR / f"{upload_id}_cleaned{ext}"
        if ext == ".csv":
            df.to_csv(cleaned_path, index=False, encoding="utf-8")
        elif ext == ".xlsx":
            df.to_excel(cleaned_path, index=False, engine="openpyxl")
        return cleaned_path
