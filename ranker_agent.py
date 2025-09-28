# backend/agents/ranker_agent.py
import logging
from typing import List, Dict, Any
import json
import re

from langchain_openai import ChatOpenAI   # ✅ use correct package
from langchain.prompts import ChatPromptTemplate

logger = logging.getLogger("RankerAgent")


class RankerAgent:
    """
    RankerAgent evaluates candidate test cases and selects the top_k most useful.
    Uses an LLM via LangChain.
    """

    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.3):
        # --- Directly set your API key here ---
        self.api_key = ""

        if not self.api_key:
            raise RuntimeError("❌ OPENAI_API_KEY not found.")

        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=self.api_key,
        )

    async def rank_and_select(
        self, candidates: List[Dict[str, Any]], top_k: int = 10
    ) -> List[Dict[str, Any]]:
        logger.info(
            "RankerAgent ranking %d candidates; selecting top %d", len(candidates), top_k
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a QA strategist. Rank the given test cases by importance, "
                    "coverage, and ability to find bugs in puzzle games. "
                    "Return ONLY a JSON array of test cases. No explanations, no text outside JSON."
                ),
                (
                    "user",
                    "Here are the candidate test cases:\n{candidates}\n\n"
                    "Select the top {top_k} most promising ones and return only them as JSON."
                ),
            ]
        )

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({
                "candidates": json.dumps(candidates, indent=2),
                "top_k": top_k
            })

            text = response.content.strip()
            if not text:
                raise ValueError("LLM returned empty response")

            # --- Clean JSON if wrapped in ```json ... ``` ---
            if text.startswith("```"):
                text = re.sub(r"^```(json)?", "", text)
                text = re.sub(r"```$", "", text).strip()

            # --- Try to parse JSON ---
            try:
                top_candidates = json.loads(text)
            except json.JSONDecodeError:
                logger.error("LLM output was not valid JSON:\n%s", text)
                raise

            # Ensure a list is returned
            if isinstance(top_candidates, dict):
                top_candidates = [top_candidates]

            return top_candidates

        except Exception as e:
            logger.error("❌ RankerAgent LLM failed: %s", e)
            raise RuntimeError("RankerAgent failed to rank candidates using LLM") from e
