import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

logger = Logger(child=True)

__all__ = ["StateMachine"]


class StateMachine:
    """Encapsulates Step Functions state machine actions."""

    def __init__(self):
        self._client = boto3.client("stepfunctions")

    def create(self, name, definition, role_arn):
        """
        Create a state machine with the specified definition.

        :param name: The name to give the state machine
        :param definition: The Amazon States Language definition of the steps
        :param role_arn: The ARN of the role assumed by Step Functions
        :returns: The ARN of the newly created state machine
        """
        try:
            response = self._client.create_state_machine(
                name=name, definition=definition, roleArn=role_arn
            )
        except ClientError as err:
            logger.error(
                "Couldn't create state machine %s. Here's why: %s: %s",
                name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return response["stateMachineArn"]

    def find(self, name):
        """
        Find a state machine by name using pagination.

        :param name: The name of the state machine to search for
        :returns: The ARN of the state machine if found, otherwise None
        """
        try:
            paginator = self._client.get_paginator("list_state_machines")
            for page in paginator.paginate():
                for state_machine in page.get("stateMachines", []):
                    if state_machine["name"] == name:
                        return state_machine["stateMachineArn"]
        except ClientError as err:
            logger.error(
                "Couldn't list state machines. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise

    def describe(self, state_machine_arn):
        """
        Get detailed information about a state machine.

        :param state_machine_arn: The ARN of the state machine to describe
        :returns: Dictionary containing state machine metadata
        """
        try:
            response = self._client.describe_state_machine(
                stateMachineArn=state_machine_arn
            )
        except ClientError as err:
            logger.error(
                "Couldn't describe state machine %s. Here's why: %s: %s",
                state_machine_arn,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return response

    def start(self, state_machine_arn, run_input):
        """
        Start an execution of a state machine with specified input.

        :param state_machine_arn: The ARN of the state machine to execute
        :param run_input: The input to the state machine in JSON format
        :returns: The ARN of the execution for tracking status and output
        """
        try:
            response = self._client.start_execution(
                stateMachineArn=state_machine_arn, input=run_input
            )
        except ClientError as err:
            logger.error(
                "Couldn't start state machine %s. Here's why: %s: %s",
                state_machine_arn,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return response["executionArn"]

    def describe_run(self, run_arn):
        """
        Get detailed information about a state machine execution.

        :param run_arn: The ARN of the execution to describe
        :returns: Dictionary containing execution status, output, and metadata
        """
        try:
            response = self._client.describe_execution(executionArn=run_arn)
        except ClientError as err:
            logger.error(
                "Couldn't describe run %s. Here's why: %s: %s",
                run_arn,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return response

    def delete(self, state_machine_arn):
        """
        Delete a state machine and all associated execution history.

        :param state_machine_arn: The ARN of the state machine to delete
        :returns: Response dictionary from the delete operation
        """
        try:
            response = self._client.delete_state_machine(
                stateMachineArn=state_machine_arn
            )
        except ClientError as err:
            logger.error(
                "Couldn't delete state machine %s. Here's why: %s: %s",
                state_machine_arn,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise
        else:
            return response
