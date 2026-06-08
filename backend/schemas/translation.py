from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


SupportedLanguage = Literal["id", "jv", "mad"]
PolitenessLevel = Literal["low", "high"]


class TranslationRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source_lang: SupportedLanguage
    target_lang: SupportedLanguage
    level: PolitenessLevel

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Teks tidak boleh kosong")
        return value

    @model_validator(mode="after")
    def validate_language_pair(self) -> "TranslationRequest":
        if self.source_lang != "id" and self.target_lang != "id" and self.source_lang != self.target_lang:
            raise ValueError("Terjemahan antarbahasa daerah harus melalui Bahasa Indonesia")
        return self


class TranslationResponse(BaseModel):
    translatedText: str
    politenessLevel: str
    ngokoPercentage: float
    kramaPercentage: float
    context: str
    alternativeText: str | None = None


class PopularWord(BaseModel):
    word: str
    language: str
    count: int


class InsightMetrics(BaseModel):
    total_vocabulary: int
    active_contributors: int
    vitality_status: str
    preservation_accuracy: str | None
    total_translations: int


class VitalityTrends(BaseModel):
    years: list[str]
    jv_scores: list[int]
    mad_scores: list[int]


class InsightsResponse(BaseModel):
    metrics: InsightMetrics
    popular_words: list[PopularWord]
    vitality_trends: VitalityTrends
