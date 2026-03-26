from __future__ import annotations

from seed_data import should_seed_demo_data


def test_demo_seed_defaults_on_in_development():
    assert should_seed_demo_data(app_env="development", explicit_flag=None) is True


def test_demo_seed_can_be_disabled_in_development():
    assert should_seed_demo_data(app_env="development", explicit_flag="false") is False


def test_demo_seed_defaults_off_in_production():
    assert should_seed_demo_data(app_env="production", explicit_flag=None) is False
    assert should_seed_demo_data(app_env="staging", explicit_flag=None) is False


def test_demo_seed_requires_explicit_opt_in_in_production():
    assert should_seed_demo_data(app_env="production", explicit_flag="true") is True
