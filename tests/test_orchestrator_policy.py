from silentir.orchestrator import provider_order


def test_provider_order_local_first() -> None:
    assert provider_order("local_first") == ["local", "online"]


def test_provider_order_online_only() -> None:
    assert provider_order("online_only") == ["online"]
