"""Tests for batch_process CLI defaults."""

from __future__ import annotations

import sys

import batch_process


def test_parse_args_defaults_to_ml(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["batch_process.py"])

    args = batch_process._parse_args()

    assert args.use_ml is True


def test_parse_args_no_ml_disables_ml(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["batch_process.py", "--no-ml"])

    args = batch_process._parse_args()

    assert args.use_ml is False
