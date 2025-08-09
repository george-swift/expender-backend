import re
from datetime import datetime, timezone

import boto3
from aws_lambda_powertools import Logger

from chalicelib import constants
from chalicelib.middleware.exceptions import DocumentProcessingError
from chalicelib.models import config
from chalicelib.repositories import SmartScanRepository
from chalicelib.services.categorization import CategorizationService

logger = Logger(child=True)

__all__ = ["SmartScanService"]


class SmartScanService:
    """Service for managing SmartScan operations."""

    def __init__(self):
        self._client = boto3.client("textract")
        self.db = SmartScanRepository()
        self.confidence_threshold = 50.0
        self.metrics = {
            "total_processed": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "ai_categorizations": 0,
        }
        self.categorization_service = CategorizationService()

    def get_metrics(self) -> dict:
        """
        Get the current metrics for SmartScan operations.

        :returns: Dictionary containing processing metrics including total processed,
                 successful extractions, failed extractions, and AI categorizations
        """
        return self.metrics

    def analyze_expense(self, key: str) -> dict | None:
        """
        Analyze a receipt stored in S3 using AWS Textract.

        :param key: S3 object key for the receipt image to analyze
        :returns: Raw Textract response data or None if processing fails
        """
        try:
            response = self._client.analyze_expense(
                Document={
                    "S3Object": {"Bucket": config.assets_bucket_name, "Name": key}
                }
            )
            return response
        except Exception as e:
            self.metrics["failed_extractions"] += 1
            raise DocumentProcessingError(
                f"Failed to analyze expense document: {str(e)}"
            )

    def detect_currency(self, summary_fields: list[dict]) -> str:
        """
        Detect the currency from the summary fields of the expense document.

        :param summary_fields: List of summary field dictionaries from Textract response
        :returns: ISO 4217 currency code if found, otherwise 'USD'
        """
        # First check for direct Currency field
        for field in summary_fields:
            if field.get("Currency", {}).get("Code"):
                if (
                    field.get("Currency", {}).get("Confidence", 0)
                    >= self.confidence_threshold
                ):
                    return field.get("Currency", {}).get("Code")

        # If no direct Currency field is found, then check for currency symbol in values
        for field in summary_fields:
            if field.get("Type", {}).get("Text") == "TOTAL":
                if (
                    field.get("ValueDetection", {}).get("Confidence", 0)
                    >= self.confidence_threshold
                ):
                    total_text = field.get("ValueDetection", {}).get("Text", "")
                    for code, patterns in constants.CURRENCY_PATTERNS.items():
                        if any(pattern in total_text for pattern in patterns):
                            return code
        return "USD"

    def format_text(self, text: str) -> str:
        """
        Remove newlines, carriage returns, and extra spaces from text.

        :param text: The input text to clean
        :returns: The cleaned text with single spaces
        """
        if not text:
            return ""
        normalized = re.sub(r"[\n\r]+", " ", text)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def auto_categorize(
        self, merchant: str | None, line_item_descriptions: list[str]
    ) -> dict:
        """
        Auto-categorize the expense based on merchant and line items.

        :param merchant: The merchant name extracted from the receipt
        :param line_item_descriptions: List of line item descriptions from the receipt
        :returns: Dictionary with `category` and `confidence` keys, or fallback values if categorization fails
        """
        merchant = merchant.lower() if merchant else ""

        combined_text = self.format_text(" ".join([merchant] + line_item_descriptions))
        categorization_result = self.categorization_service._categorize_with_details(
            combined_text
        )

        if categorization_result and categorization_result.get("category"):
            self.metrics["ai_categorizations"] += 1
            return {
                "category": categorization_result["category"],
                "confidence": categorization_result.get("confidence", 0.0),
            }

        # Fallback to "Other" if no category matched
        return {"category": "Other", "confidence": 0.0}

    def format_date(self, date_str: str | None) -> str | None:
        """
        Format date string to ISO 8601 format if possible.

        :param date_str: The date string to format from the receipt
        :returns: ISO 8601 formatted date string or original string if parsing fails
        """
        if not date_str:
            return None

        # Handle date-only ISO format
        try:
            # Simple YYYY-MM-DD format
            if len(date_str) >= 10 and date_str[4] == "-" and date_str[7] == "-":
                parsed_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass

        # If we're here, the input wasn't in ISO format, so we're identifying the most common formats from receipts
        common_date_formats = [
            "%Y-%m-%d",  # ISO format (YYYY-MM-DD)
            "%m/%d/%Y",  # US format (MM/DD/YYYY)
            "%d/%m/%Y",  # European format (DD/MM/YYYY)
        ]

        # Try to parse the date with each format
        for format in common_date_formats:
            try:
                parsed_date = datetime.strptime(date_str, format)
                return parsed_date.strftime("%Y-%m-%d")  # Always return ISO format
            except ValueError:
                continue

        # If it can't be parsed, return as is
        return date_str

    def format_amount(self, amount: float | int | str | None) -> float:
        """
        Format the amount to a float, handling various input types.

        :param amount: The amount value to format from the receipt
        :returns: Formatted float amount or 0.0 if conversion fails
        """
        if amount is None:
            return 0.0

        delocalized_amount = str(amount).replace(",", "").replace(" ", "")
        normalized_amount = re.sub(r"[^\d.]", "", delocalized_amount)

        try:
            return float(normalized_amount)
        except (ValueError, TypeError):
            # Try alternative approach for European format (commas are used as separators)
            try:
                european = normalized_amount.replace(".", "").replace(",", ".")
                normalized_european = re.sub(r"[^\d.]", "", european)
                return float(normalized_european)
            except:
                logger.warning(f"Could not parse amount: {amount}")
                return 0.0

    def structure_response(self, textract_response: dict | None) -> dict | None:
        """
        Structure the Textract response into a more usable format.

        :param textract_response: Raw response from AWS Textract analyze_expense
        :returns: Structured expense data dictionary with extracted fields or None if processing fails
        """
        self.metrics["total_processed"] += 1

        if not textract_response:
            self.metrics["failed_extractions"] += 1
            raise DocumentProcessingError(
                "No Textract response provided for structuring"
            )

        docs = textract_response.get("ExpenseDocuments", [])
        if not docs:
            self.metrics["failed_extractions"] += 1
            raise DocumentProcessingError(
                "No ExpenseDocuments found in Textract response"
            )

        doc = docs[0]
        summary_fields = doc.get("SummaryFields", [])
        line_item_groups = doc.get("LineItemGroups", [])

        currency = self.detect_currency(summary_fields)

        result = {
            "merchant": "Unknown Merchant",
            "date": datetime.now(timezone.utc).isoformat(),
            "category": "Other",
            "currency": currency,
            "amount": 0.0,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "confidence": 0.0,
        }

        confidences = {"merchant": 0, "date": 0, "amount": 0, "category": 0}

        MERCHANT_TYPES = {"VENDOR_NAME", "SUPPLIER_NAME", "MERCHANT_NAME"}
        DATE_TYPES = {"INVOICE_RECEIPT_DATE", "DATE", "RECEIPT_DATE"}
        AMOUNT_TYPES = {"PRICE", "AMOUNT", "COST"}

        for field in summary_fields:
            field_type = field.get("Type", {}).get("Text", "")
            confidence = field.get("ValueDetection", {}).get("Confidence", 0)

            if confidence < self.confidence_threshold:
                continue

            value = field.get("ValueDetection", {}).get("Text", "")

            if field_type in MERCHANT_TYPES:
                result["merchant"] = self.format_text(value)
                confidences["merchant"] = confidence
            elif field_type in DATE_TYPES:
                result["date"] = self.format_date(value)
                confidences["date"] = confidence
            elif field_type == "TOTAL":
                result["amount"] = self.format_amount(value)
                confidences["amount"] = confidence

        line_items = []
        line_item_descriptions = []  # For intelligent categorization
        total_line_amount = 0.0

        for group in line_item_groups:
            for item in group.get("LineItems", []):
                fields = item.get("LineItemExpenseFields", [])
                item_data = {
                    "description": "Unknown Item",
                    "quantity": 1,
                    "amount": 0.0,
                }

                for field in fields:
                    field_type = field.get("Type", {}).get("Text", "")
                    confidence = field.get("ValueDetection", {}).get("Confidence", 0)

                    if confidence < self.confidence_threshold:
                        continue

                    value = field.get("ValueDetection", {}).get("Text", "")

                    if field_type == "ITEM":
                        item_data["description"] = self.format_text(value)
                    elif field_type == "QUANTITY":
                        try:
                            item_data["quantity"] = int(
                                float(self.format_amount(value))
                            )
                        except (ValueError, TypeError):
                            item_data["quantity"] = 1
                    elif field_type in AMOUNT_TYPES:
                        item_data["amount"] = self.format_amount(value)

                # Only include items with meaningful data
                if (
                    item_data["description"] != "Unknown Item"
                    or item_data["amount"] > 0
                ):
                    line_items.append(item_data)
                    line_item_descriptions.append(item.get("description", "").lower())
                    total_line_amount += item_data["amount"]

        # Calculate total if not in summary fields but we have line items
        if not confidences["amount"] and line_items:
            result["amount"] = total_line_amount

        # Deduce category intelligently with confidence
        categorization_result = self.auto_categorize(
            result["merchant"], line_item_descriptions
        )
        result["category"] = categorization_result["category"]
        confidences["category"] = (
            categorization_result["confidence"] * 100
        )  # Convert to 0-100 scale to match Textract

        # Calculate overall confidence of data extraction
        valid_confidences = [c for c in confidences.values() if c > 0]
        result["confidence"] = round(
            sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0,
            2,
        )

        # Determine success/failure of data extraction
        is_successful = (
            result["merchant"] != "Unknown Merchant"
            or result["amount"] > 0.0
            or line_items
        )

        if is_successful:
            self.metrics["successful_extractions"] += 1
        else:
            self.metrics["failed_extractions"] += 1

        return result

    def get_smartscans_batch(
        self, user_id: str, limit: int = 25, last_evaluated_key: dict = None
    ) -> dict:
        """
        Get smartscans for a user in batches with pagination support.

        :param user_id: The user ID to get smartscans for
        :param limit: Maximum number of items to return (default: 25)
        :param last_evaluated_key: Key to start pagination from (optional)
        :returns: Dictionary with items list, `hasMore` flag, and `lastEvaluatedKey` for pagination
        """
        smartscans = self.db.get_user_smartscans(user_id, limit, last_evaluated_key)

        return {
            "items": smartscans,
            "hasMore": len(smartscans) == limit,
            "lastEvaluatedKey": smartscans[-1] if smartscans else None,
        }

    def delete_smartscans_batch(
        self, user_id: str, limit: int = 25, last_evaluated_key: dict = None
    ) -> dict:
        """
        Delete smartscans in batches for scalability during user deletion.

        :param user_id: The user ID to delete smartscans for
        :param limit: Maximum number of items to delete per batch (default: 25)
        :param last_evaluated_key: Key to start pagination from (optional)
        :returns: Dictionary with `deletedCount`, `hasMore` flag, and lastEvaluatedKey for continued processing
        """
        batch_result = self.get_smartscans_batch(user_id, limit, last_evaluated_key)
        smartscans = batch_result["items"]

        if not smartscans:
            return {"deletedCount": 0, "hasMore": False, "lastEvaluatedKey": None}

        deleted_count = 0

        # Use batch writer for efficient deletion
        with self.db.table.batch_writer() as batch:
            for smartscan in smartscans:
                try:
                    batch.delete_item(
                        Key={
                            "userId": smartscan["userId"],
                            "scanId": smartscan["scanId"],
                        }
                    )
                    deleted_count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to delete smartscan {smartscan.get('scanId')}: {str(e)}"
                    )

        return {
            "deletedCount": deleted_count,
            "hasMore": batch_result["hasMore"],
            "lastEvaluatedKey": batch_result["lastEvaluatedKey"],
        }
