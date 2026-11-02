from fastapi import APIRouter, Depends

from app.api.dependencies import AuthContext, get_auth_context

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/context")
def task_context(context: AuthContext = Depends(get_auth_context)) -> dict:
    return {
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "role": context.role,
        "membership_status": context.membership_status,
    }

