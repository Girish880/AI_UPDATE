# backend/agents/planner_agent.py
import logging
from typing import List, Dict, Any, Optional
import json
import os

from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

logger = logging.getLogger("PlannerAgent")


class PlannerAgent:
    """
    PlannerAgent generates candidate test cases for play.ezygamers.com.
    It uses an LLM via LangChain to propose structured, real-world QA test scenarios.
    """

    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.5):
        # ✅ Load API key from environment (recommended) or hardcode for testing
        self.api_key = ""

        if not self.api_key or self.api_key.strip() == "":
            raise RuntimeError(
                "❌ OPENAI_API_KEY not found. Please set it as an env variable or in the code."
            )

        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=self.api_key,
        )

    async def generate(
        self,
        target_url: str,
        seeds: Optional[List[str]] = None,
        n: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Generate real-world QA test cases for play.ezygamers.com.
        :param target_url: Target web app URL
        :param seeds: Optional seed ideas (user-provided)
        :param n: Number of candidate test cases to generate
        """

        logger.info("PlannerAgent generating %d test cases for %s", n, target_url)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an experienced QA test planner for online puzzle/gaming platforms. "
                    "Your job is to generate **realistic, structured test cases** for the website "
                    "'https://play.ezygamers.com'. This includes login, user onboarding, gameplay flow, "
                    "leaderboards, rewards, responsiveness, and edge cases."
                ),
                (
                    "user",
                    f"Target: {target_url}\n"
                    f"Seeds (optional): {seeds or 'none'}\n\n"
                    f"Generate {n} unique test cases as a JSON array. "
                    "Each test case **must** have the following fields:\n"
                    "- id: short unique identifier\n"
                    "- description: what the test verifies\n"
                    "- steps: ordered list of steps a tester should follow\n"
                    "- expected_result: the expected outcome if the site is working correctly\n\n"
                    "Return ONLY a valid JSON list, no explanations or commentary."
                ),
            ]
        )

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({})
            text = response.content.strip()

            # ✅ Fix common LLM formatting issues
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()

            candidates = json.loads(text)

            # ✅ Ensure list format
            if isinstance(candidates, dict):
                candidates = [candidates]

            logger.info("✅ Generated %d candidate test cases", len(candidates))
            return candidates

        except json.JSONDecodeError as je:
            logger.error("❌ Failed to parse LLM output as JSON: %s", je)
            raise RuntimeError("PlannerAgent failed to parse JSON output from LLM") from je

        except Exception as e:
            logger.error("❌ PlannerAgent LLM failed: %s", e)
            raise RuntimeError("PlannerAgent failed to generate test cases") from e
