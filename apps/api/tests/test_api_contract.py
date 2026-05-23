from fastapi.testclient import TestClient


def test_api_only_backend_not_serving_spa(client: TestClient) -> None:
    # API 服务只提供 API/健康检查，不承接前端 SPA 回退路由
    response = client.get("/workbench")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
