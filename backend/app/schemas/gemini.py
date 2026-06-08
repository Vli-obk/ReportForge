from pydantic import BaseModel, Field, field_validator


class GeminiExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, examples=["Extract insights from this PDF content..."])
    temperature: float = Field(0.3, ge=0.0, le=2.0, examples=[0.3])
    max_tokens: int = Field(1000, ge=1, le=8000, examples=[1000])

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("text cannot be empty")
        return text


class GeminiStructuredExtractRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, examples=["Extract structured data from this PDF text..."])
    temperature: float = Field(0.0, ge=0.0, le=2.0, examples=[0.0])
    max_tokens: int = Field(256, ge=32, le=8000, examples=[256])

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("text cannot be empty")
        return text


class GeminiExtractResponse(BaseModel):
    success: bool = Field(True, examples=[True])
    model: str = Field(..., examples=["gemini-1.5-mini"])
    response: str = Field("", examples=["..."])
    processing_time: float = Field(..., examples=[1.24])
    dataset_id: int | None = Field(None, examples=[5])
    dataset_name: str | None = Field(None, examples=["AI Extracted - report.pdf"])
    row_count: int = Field(0, examples=[42])
    message: str | None = Field(None, examples=["Dataset created with 42 rows."])


class GeminiStructuredExtractResponse(BaseModel):
    success: bool = Field(True, examples=[True])
    model: str = Field(..., examples=["gemini-1.5-mini"])
    data: list[dict] = Field(..., examples=[[{"field": "value"}]])
    processing_time: float = Field(..., examples=[1.24])


class GeminiErrorResponse(BaseModel):
    success: bool = Field(False, examples=[False])
    error: str = Field(..., examples=["Gemini service unavailable"])


class GeminiHealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    success: bool
    model: str
    available: bool
    model_available: bool
    error: str | None = None
