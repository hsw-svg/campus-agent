from app.integrations.deeptutor.catalog_sync import SharedModelConfig, build_synced_catalog


def test_build_synced_catalog_selects_managed_profiles_and_preserves_other_settings() -> None:
    catalog = {
        "version": 1,
        "services": {
            "llm": {
                "active_profile_id": "old",
                "active_model_id": "old-model",
                "profiles": [{"id": "old", "models": []}],
            },
            "search": {"active_profile_id": None, "profiles": []},
        },
    }
    llm = SharedModelConfig("openai", "deepseek-chat", "secret", "https://api.deepseek.com")
    embedding = SharedModelConfig(
        "openai",
        "text-embedding-3-small",
        "secret",
        "https://api.example.com/v1/embeddings",
        dimension=1536,
    )

    synced = build_synced_catalog(catalog, llm, embedding)

    assert synced["services"]["search"] == catalog["services"]["search"]
    assert synced["services"]["llm"]["active_profile_id"] == "campus-agent-shared-profile"
    assert synced["services"]["llm"]["profiles"][-1]["base_url"] == "https://api.deepseek.com"
    assert synced["services"]["llm"]["profiles"][-1]["api_key"] == "secret"
    assert synced["services"]["embedding"]["profiles"][-1]["models"][0]["dimension"] == 1536
    assert catalog["services"]["llm"]["active_profile_id"] == "old"
