"""Tests for test runner."""

from unittest.mock import MagicMock, patch

import pytest

from src.opa_test_framework.config import PolicyTest, TestConfig
from src.opa_test_framework.runner import TestRunner


class TestTestRunner:
    """Tests for TestRunner."""

    def _make_config(self, **kwargs):
        defaults = {
            "opa_url": "http://localhost:8181",
            "timeout_seconds": 10,
        }
        defaults.update(kwargs)
        return TestConfig(**defaults)

    def test_get_all_categories_without_policies(self):
        config = self._make_config()
        runner = TestRunner(config)
        categories = runner._get_all_categories()
        # Should have health and bundle categories
        assert len(categories) == 2
        names = [c.name for c in categories]
        assert "health" in names
        assert "bundle" in names

    def test_get_all_categories_with_policies(self):
        config = self._make_config(
            test_policies=[
                PolicyTest(
                    name="test1",
                    policy_path="example/allow",
                    input={"role": "admin"},
                    expected_output={"allow": True},
                )
            ]
        )
        runner = TestRunner(config)
        categories = runner._get_all_categories()
        assert len(categories) == 3
        names = [c.name for c in categories]
        assert "policy" in names

    def test_get_smoke_categories(self):
        config = self._make_config()
        runner = TestRunner(config)
        smoke = runner._get_smoke_categories()
        # Health and bundle are both smoke tests
        assert len(smoke) >= 1
        for cat in smoke:
            assert cat.is_smoke_test()

    def test_categories_sorted_by_priority(self):
        config = self._make_config(
            test_policies=[
                PolicyTest(
                    name="test1",
                    policy_path="example/allow",
                    input={"role": "admin"},
                    expected_output={"allow": True},
                )
            ]
        )
        runner = TestRunner(config)
        categories = runner._get_all_categories()
        priorities = [c.get_priority() for c in categories]
        assert priorities == sorted(priorities)

    def test_run_category_invalid_name(self):
        config = self._make_config()
        runner = TestRunner(config)
        with pytest.raises(ValueError, match="not found"):
            # Need to mock OPAClient since run_category creates one
            with patch("src.opa_test_framework.runner.OPAClient"):
                runner.run_category("nonexistent")

    def test_run_smoke_tests_returns_summary(self):
        config = self._make_config()
        runner = TestRunner(config)

        with patch("src.opa_test_framework.runner.OPAClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            # Mock the category execute_all to return results
            with patch.object(
                runner,
                "_get_smoke_categories",
                return_value=[],
            ):
                summary = runner.run_smoke_tests()
                assert summary.total_tests == 0
                assert summary.success is True

    def test_run_full_tests_returns_summary(self):
        config = self._make_config()
        runner = TestRunner(config)

        with patch("src.opa_test_framework.runner.OPAClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value.__enter__ = MagicMock(return_value=mock_client)
            MockClient.return_value.__exit__ = MagicMock(return_value=False)

            with patch.object(
                runner,
                "_get_all_categories",
                return_value=[],
            ):
                summary = runner.run_full_tests()
                assert summary.total_tests == 0
