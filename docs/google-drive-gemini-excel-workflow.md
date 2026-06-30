# Workflow: Google Drive → Gemini → Excel → EOD Report

## Objective
Automate the extraction of WhatsApp-related documents or images stored in Google Drive, send them through Gemini for OCR and classification, store the results in Excel, and produce an end-of-day report in Google Drive.

## Target Flow
1. Read files from a Google Drive folder.
2. Send files to Gemini for OCR and structured extraction.
3. Automatically categorize each record as:
   - Expense
   - Delivery Challan
   - Other / Needs Review
4. Append the results to an Excel workbook.
5. Generate an EOD summary report.
6. Save the summary report back to Google Drive.

## Suggested Folder Structure in Google Drive
- Incoming/WhatsApp
- Processed/Completed
- Processed/Failed
- Reports/EOD
- Reports/Excel

## Data Fields to Extract
For each document, extract:
- Source file name
- Date
- Vendor or customer name
- Amount
- Reference number
- Document type
- Category
- Notes

## Classification Rules
Use the following logic for auto-categorization:
- Expense
  - Keywords: bill, invoice, payment, receipt, fuel, food, travel, office expense
- Delivery Challan
  - Keywords: challan, delivery, dispatch, waybill, shipment, consignment
- Needs Review
  - Anything that does not clearly match the above categories

## Gemini OCR Prompt Template
Use a prompt like this for each document:

"Extract text from this document. Return the result in JSON with the following fields: date, vendor, amount, reference_number, document_type, category, notes. If the document is an expense, classify it as Expense. If it is a delivery-related document, classify it as Delivery Challan. If unclear, classify it as Needs Review."

## Excel Output Structure
Create or update an Excel sheet with these columns:
- Date
- Category
- Vendor / Customer
- Amount
- Reference Number
- Document Type
- Notes
- Source File
- Status

## EOD Report Output
Generate a daily report containing:
- Total number of records processed
- Total expenses
- Total delivery challans
- Number of records requiring review
- Summary by category
- Link to the Excel workbook

## Recommended Automation Stack
- Google Drive API
- Gemini API or Gemini in Google AI Studio
- Python with pandas and openpyxl
- Google Sheets or Excel workbook export

## Example Process Flow
1. Pull files from the Google Drive input folder.
2. For each file:
   - Read the file from Drive
   - Send it to Gemini for OCR
   - Extract structured fields
   - Classify the record
   - Append to Excel
3. Move processed files to the archive folder.
4. Generate the EOD report.
5. Upload the report to the Google Drive reports folder.

## Operational Notes
- Run this workflow daily or on a fixed schedule.
- Keep a log of failed files for manual follow-up.
- Review low-confidence classifications before finalizing the EOD report.
