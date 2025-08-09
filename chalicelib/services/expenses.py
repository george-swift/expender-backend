import csv
import io
import time
from datetime import datetime
from decimal import Decimal

from aws_lambda_powertools import Logger

from chalicelib.models import Expense
from chalicelib.repositories import ExpenseRepository

logger = Logger(child=True)

__all__ = ["ExpenseService"]


class ExpenseService:
    """Service for managing business logic for expenses."""

    def __init__(self):
        self.db = ExpenseRepository()

    def get_expenses(self, user_id):
        """
        Get all expenses for a user sorted by date.

        :param user_id: The user ID to get expenses for
        :returns: List of expense dictionaries sorted by date (newest first)
        """
        expenses = self.db.get_expenses_sorted_by_date(user_id)
        return expenses

    def create_single_expense(self, user_id, payload):
        """
        Create a single expense after validation.

        :param user_id: The user ID creating the expense
        :param payload: Dictionary containing expense data
        :returns: The created expense ID
        """
        if "date" in payload:
            payload["date"] = self._normalize_date(payload["date"])

        expense = Expense(**payload).model_dump(exclude_none=True)
        expense_id = self.db.create_expense(user_id, expense)
        return expense_id

    def create_multiple_expenses(self, user_id, payload):
        """
        Create multiple expenses in a batch operation after validation.

        :param user_id: The user ID creating the expenses
        :param payload: List of dictionaries containing expense data
        :returns: List of created expense IDs
        """
        expenses = [Expense(**item).model_dump(exclude_none=True) for item in payload]
        expense_ids = self.db.batch_create_expenses(user_id, expenses)
        return expense_ids

    def update_expense(self, user_id, expense_id, payload):
        """
        Update an existing expense after validation and field sanitization.

        :param user_id: The user ID who owns the expense
        :param expense_id: The expense ID to update
        :param payload: Dictionary containing updated expense data
        :returns: The updated expense dictionary
        """
        if "date" in payload:
            payload["date"] = self._normalize_date(payload["date"])

        expense = Expense(**payload).model_dump(exclude_none=True)

        forbidden_fields = {"userId", "expenseId", "createdAt"}
        for field in forbidden_fields:
            expense.pop(field, None)

        if not expense:
            raise ValueError("No mutable fields provided to update")

        updated_expense = self.db.update_expense(user_id, expense_id, payload=expense)
        return updated_expense

    def delete_single_expense(self, user_id, expense_id):
        """
        Delete a single expense.

        :param user_id: The user ID who owns the expense
        :param expense_id: The expense ID to delete
        :returns: The deleted expense ID
        """
        deleted_expense = self.db.delete_expense(user_id, expense_id)
        return deleted_expense.get("expenseId")

    def delete_multiple_expenses(self, user_id, expense_ids):
        """
        Delete multiple expenses in a batch operation.

        :param user_id: The user ID who owns the expenses
        :param expense_ids: List of expense IDs to delete
        :returns: List of deleted expense IDs
        """
        if not isinstance(expense_ids, list) or not expense_ids:
            raise ValueError("A list of expense IDs must be provided for deletion")

        deleted_expenses_ids = self.db.batch_delete_expenses(user_id, expense_ids)
        return deleted_expenses_ids

    def delete_all_expenses(self, user_id):
        """
        Delete all expenses for a user.

        :param user_id: The user ID to delete all expenses for
        :returns: Dictionary with success status and count of deleted expenses
        """
        return self.db.delete_expenses_by_user(user_id)

    def get_expenses_batch(
        self, user_id: str, limit: int = 25, last_evaluated_key: dict = None
    ) -> dict:
        """
        Get expenses for a user in batches with pagination support.
        Returns structured response with items and pagination info.
        """
        expenses = self.db.get_user_expenses(user_id, limit, last_evaluated_key)

        return {
            "items": expenses,
            "hasMore": len(expenses) == limit,
            "lastEvaluatedKey": expenses[-1] if expenses else None,
        }

    def mark_expenses_for_ttl_deletion(
        self, user_id: str, limit: int = 25, last_evaluated_key: dict = None
    ) -> dict:
        """
        Mark expenses for TTL deletion by setting expireAt to now and removing scanId.
        This prevents DynamoDB stream conflicts during user deletion.
        """
        batch_result = self.get_expenses_batch(user_id, limit, last_evaluated_key)
        expenses = batch_result["items"]

        if not expenses:
            return {"markedCount": 0, "hasMore": False, "lastEvaluatedKey": None}

        marked_count = 0
        current_time = int(time.time())

        for expense in expenses:
            try:
                update_expression = "SET expireAt = :ttl"
                expression_values = {":ttl": current_time}

                if "scanId" in expense:
                    update_expression += " REMOVE scanId"

                self.db.update_expense(
                    user_id=expense["userId"],
                    expense_id=expense["expenseId"],
                    update_expression=update_expression,
                    expression_attribute_values=expression_values,
                )
                marked_count += 1

            except Exception as e:
                logger.warning(
                    f"Failed to mark expense {expense.get('expenseId')} for deletion: {str(e)}"
                )

        return {
            "markedCount": marked_count,
            "hasMore": batch_result["hasMore"],
            "lastEvaluatedKey": batch_result["lastEvaluatedKey"],
        }

    def export_expenses(self, user_id, attributes=None, format="csv"):
        """
        Export user expenses to CSV format.

        :param user_id: The user ID to export expenses for
        :param attributes: List of attributes to include in export (optional)
        :param format: Export format, currently only 'csv' is supported (default: 'csv')
        :returns: CSV string containing exported expense data
        """
        if format.lower() != "csv":
            raise ValueError(
                "Unsupported format. Only 'csv' is supported at this time."
            )

        expenses = self.db.get_expenses(user_id)

        if not expenses:
            raise ValueError("No expenses found for user.")

        csv = self._create_csv(expenses, attributes)
        return csv

    def _create_csv(self, expenses, attributes=None):
        """
        Create CSV content from expenses data.

        :param expenses: List of expense dictionaries
        :param attributes: List of attributes to include (optional)
        :returns: CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        all_columns = {
            "date": "Date",
            "merchant": "Merchant",
            "amount": "Amount",
            "currency": "Currency",
            "category": "Category",
            "description": "Description",
        }

        # Determine which columns to include
        if attributes:
            requested_columns = [col for col in attributes if col in all_columns]
        else:
            requested_columns = list(all_columns.keys())

        # Apply column ordering rules
        ordered_columns = self._order_columns(requested_columns)

        # Write header row
        writer.writerow([all_columns[col] for col in ordered_columns])

        # Write data rows
        for expense in expenses:
            row = []
            for col in ordered_columns:
                value = self._format_cell_value(expense, col)
                row.append(value)
            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()
        return csv_content

    def _format_cell_value(self, expense, column):
        """
        Format a cell value based on the column type and expense data.

        :param expense: The expense dictionary
        :param column: The column name being formatted
        :returns: Formatted value for the cell
        """
        value = expense.get(column, "")

        if column == "date" and value:
            return self._format_date(value)
        elif column == "amount" and isinstance(value, Decimal):
            return "{:,.2f}".format(value)
        elif isinstance(value, Decimal):
            return str(value)
        else:
            return str(value) if value is not None else ""

    def _format_date(self, date_value):
        """
        Format date value to readable format.

        :param date_value: The date value to format
        :returns: Formatted date string
        """
        try:
            parsed_date = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            return parsed_date.strftime("%B %d, %Y")
        except Exception:
            return str(date_value)

    def _normalize_date(self, date_str):
        """
        Parse common date formats expected in receipts

        :param date_str: The date value to normalize
        :returns: ISO 8601 date string (with 'Z' for UTC) or original string if parsing fails
        """
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%d %b %Y", "%d %B %Y"):
            try:
                return datetime.strptime(date_str, fmt).isoformat() + "Z"
            except Exception:
                continue

        return date_str

    def _order_columns(self, requested_columns):
        """
        Apply column ordering rules for readability.

        :param requested_columns: List of requested column names
        :returns: Ordered list of column names following business rules
        """
        ordered = ["date"]  # Date is always first

        # Get remaining columns (excluding date)
        remaining = [col for col in requested_columns if col != "date"]

        # Remove currency if amount is not requested
        if "amount" not in remaining:
            remaining = [col for col in remaining if col != "currency"]

        # Process remaining columns
        for col in remaining:
            if col == "amount":
                # Always add currency right after amount
                ordered.extend(["amount", "currency"])
            elif col == "currency":
                # Skip currency here, it's handled with amount
                continue
            else:
                ordered.append(col)

        return ordered
