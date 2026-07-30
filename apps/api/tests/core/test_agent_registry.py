from app.agents.registry import list_agents


def test_registered_agents_have_unique_complete_routing_profiles() -> None:
    for role in ("student", "teacher", "admin"):
        agents = list_agents(role)

        assert agents
        assert len({agent.id for agent in agents}) == len(agents)
        for agent in agents:
            assert agent.routing.intent.strip()
            assert len(agent.routing.examples) >= 2
            assert all(example.strip() for example in agent.routing.examples)
            assert all(exclusion.strip() for exclusion in agent.routing.exclusions)
