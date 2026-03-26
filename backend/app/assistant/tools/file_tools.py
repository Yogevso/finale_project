"""AI assistant tools for uploaded file analysis."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.assistant.ollama_client import OllamaClient
from app.assistant.tools.base import BaseTool
from app.config import settings
from app.models import AssistantUploadedFile, User

logger = logging.getLogger(__name__)


def _get_user_file(
    file_id: int, user: User, db: Session,
) -> AssistantUploadedFile | None:
    return (
        db.query(AssistantUploadedFile)
        .filter(
            AssistantUploadedFile.id == file_id,
            AssistantUploadedFile.user_id == user.id,
        )
        .first()
    )


class AnalyzeUploadedFileTool(BaseTool):
    name = "analyze_uploaded_file"
    description = (
        "Analyze an uploaded file and answer questions about its content. "
        "If no question is provided, returns a summary of the file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_id": {"type": "integer", "description": "ID of the uploaded file"},
            "question": {
                "type": "string",
                "description": "Optional question to answer about the file content",
                "maxLength": 1000,
            },
        },
        "required": ["file_id"],
    }

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        file_id = params.get("file_id")
        question = params.get("question")

        record = _get_user_file(file_id, user, db)
        if not record:
            return {"success": False, "result": "", "error": "File not found or you don't have access."}

        text = record.extracted_text
        if not text:
            return {"success": False, "result": "", "error": f"No text could be extracted from '{record.original_filename}'."}

        truncated = text[:6000]
        client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.ASSISTANT_MODEL,
            timeout=settings.ASSISTANT_REQUEST_TIMEOUT,
        )

        if question:
            prompt = (
                f"Based on the following file content, answer the question.\n\n"
                f"FILE: {record.original_filename}\n---\n{truncated}\n---\n\n"
                f"QUESTION: {question}\n\n"
                f"Provide a clear, concise answer based only on the file content."
            )
        else:
            prompt = (
                f"Provide a clear summary of the following file.\n\n"
                f"FILE: {record.original_filename}\n---\n{truncated}\n---\n\n"
                f"Summarize the key points and structure of this document."
            )

        try:
            response = await client.chat([{"role": "user", "content": prompt}])
            answer = response.get("message", {}).get("content", "")
            return {"success": True, "result": answer or "No response generated."}
        except Exception:  # policy: BOUNDARY — tool should return a stable extraction error to the assistant
            logger.exception("File analysis failed")
            return {"success": False, "result": "", "error": "File analysis failed. AI service may be busy."}


class CompareFilesTool(BaseTool):
    name = "compare_files"
    description = (
        "Compare two uploaded files and highlight the key differences between them."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_id_1": {"type": "integer", "description": "ID of the first file"},
            "file_id_2": {"type": "integer", "description": "ID of the second file"},
        },
        "required": ["file_id_1", "file_id_2"],
    }

    async def execute(
        self, user: User, tenant_id: int | None, params: dict[str, Any], db: Session,
    ) -> dict[str, Any]:
        f1 = _get_user_file(params.get("file_id_1"), user, db)
        f2 = _get_user_file(params.get("file_id_2"), user, db)

        if not f1:
            return {"success": False, "result": "", "error": "First file not found or you don't have access."}
        if not f2:
            return {"success": False, "result": "", "error": "Second file not found or you don't have access."}
        if not f1.extracted_text:
            return {"success": False, "result": "", "error": f"No text from '{f1.original_filename}'."}
        if not f2.extracted_text:
            return {"success": False, "result": "", "error": f"No text from '{f2.original_filename}'."}

        text1 = f1.extracted_text[:4000]
        text2 = f2.extracted_text[:4000]
        client = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.ASSISTANT_MODEL,
            timeout=settings.ASSISTANT_REQUEST_TIMEOUT,
        )
        prompt = (
            f"Compare these two files and highlight the key differences.\n\n"
            f"FILE 1: {f1.original_filename}\n---\n{text1}\n---\n\n"
            f"FILE 2: {f2.original_filename}\n---\n{text2}\n---\n\n"
            f"Provide a structured comparison covering: content differences, "
            f"structural differences, and a brief summary of what changed."
        )
        try:
            response = await client.chat([{"role": "user", "content": prompt}])
            result = response.get("message", {}).get("content", "")
            return {"success": True, "result": result or "No response generated."}
        except Exception:  # policy: BOUNDARY — tool should return a stable extraction error to the assistant
            logger.exception("File comparison failed")
            return {"success": False, "result": "", "error": "File comparison failed. AI service may be busy."}
