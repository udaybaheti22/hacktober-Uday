"""Verify every skillcapture module imports cleanly."""
from dotenv import load_dotenv
load_dotenv()

print("Importing schema...")
from skillcapture.schema import Procedure, ProcedureStep, SourceRef
print("  OK")

print("Importing transcribe...")
from skillcapture.transcribe import (
    get_whisper_model, transcribe_audio_with_model, segments_to_annotated_text
)
print("  OK")

print("Importing extract_pdf...")
from skillcapture.extract_pdf import extract_pdf, get_docling_converter
print("  OK")

print("Importing synthesize...")
from skillcapture.synthesize import synthesize_procedure, GEMMA_MODEL
print(f"  OK — model: {GEMMA_MODEL}")

print("Importing export...")
from skillcapture.export import procedure_to_markdown
print("  OK")

print("\nAll imports OK. Run: streamlit run app.py")
