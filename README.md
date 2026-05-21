# OCR Order Automation System

An intelligent document-processing and order automation system that extracts structured data from invoices, receipts, images, and PDF documents using OCR and AI-powered validation.

The project is currently under active development and testing.

---

## Project Overview

Businesses often receive orders through WhatsApp images, scanned invoices, handwritten receipts, and PDF documents. Manual data entry is time-consuming and prone to human errors.

This system automates the entire process by:

1. Receiving documents (images/PDFs)
2. Extracting text using OCR
3. Cleaning and preprocessing extracted content
4. Validating data using LLM-powered workflows
5. Generating structured JSON output
6. Automatically updating Google Sheets
7. Providing API responses for further integrations

---

## Architecture

Input Documents
(Image / Invoice / Receipt / PDF)

↓

Image Processing

↓

OCR Engine

↓

Text Extraction

↓

AI Validation Layer (LangChain + LLM)

↓

Structured Data Generation

↓

FastAPI Backend

↓

Google Sheets Integration

↓

Business Dashboard / API Response

---

## Features

### OCR Extraction

- Image text extraction
- PDF text extraction
- Invoice processing
- Receipt processing

### Data Processing

- Text cleaning
- Field normalization
- Missing value handling
- Structured JSON generation

### AI Validation

- LLM-assisted validation
- Error detection
- Data consistency checks
- Business rule validation

### Automation

- Google Sheets integration
- Automatic order recording
- API-based workflows
- Future ERP integrations

### Backend APIs

- FastAPI architecture
- RESTful endpoints
- JSON responses
- Modular service structure

---

## Technology Stack

### Backend

- Python
- FastAPI

### OCR

- Tesseract OCR
- OpenCV

### AI

- LangChain
- Gemini / OpenAI Models

### Data Processing

- Pandas
- NumPy

### Integrations

- Google Sheets API

### Deployment

- Docker (Planned)
- Render (Planned)

---

## Current Development Status

### Completed

- OCR pipeline implementation
- Image preprocessing module
- Text extraction workflow
- FastAPI backend setup
- Google Sheets integration
- Basic validation pipeline

### In Progress

- LLM validation improvements
- Multi-document support
- Accuracy optimization
- Automated testing
- Error handling enhancements

### Planned Features

- Web dashboard
- User authentication
- ERP integration
- Analytics module
- Multi-language OCR
- Batch processing

---

## Example Workflow

1. User uploads invoice image
2. OCR extracts raw text
3. AI validates extracted information
4. Structured JSON is generated
5. Order details are pushed to Google Sheets
6. API returns processed result

---

## Sample Output

```json
{
  "customer_name": "ABC Traders",
  "invoice_number": "INV-1025",
  "items": [
    {
      "product": "Product A",
      "quantity": 10,
      "price": 250
    }
  ],
  "total_amount": 2500
}
```

---

## Project Goals

- Reduce manual data entry
- Improve processing speed
- Minimize human errors
- Automate business workflows
- Create reusable document-processing APIs

---

## Folder Structure

```
project/
│
├── api/
├── services/
├── ocr/
├── validators/
├── sheets/
├── models/
├── tests/
├── configs/
│
├── main.py
├── requirements.txt
└── README.md
```

---

## Disclaimer

This project is currently in the testing phase and under active development. Features, architecture, and integrations may change as the system evolves.

---

## Author

Ritik Chauhan

AI & Machine Learning Engineer

LinkedIn:
https://www.linkedin.com/in/ritik-chauhan-06b279211/

Portfolio:
https://voluble-panda-3a9ee0.netlify.app/
