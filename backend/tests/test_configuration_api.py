import pytest
from httpx import AsyncClient, ASGITransport
from api.app import app

@pytest.mark.asyncio
async def test_TRC_108_configuration_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch current config
        res = await client.get("/api/v1/config")
        assert res.status_code == 200
        cfg = res.json()
        assert "retention_days" in cfg
        assert "max_spans_per_trace" in cfg
        assert "default_sample_rate" in cfg

        # 2. Update config
        update_payload = {
            "retention_days": 45,
            "max_spans_per_trace": 5000,
            "default_sample_rate": 0.75,
            "ingestion_buffer_size": 20000
        }
        res_put = await client.put("/api/v1/config", json=update_payload)
        assert res_put.status_code == 200
        updated = res_put.json()
        assert updated["retention_days"] == 45
        assert updated["max_spans_per_trace"] == 5000
        assert updated["default_sample_rate"] == 0.75
        assert updated["ingestion_buffer_size"] == 20000

        # 3. Verify changes persist across GET
        res_check = await client.get("/api/v1/config")
        assert res_check.status_code == 200
        check_cfg = res_check.json()
        assert check_cfg["retention_days"] == 45
        assert check_cfg["default_sample_rate"] == 0.75

        # 4. Validation error: sample rate > 1.0 or < 0.0
        bad_res = await client.put("/api/v1/config", json={"default_sample_rate": 1.5})
        assert bad_res.status_code == 422

        # 5. Validation error: negative retention
        bad_res2 = await client.put("/api/v1/config", json={"retention_days": -5})
        assert bad_res2.status_code == 422
