from chalice import Blueprint, Response

from chalicelib.authorizers import api_gateway_authorizer
from chalicelib.services import ExpenseService

expense_router = Blueprint(__name__)
expense_service = ExpenseService()

__all__ = ["expense_router"]


def get_authorized_user(current_request):
    return current_request.context["authorizer"]["principalId"]


@expense_router.route("/expenses", methods=["GET"], authorizer=api_gateway_authorizer)
def list_expenses():
    user_id = get_authorized_user(expense_router.current_request)
    expenses = expense_service.get_expenses(user_id)
    return Response(
        body=expenses,
        headers={"X-Total-Count": str(len(expenses))},
        status_code=200,
    )


@expense_router.route("/expenses", methods=["POST"], authorizer=api_gateway_authorizer)
def create_expense():
    user_id = get_authorized_user(expense_router.current_request)
    payload = expense_router.current_request.json_body
    expense_id = expense_service.create_single_expense(user_id, payload)
    return Response(body={"expenseId": expense_id}, status_code=201)


@expense_router.route(
    "/expenses/batch", methods=["POST"], authorizer=api_gateway_authorizer
)
def create_expenses():
    user_id = get_authorized_user(expense_router.current_request)
    payload = expense_router.current_request.json_body
    expense_ids = expense_service.create_multiple_expenses(user_id, payload)
    return Response(body={"expenseIds": expense_ids}, status_code=201)


@expense_router.route(
    "/expenses/{expense_id}", methods=["PUT"], authorizer=api_gateway_authorizer
)
def update_expense(expense_id):
    user_id = get_authorized_user(expense_router.current_request)
    payload = expense_router.current_request.json_body
    updated_expense = expense_service.update_expense(user_id, expense_id, payload)
    return Response(body=updated_expense, status_code=200)


@expense_router.route(
    "/expenses/{expense_id}", methods=["DELETE"], authorizer=api_gateway_authorizer
)
def delete_expense(expense_id):
    user_id = get_authorized_user(expense_router.current_request)
    deleted_expense_id = expense_service.delete_single_expense(user_id, expense_id)
    return Response(body={"expenseId": deleted_expense_id}, status_code=204)


@expense_router.route(
    "/expenses/batch", methods=["DELETE"], authorizer=api_gateway_authorizer
)
def delete_expenses():
    user_id = get_authorized_user(expense_router.current_request)
    payload = expense_router.current_request.json_body
    deleted_expense_ids = expense_service.delete_multiple_expenses(user_id, payload)
    return Response(body={"expenseIds": deleted_expense_ids}, status_code=204)


@expense_router.route(
    "/expenses/export", methods=["POST"], authorizer=api_gateway_authorizer
)
def export_expenses():
    user_id = get_authorized_user(expense_router.current_request)
    payload = expense_router.current_request.json_body
    format = payload.get("format", "csv").lower()
    attributes = payload.get("attributes", [])
    csv = expense_service.export_expenses(user_id, attributes=attributes, format=format)
    return Response(
        body=csv,
        status_code=200,
        headers={
            "Content-Type": "text/csv",
            "Content-Disposition": 'attachment; filename="expenses.csv"',
        },
    )
