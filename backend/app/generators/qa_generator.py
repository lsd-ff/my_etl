"""Rule-based QA generation with pluggable LLM seams."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.generators.context_generator import ContextGenerator, MockLLM, OpenAICompatibleLLM
from app.generators.keyword_generator import KeywordGenerator
from app.schemas.qa_record import Chunk, QARecord


@dataclass(frozen=True)
class GeneratedQA:
    question: str
    answer: str
    context: str
    keywords: str


class QAGenerator:
    def __init__(
        self,
        context_generator: ContextGenerator | None = None,
        keyword_generator: KeywordGenerator | None = None,
        llm: MockLLM | None = None,
    ) -> None:
        self.provider = settings.llm_provider
        if self.provider == "mock":
            self.llm = llm or MockLLM()
        elif self.provider in {"openai", "autodl", "openai_compatible", "deepseek", "ollama"}:
            self.llm = OpenAICompatibleLLM()
        else:
            raise NotImplementedError(f"Unsupported LLM provider: {self.provider}")
        self.context_generator = context_generator or ContextGenerator(self.llm)
        self.keyword_generator = keyword_generator or KeywordGenerator()

    def generate_for_chunk(
        self,
        chunk: Chunk,
        source: str,
        file_type: str,
        file_hash: str,
        id_pad_width: int = 0,
    ) -> list[QARecord]:
        payloads = self.generate_json_for_chunk(chunk)
        records: list[QARecord] = []
        for index, payload in enumerate(payloads, start=1):
            records.append(
                QARecord(
                    doc_id=chunk.doc_id,
                    chunk_id=chunk.chunk_id,
                    chunk_index=chunk.chunk_index,
                    qa_index=index,
                    question=str(payload["question"]),
                    answer=str(payload["answer"]),
                    context=str(payload["context"]),
                    keywords=str(payload["keywords"]),
                    source=source,
                    file_type=file_type,
                    page=chunk.page,
                    section=chunk.section,
                    file_hash=file_hash,
                    chunk_hash=chunk.chunk_hash,
                    id_pad_width=id_pad_width,
                )
            )
        return records

    def generate_json_for_chunk(self, chunk: Chunk) -> list[dict[str, Any]]:
        if len(chunk.content.strip()) < 40:
            return []
        if self.provider != "mock":
            return self._generate_with_llm(chunk)

        context = self.context_generator.generate(chunk.content)
        keywords = self.keyword_generator.generate(chunk.content)
        topic = self._topic(chunk.content, keywords)
        answers = self._answers(chunk.content)
        specs = self._question_specs(topic)
        count = min(len(specs), max(1, min(5, len(answers))))

        payloads: list[dict[str, Any]] = []
        for index, question in enumerate(specs[:count], start=1):
            answer = answers[(index - 1) % len(answers)]
            payloads.append(
                {
                    "question": question,
                    "answer": answer,
                    "context": context,
                    "keywords": keywords,
                    "evidence": answer,
                    "answer_type": self._answer_type_from_question(question),
                    "confidence": "0.85",
                }
            )
        return payloads

    def _generate_with_llm(self, chunk: Chunk) -> list[dict[str, Any]]:
        prompt = f"""
请基于下面的文档片段生成 QA 类型 RAG 数据。只输出一个合法 JSON 对象，不要输出 Markdown。

要求：
1. context 是 150 到 400 字的详细语义增强描述，不是普通摘要。
2. keywords 是 5 到 12 个关键词，用英文逗号或中文逗号分隔的字符串，不要数组。
3. qas 生成 1 到 5 条，问题类型尽量覆盖定义、原理、作用、应用、对比、步骤。
4. 如果信息量不足，可以少生成。
5. answer 必须基于原文，不要编造。
6. 每条 QA 必须给 evidence，evidence 是文档片段中的原文证据句或短段。
7. answer_type 只能是：定义、原理、作用、应用、对比、步骤、事实、限制。
8. confidence 是 0 到 1 的数字，表示答案由原文支撑的置信度。

JSON 格式：
{{
  "context": "...",
  "keywords": "关键词1,关键词2,关键词3",
  "qas": [
    {{"question": "...", "answer": "...", "evidence": "...", "answer_type": "定义", "confidence": 0.9}}
  ]
}}

文档片段：
{chunk.content}
""".strip()
        raw = self.llm.complete(prompt)
        data = self._parse_json_object(raw)
        context = str(data.get("context") or "").strip()
        keywords = str(data.get("keywords") or "").strip()
        qas = data.get("qas") or data.get("qa") or []
        if not isinstance(qas, list):
            return []
        payloads: list[dict[str, Any]] = []
        for item in qas[:5]:
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            answer = str(item.get("answer") or "").strip()
            evidence = str(item.get("evidence") or "").strip()
            answer_type = str(item.get("answer_type") or "").strip()
            confidence = str(item.get("confidence") or "").strip()
            item_context = str(item.get("context") or context).strip()
            item_keywords = str(item.get("keywords") or keywords).strip()
            if question and answer and item_context and item_keywords:
                payloads.append(
                    {
                        "question": question,
                        "answer": answer,
                        "context": item_context,
                        "keywords": item_keywords,
                        "evidence": evidence,
                        "answer_type": answer_type,
                        "confidence": confidence,
                    }
                )
        return payloads

    @staticmethod
    def _parse_json_object(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
        data = __import__("json").loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("LLM response JSON must be an object.")
        return data

    @staticmethod
    def _topic(text: str, keywords: str) -> str:
        if keywords:
            return keywords.split(",")[0]
        first = re.split(r"[。！？!?\n]", text.strip())[0]
        return first[:24] or "该内容"

    @staticmethod
    def _answers(text: str) -> list[str]:
        compact = re.sub(r"\s+", " ", text).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+", compact) if len(s.strip()) >= 12]
        if not sentences:
            return [compact[:220]]
        return [sentence[:260] for sentence in sentences[:5]]

    @staticmethod
    def _question_specs(topic: str) -> list[str]:
        return [
            f"什么是{topic}？",
            f"{topic}的核心原理是什么？",
            f"{topic}有什么作用？",
            f"{topic}适用于哪些场景？",
            f"{topic}与相关概念有什么区别？",
            f"使用{topic}的一般步骤是什么？",
        ]

    @staticmethod
    def _answer_type_from_question(question: str) -> str:
        if "步骤" in question:
            return "步骤"
        if "原理" in question:
            return "原理"
        if "作用" in question:
            return "作用"
        if "场景" in question:
            return "应用"
        if "区别" in question:
            return "对比"
        if "什么是" in question:
            return "定义"
        return "事实"
