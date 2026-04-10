"""
File Extraction Service
Extracts text from uploaded PDFs and images.
"""

import logging
import io
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        result = "\n".join(text_parts).strip()
        logger.info(f"Extracted {len(result)} characters from PDF")
        return result
    except ImportError:
        raise RuntimeError("pdfplumber not installed. Run: pip install pdfplumber")
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise RuntimeError(f"Failed to extract text from PDF: {e}")


def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Extract text from an image using Tesseract OCR.
    Requires: pytesseract + Tesseract binary installed.
    """
    try:
        import pytesseract
        from PIL import Image

        image = Image.open(io.BytesIO(file_bytes))
        # Pre-processing: convert to greyscale for better OCR accuracy
        image = image.convert("L")
        text = pytesseract.image_to_string(image, lang="eng")
        logger.info(f"OCR extracted {len(text)} characters from image")
        return text.strip()
    except ImportError:
        raise RuntimeError(
            "pytesseract or Pillow not installed. Run: pip install pytesseract Pillow\n"
            "Also install Tesseract binary: https://github.com/tesseract-ocr/tesseract"
        )
    except Exception as e:
        logger.error(f"Image OCR failed: {e}")
        raise RuntimeError(f"Failed to extract text from image: {e}")


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    """
    Route to the correct extractor based on file extension.
    """
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif suffix in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        return extract_text_from_image(file_bytes)
    elif suffix == ".txt":
        return file_bytes.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: '{suffix}'. Supported: PDF, PNG, JPG, TXT")
