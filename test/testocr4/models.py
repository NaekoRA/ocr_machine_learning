from pydantic import BaseModel, Field
from typing import List, Optional

class OCRResult(BaseModel):
    name: Optional[str]
    quantity: Optional[float]
    price: Optional[float]
    total: Optional[float]
    Final_accuracy: Optional[float]
    text_accuracy: Optional[float]
    price_accuracy: Optional[float]
    keywords: List[str] = []

class ItemMatched(BaseModel):
    id: Optional[int]
    name: Optional[str]
    harga_di_datapusat: Optional[float]
    ocr_result: OCRResult

class Merchant(BaseModel):
    name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]

class FinalOutput(BaseModel):
    invoice_number: Optional[str]
    tanggal: Optional[str]
    merchant: Merchant
    items: List[ItemMatched]
    grand_total: Optional[float]

class KeywordUpdate(BaseModel):
    keyword: str = Field(..., min_length=1)
    normalized_value: str = Field(..., min_length=1)
