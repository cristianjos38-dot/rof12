from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies import AuthContext, get_auth_context
from app.api.state import api_state

router = APIRouter(prefix="/tasks", tags=["tasks"])

v1_router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_type: str = Field(min_length=1, max_length=100)
    payload: dict


class ArtifactLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    artifact_id: str = Field(min_length=1)


@v1_router.post("")
def create_task(payload: TaskRequest, context: AuthContext = Depends(get_auth_context)):
    task_id = str(uuid4())
    with api_state.lock:
        api_state.tasks[(context.tenant_id, task_id)] = {"task_id": task_id, "tenant_id": context.tenant_id, "status": "CREATED", "task_type": payload.task_type, "payload": payload.payload, "artifacts": []}
    return api_state.tasks[(context.tenant_id, task_id)]


@v1_router.get("/{task_id}")
def get_task(task_id: str, context: AuthContext = Depends(get_auth_context)):
    task = api_state.task(context.tenant_id, task_id)
    if task is None:
        raise HTTPException(404, detail="task not found")
    return task


@v1_router.post("/{task_id}/artifacts")
def link_artifact(task_id: str, payload: ArtifactLink, context: AuthContext = Depends(get_auth_context)):
    task = api_state.task(context.tenant_id, task_id)
    if task is None or (context.tenant_id, payload.artifact_id) not in api_state.artifacts:
        raise HTTPException(404, detail="task or artifact not found")
    task["artifacts"].append(payload.artifact_id)
    return task


@v1_router.get("/{task_id}/audit")
def task_audit(task_id: str, context: AuthContext = Depends(get_auth_context)):
    if api_state.task(context.tenant_id, task_id) is None:
        raise HTTPException(404, detail="task not found")
    return {"task_id": task_id, "events": api_state.audit.get((context.tenant_id, task_id), [])}


@router.get("/context")
def task_context(context: AuthContext = Depends(get_auth_context)) -> dict:
    return {
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "role": context.role,
        "membership_status": context.membership_status,
    }
