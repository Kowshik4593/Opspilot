from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def run():
    print('Creating task')
    payload = {"task_id": "t_test", "title": "T", "description": "d", "status": "pending"}
    r = client.post("/api/v1/tasks", json=payload, headers={"x-api-key": "dev-unprotected"})
    print('POST', r.status_code, r.text)
    print('Updating task')
    up = {"task_id": "t_test", "title": "T", "description": "d", "status": "done"}
    r = client.put("/api/v1/tasks/t_test", json=up, headers={"x-api-key": "dev-unprotected"})
    print('PUT', r.status_code, r.text)
    print('Deleting task')
    r = client.delete("/api/v1/tasks/t_test", headers={"x-api-key": "dev-unprotected"})
    print('DELETE', r.status_code, r.text)

if __name__ == '__main__':
    run()
