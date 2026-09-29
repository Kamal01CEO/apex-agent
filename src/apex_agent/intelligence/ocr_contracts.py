"""PaddleOCR & PyMuPDF Contract & Invoice Structured Scanner for Apex Agent."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import fitz  # PyMuPDF

logger = logging.getLogger("apex_agent.ocr")


class ContractInvoiceOCRScanner:
    """Extracts text, financial figures, and structured agreement metadata from scanned PDFs/invoices."""

    def __init__(self):
        self._ocr = None

    def _get_ocr(self):
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except Exception as e:
                logger.warning("PaddleOCR engine fallback: %s", e)
                self._ocr = False
        return self._ocr

    def scan_document(self, file_path: Path) -> Dict[str, Any]:
        """Extracts text via PyMuPDF + PaddleOCR fallback for scanned pages."""
        p = Path(file_path).resolve()
        if not p.exists():
            return {"status": "error", "error": f"File not found: {p}"}

        doc_text_parts = []
        doc = fitz.open(str(p))

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text().strip()

            # If page has digital text, extract it
            if len(text) > 40:
                doc_text_parts.append(f"[Page {page_idx+1}]\n{text}")
            else:
                # Scanned image page -> run PaddleOCR
                ocr_engine = self._get_ocr()
                if ocr_engine:
                    try:
                        pix = page.get_pixmap(dpi=150)
                        temp_img = p.parent / f"_temp_page_{page_idx}.png"
                        pix.save(str(temp_img))

                        result = ocr_engine.ocr(str(temp_img), cls=True)
                        lines = []
                        if result and result[0]:
                            for line in result[0]:
                                lines.append(line[1][0])
                        if temp_img.exists():
                            temp_img.unlink()

                        doc_text_parts.append(f"[Page {page_idx+1} (OCR)]\n" + "\n".join(lines))
                    except Exception as e:
                        logger.error("OCR scan error on page %d: %s", page_idx+1, e)

        full_text = "\n\n".join(doc_text_parts)
        doc.close()

        # Extract structured contract/invoice metadata
        metadata = self._extract_contract_fields(full_text, p.name)
        return {
            "status": "success",
            "file": p.name,
            "text": full_text,
            "structured_metadata": metadata
        }

    def _extract_contract_fields(self, text: str, filename: str) -> Dict[str, Any]:
        """Parses key contract/invoice fields."""
        meta = {
            "document_name": filename,
            "detected_type": "contract" if any(w in text.lower() for w in ("agreement", "contract", "terms", "party")) else "invoice",
            "parties": [],
            "payment_terms": "Not specified",
            "deal_value": "Not specified"
        }

        # Payment terms heuristic
        low = text.lower()
        if "net 15" in low: meta["payment_terms"] = "Net 15 Days"
        elif "net 30" in low: meta["payment_terms"] = "Net 30 Days"
        elif "net 45" in low: meta["payment_terms"] = "Net 45 Days"
        elif "net 60" in low: meta["payment_terms"] = "Net 60 Days"

        # Values
        amounts = re.findall(r"\$[\d,]+(?:\.\d{2})?", text)
        if amounts:
            meta["deal_value"] = amounts[0]

        return meta
