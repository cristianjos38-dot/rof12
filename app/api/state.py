from threading import RLock
from uuid import uuid4


class ApiState:
    def __init__(self):
        self.lock = RLock()
        self.tasks = {}
        self.artifacts = {}
        self.holds = {}
        self.audit = {}

    def task(self, tenant_id, task_id):
        return self.tasks.get((tenant_id, task_id))

    def new_id(self):
        return str(uuid4())


api_state = ApiState()
