from app.core.config import Settings

from .docx import DocxScreenplayVerifier, DocxVerificationSettings
from .pdf import PdfScreenplayVerifier, PdfVerificationSettings
from .screenplay import ScreenplayImportVerifier
from .text import TextScreenplayVerifier, TextVerificationSettings


def build_screenplay_verifier(settings: Settings) -> ScreenplayImportVerifier:
    text_settings = TextVerificationSettings(
        max_size_bytes=settings.document_import_max_bytes
    )
    return ScreenplayImportVerifier(
        TextScreenplayVerifier(settings.import_workspace_root, text_settings),
        DocxScreenplayVerifier(
            settings.import_workspace_root,
            DocxVerificationSettings(text=text_settings),
        ),
        PdfScreenplayVerifier(
            settings.import_workspace_root,
            PdfVerificationSettings(text=text_settings),
        ),
    )
