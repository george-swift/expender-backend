from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key

from chalicelib import constants
from chalicelib.models import config

__all__ = ["ExpenseRepository"]


class ExpenseRepository:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(config.expenses_table_name)
        self.max_batch_size = constants.MAX_BATCH_SIZE

    def create_expense(self, user_id: str, payload: dict) -> str:
        """
        Create a new expense record in DynamoDB.

        :param user_id: The user ID creating the expense
        :param payload: Dictionary containing expense data
        :returns: The generated expense ID
        """
        expense_id = f"exp_{uuid4()}"
        timestamp = datetime.now(timezone.utc).isoformat()

        expense = {
            "userId": user_id,
            "expenseId": expense_id,
            "date": payload["date"],
            "amount": Decimal(str(payload["amount"])),
            "currency": payload["currency"],
            "category": payload["category"],
            "merchant": payload.get("merchant"),
            "description": payload.get("description"),
            "scanId": payload.get("scanId"),
            "receipt": payload.get("receipt"),
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        self.table.put_item(Item=expense)
        return expense_id

    def batch_create_expenses(self, user_id: str, payload: list[dict]) -> list[str]:
        """
        Create multiple expense records in a single batch operation.

        :param user_id: The user ID creating the expenses
        :param payload: List of dictionaries containing expense data
        :returns: List of generated expense IDs
        """
        if len(payload) > self.max_batch_size:
            raise ValueError(
                f"Cannot create more than {self.max_batch_size} expenses at once."
            )

        timestamp = datetime.now(timezone.utc).isoformat()
        expense_ids = set()

        with self.table.batch_writer() as batch:
            for expense in payload:
                expense_id = f"exp_{uuid4()}"
                batch.put_item(
                    Item={
                        "userId": user_id,
                        "expenseId": expense_id,
                        "date": expense["date"],
                        "amount": Decimal(str(expense["amount"])),
                        "currency": expense["currency"],
                        "category": expense["category"],
                        "merchant": expense.get("merchant"),
                        "description": expense.get("description"),
                        "createdAt": timestamp,
                        "updatedAt": timestamp,
                    }
                )
                expense_ids.add(expense_id)
        return list(expense_ids)

    def get_expense(self, user_id: str, expense_id: str) -> dict | None:
        """
        Get a single expense by user ID and expense ID.

        :param user_id: The user ID who owns the expense
        :param expense_id: The expense ID to retrieve
        :returns: Expense dictionary or None if not found
        """
        response = self.table.get_item(
            Key={"userId": user_id, "expenseId": expense_id},
            ProjectionExpression="expenseId, #date, amount, currency, category, merchant, description, scanId, receipt",
            ExpressionAttributeNames={"#date": "date"},
        )
        return response.get("Item")

    def get_expenses(self, user_id: str) -> list[dict]:
        """
        Get all expenses for a user.

        :param user_id: The user ID to get expenses for
        :returns: List of expense dictionaries
        """
        response = self.table.query(KeyConditionExpression=Key("userId").eq(user_id))
        return response.get("Items", [])

    def get_expenses_sorted_by_date(self, user_id: str) -> list[dict]:
        """
        Get all expenses for a user sorted by date using the DateIndex GSI.

        :param user_id: The user ID to get expenses for
        :returns: List of expense dictionaries sorted by date (newest first)
        """
        response = self.table.query(
            IndexName="DateIndex",
            KeyConditionExpression=Key("userId").eq(user_id),
            ScanIndexForward=False,
            ProjectionExpression="expenseId, #date, amount, currency, category, merchant, description, scanId, receipt",
            ExpressionAttributeNames={"#date": "date"},
        )
        return response.get("Items", [])

    def get_user_expenses(
        self, user_id: str, limit: int = 25, last_evaluated_key: dict = None
    ) -> list:
        """
        Get expenses for a user with pagination support.

        :param user_id: The user ID to get expenses for
        :param limit: Maximum number of items to return
        :param last_evaluated_key: Key to start pagination from
        :return: List of expense items
        """
        query_kwargs = {
            "KeyConditionExpression": Key("userId").eq(user_id),
            "Limit": limit,
        }

        if last_evaluated_key:
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = self.table.query(**query_kwargs)
        return response.get("Items", [])

    def update_expense(
        self,
        user_id: str,
        expense_id: str,
        update_expression: str = None,
        expression_attribute_values: dict = None,
        payload: dict = None,
    ) -> dict:
        """
        Update an expense with either a custom update expression or payload dict.
        """
        if update_expression and expression_attribute_values:
            # Use custom update expression (for Step Functions on user account deletion)
            response = self.table.update_item(
                Key={"userId": user_id, "expenseId": expense_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression="attribute_exists(expenseId)",
                ReturnValues="ALL_NEW",
            )
        elif payload:
            # Create update expression from payload for regular client updates
            if "amount" in payload:
                payload["amount"] = Decimal(str(payload["amount"]))

            payload["updatedAt"] = datetime.now(timezone.utc).isoformat()

            update_expression = "SET " + ", ".join(
                f"#{k} = :{k}" for k in payload.keys()
            )
            expression_attribute_names = {f"#{k}": k for k in payload.keys()}
            expression_attribute_values = {f":{k}": v for k, v in payload.items()}

            response = self.table.update_item(
                Key={"userId": user_id, "expenseId": expense_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ConditionExpression="attribute_exists(expenseId)",
                ReturnValues="ALL_NEW",
            )
        else:
            raise ValueError(
                "Either update_expression with expression_attribute_values or payload must be provided"
            )

        return response.get("Attributes", {})

    def delete_expense(self, user_id: str, expense_id: str) -> dict:
        """
        Delete a single expense record.

        :param user_id: The user ID who owns the expense
        :param expense_id: The expense ID to delete
        :returns: The deleted expense data
        """
        response = self.table.delete_item(
            Key={"userId": user_id, "expenseId": expense_id},
            ConditionExpression="attribute_exists(expenseId)",
            ReturnValues="ALL_OLD",
        )
        return response.get("Attributes", {})

    def delete_expenses_by_user(self, user_id: str) -> dict:
        """
        Delete all expenses for a user using paginated batch operations.

        :param user_id: The user ID to delete all expenses for
        :returns: Dictionary with success status and count of deleted expenses
        """
        deleted_count = 0
        response = self.table.query(KeyConditionExpression=Key("userId").eq(user_id))
        items = response.get("Items", [])
        if items:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={"userId": user_id, "expenseId": item["expenseId"]}
                    )
            deleted_count += len(items)
            last_evaluated_key = response.get("LastEvaluatedKey")
            while last_evaluated_key:
                response = self.table.query(
                    KeyConditionExpression=Key("userId").eq(user_id),
                    ExclusiveStartKey=last_evaluated_key,
                )
                items = response.get("Items", [])
                with self.table.batch_writer() as batch:
                    for item in items:
                        batch.delete_item(
                            Key={"userId": user_id, "expenseId": item["expenseId"]}
                        )
                deleted_count += len(items)
                last_evaluated_key = response.get("LastEvaluatedKey")
        return {"success": True, "deletedCount": deleted_count}

    def batch_delete_expenses(self, user_id: str, expense_ids: list[str]) -> list[str]:
        """
        Delete multiple expenses in a batch operation.

        :param user_id: The user ID who owns the expenses
        :param expense_ids: List of expense IDs to delete
        :returns: List of deleted expense IDs
        """
        if len(expense_ids) > self.max_batch_size:
            raise ValueError(
                f"Cannot delete more than {self.max_batch_size} expenses at once."
            )

        with self.table.batch_writer() as batch:
            for expense_id in expense_ids:
                batch.delete_item(Key={"userId": user_id, "expenseId": expense_id})
        return expense_ids
