import requests
from aws_lambda_powertools import Logger

from chalicelib.models import config
from chalicelib.repositories import SmartScanRepository

logger = Logger(child=True)

__all__ = ["AppSync"]


class AppSync:
    def __init__(self):
        self._endpoint = config.appsync_graphql_endpoint
        self.db = SmartScanRepository()

    def publish_smart_scan_result(
        self, user_id: str, token: str, object_key: str, result: dict
    ):
        """
        Publish a smart scan result to AppSync to trigger subscriptions.

        :param user_id: The user's ID
        :param token: The authorization token for the user
        :param object_key: The S3 object key for the scanned receipt
        :param result: The scan result object
        :returns: The response from AppSync GraphQL API
        """
        scan_id = self.db.generate_scan_id(user_id, object_key)

        mutation = """
        mutation PublishResult($userId: String!, $scanId: String!, $objectKey: String!, $result: ScanResultInput!) {
            publishSmartScanResult(
                userId: $userId,
                scanId: $scanId,
                objectKey: $objectKey,
                result: $result
            ) {
                userId
                scanId
                result {
                    merchant
                    date
                    category
                    currency
                    amount
                    createdAt
                    confidence
                }
            }
        }
        """
        variables = {
            "userId": user_id,
            "scanId": scan_id,
            "objectKey": object_key,
            "result": result,
        }

        headers = {"Content-Type": "application/json", "Authorization": token}

        try:
            response = requests.post(
                self._endpoint,
                json={"query": mutation, "variables": variables},
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                raise Exception(f"AppSync error: {data['errors']}")
        except Exception as e:
            logger.error("Failed to publish smart scan result", extra={"error": str(e)})
            raise
        else:
            return data
