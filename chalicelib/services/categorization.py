import json
import time
from functools import lru_cache
from typing import Any, Dict

from aws_lambda_powertools import Logger
from openai import OpenAI

from chalicelib import constants
from chalicelib.models import config

logger = Logger(child=True)
openai_client = OpenAI()

__all__ = ["CategorizationService"]


class CategorizationService:
    """
    Service for auto-categorizing expenses using OpenAI's GPT model.
    Provides intelligent expense categorization with retry logic and caching.
    """

    def __init__(self):
        """
        Initialize the CategorizationService with OpenAI client and configuration.
        """
        self.model = "gpt-4o-mini"
        self.max_retries = 3
        self.retry_delay = 1
        self._client = OpenAI(api_key=config.openai_api_key.get_secret_value())

    @lru_cache(maxsize=64)
    def categorize_expense(self, parsed_receipt: str) -> str:
        """
        Categorize an expense using OpenAI's GPT model with JSON structured output.

        Uses LRU cache for performance optimization and implements exponential backoff
        for handling API rate limits and temporary failures.

        :param parsed_receipt: The text content extracted from a receipt containing
                              merchant name and line items
        :returns: The categorized expense type from predefined categories or 'Other'
                 if categorization fails or no suitable category is found
        """
        result = self._categorize_with_details(parsed_receipt)
        return result

    def _categorize_with_details(self, parsed_receipt: str) -> Dict[str, Any]:
        """
        Internal method that returns full categorization details including confidence and reasoning.

        :param parsed_receipt: The text content extracted from a receipt
        :returns: Dictionary with category, confidence, and reasoning
        """
        if not parsed_receipt:
            logger.warning("No parsed receipt provided for categorization.")
            return {
                "category": "Other",
                "confidence": 0.0,
                "reasoning": "No receipt data provided",
            }

        sanitized_text = parsed_receipt.strip()
        if len(sanitized_text) < 3:
            logger.warning("Parsed receipt text is too short for categorization.")
            return {
                "category": "Other",
                "confidence": 0.0,
                "reasoning": "Receipt text too short for analysis",
            }

        for attempt in range(self.max_retries):
            try:
                categories_list = ", ".join(sorted(constants.CATEGORIES))

                prompt = f"""
                You are analyzing a receipt to determine which category the expense falls into. Your task is to categorize this expense into EXACTLY ONE of these categories:
                {categories_list}.

                The input ("Expense Details"), may contain a merchant/vendor name followed by multiple line items, parsed with an ML service from the receipt.

                IMPORTANT: The merchant may appear as "Unknown Merchant" and some items may be labeled "Unknown Item". In these cases, focus more on the available information:
                1. Look for patterns across all available line items, even if some are unknown
                2. Use quantity and price information if available
                3. Pay attention to recognizable keywords and terms in any of the items
                4. Consider the overall context of what's being purchased

                Analysis approach:
                1. The type of merchant/vendor (e.g., restaurant, office supply store, airline)
                2. The overall pattern in the line items, not just individual items
                3. The primary purpose of the purchase
                4. Frequency of certain types of items in the list

                Category examples:
                - Multiple food/drink items → "Meals and Entertainment"
                - Paper, pens, printer supplies → "Office Supplies"
                - Flight tickets, hotels reservations → "Travel"

                Only return "Other" as a last resort if there's truly no discernible pattern or when the available information is insufficient.

                Expense Details: {sanitized_text}

                Respond with a JSON object in this exact format:
                {{
                    "category": "exact category name from the list above",
                    "confidence": confidence_score_between_0_and_1,
                    "reasoning": "brief explanation of why this category was chosen"
                }}

                NOTE: Do NOT use Markdown formatting or code blocks. Return ONLY the raw JSON object, not inside any code block or with any extra formatting.
                """

                logger.info(
                    f"Sending JSON categorization request to OpenAI for: '{sanitized_text[:50]}...'"
                )

                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=150,
                    store=False,
                )

                content = response.choices[0].message.content.strip()

                # Parse JSON response with fallback handling
                try:
                    result = json.loads(content)

                    # Validate JSON structure
                    if not isinstance(result, dict) or "category" not in result:
                        raise ValueError("Invalid JSON structure")

                    category = result.get("category", "Other")
                    confidence = float(result.get("confidence", 0.0))
                    reasoning = result.get("reasoning", "No reasoning provided")

                    # Validate category against known categories
                    if category not in constants.CATEGORIES:
                        logger.warning(
                            f"Unknown category '{category}' returned. Using 'Other'."
                        )
                        category = "Other"
                        confidence = max(
                            0.0, confidence - 0.5
                        )  # Reduce confidence for fallback

                    logger.info(
                        f"Categorization successful: '{sanitized_text[:30]}...' → '{category}' "
                        f"(confidence: {confidence:.2f})"
                    )

                    return {
                        "category": category,
                        "confidence": confidence,
                        "reasoning": reasoning,
                    }

                except (json.JSONDecodeError, ValueError, TypeError) as parse_error:
                    logger.warning(
                        f"Failed to parse JSON response: {parse_error}. Content: {content}"
                    )

                    # Fallback: try to extract category from plain text
                    content_lower = content.lower()
                    for category in constants.CATEGORIES:
                        if category.lower() in content_lower:
                            logger.info(
                                f"Fallback categorization: '{category}' found in response"
                            )
                            return {
                                "category": category,
                                "confidence": 0.5,  # Lower confidence for fallback parsing
                                "reasoning": f"Extracted from response: {content[:50]}...",
                            }

                    # If no category found in fallback, continue to next attempt
                    raise parse_error

            except Exception as e:
                logger.warning(
                    f"Categorization attempt ({attempt+1}/{self.max_retries}) failed: {str(e)}. Retrying..."
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    logger.error(
                        f"Categorization failed after {self.max_retries} attempts for: '{sanitized_text[:30]}...'. Returning 'Other'."
                    )
                    return {
                        "category": "Other",
                        "confidence": 0.0,
                        "reasoning": f"Failed after {self.max_retries} attempts: {str(e)}",
                    }

        return {
            "category": "Other",
            "confidence": 0.0,
            "reasoning": "Exhausted all retry attempts",
        }
