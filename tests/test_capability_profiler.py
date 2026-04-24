from ai_pc_kit.capabilities import collect_capabilities


def test_capability_profile_schema_has_expected_top_level_keys() -> None:
    profile = collect_capabilities().to_dict()

    assert set(profile) == {"system", "cpu", "gpus", "npus", "memory", "warnings"}
    assert "python_version" in profile["system"]
    assert "total_gb" in profile["memory"]
