"""Tests for evaluation handoff in the ML workbench."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from case_parser.ml.config import DEFAULT_ML_THRESHOLD
from ml_training import workbench


def test_evaluate_command_uses_defaults_for_optional_eval_args(tmp_path, monkeypatch):
    captured: dict[str, object] = {}
    eval_data = tmp_path / "eval.csv"

    monkeypatch.setattr(
        workbench,
        "_resolve_optional_data_path",
        lambda _data: eval_data,
    )

    def fake_run_script_stage(_name, _script_path, argv):
        """
        Act as a test double for running a script stage: capture the argv list and indicate successful execution.

        Parameters:
            _name: Ignored.
            _script_path: Ignored.
            argv: The argument list passed to the script; stored in captured["argv"].

        Returns:
            int: Exit code `0` indicating success.
        """
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(workbench, "_run_script_stage", fake_run_script_stage)

    rc = workbench._evaluate_command(
        argparse.Namespace(model="ml_models/procedure_classifier.pkl", data=None)
    )

    assert rc == 0
    assert captured["argv"] == [
        str(Path("ml_models/procedure_classifier.pkl").resolve()),
        str(eval_data),
        "--hybrid-threshold",
        str(DEFAULT_ML_THRESHOLD),
    ]


def test_run_command_chain_builds_complete_eval_args(tmp_path, monkeypatch):
    captured: dict[str, argparse.Namespace] = {}
    eval_data = tmp_path / "run-eval.csv"

    monkeypatch.setattr(workbench, "_train_command", lambda _args: 0)
    monkeypatch.setattr(
        workbench, "_resolve_eval_data_for_run", lambda _args: eval_data
    )
    monkeypatch.setattr(workbench, "_print_next_review_step", lambda *_args: None)

    def fake_evaluate_command(eval_args: argparse.Namespace) -> int:
        """
        Capture evaluation command arguments into the test's captured dictionary.

        Parameters:
            eval_args (argparse.Namespace): The evaluation command arguments to capture.

        Returns:
            int: `0` to indicate successful capture.
        """
        captured["args"] = eval_args
        return 0

    monkeypatch.setattr(workbench, "_evaluate_command", fake_evaluate_command)

    rc = workbench._run_command_chain(
        argparse.Namespace(
            model="ml_models/procedure_classifier.pkl",
            label_column="rule_category",
            eval_label_column=None,
            skip_evaluate=False,
            eval_data=None,
            prepared_data="prepared.csv",
            unseen_data="unseen.csv",
            skip_split=False,
        )
    )

    assert rc == 0
    assert captured["args"].model == "ml_models/procedure_classifier.pkl"
    assert captured["args"].data == eval_data
    assert captured["args"].label_column is None
    assert captured["args"].hybrid_threshold == DEFAULT_ML_THRESHOLD


def test_retrain_command_builds_complete_eval_args(monkeypatch):
    captured: dict[str, argparse.Namespace] = {}

    monkeypatch.setattr(
        workbench,
        "_prepare_override_retrain_datasets",
        lambda _args: workbench.RetrainMergeSummary(
            override_count=1,
            seen_overrides_applied=1,
            unseen_promoted=1,
            corrected_rows_weighted=1,
            rows_added_by_weighting=0,
            weighting_multiplier=workbench.OVERRIDE_CORRECTION_MULTIPLIER,
            retrain_rows=10,
            remaining_eval_rows=2,
        ),
    )
    monkeypatch.setattr(workbench, "_print_retrain_merge_summary", lambda *_args: None)
    monkeypatch.setattr(workbench, "_run_script_stage", lambda *_args: 0)

    def fake_evaluate_command(eval_args: argparse.Namespace) -> int:
        """
        Capture evaluation command arguments into the test's captured dictionary.

        Parameters:
            eval_args (argparse.Namespace): The evaluation command arguments to capture.

        Returns:
            int: `0` to indicate successful capture.
        """
        captured["args"] = eval_args
        return 0

    monkeypatch.setattr(workbench, "_evaluate_command", fake_evaluate_command)

    rc = workbench._retrain_command(
        argparse.Namespace(
            retrain_data_output="retrain.csv",
            model="ml_models/procedure_classifier.pkl",
            label_column="human_category",
            eval_label_column=None,
            cross_validate=False,
            skip_evaluate=False,
            eval_data_output="remaining.csv",
        )
    )

    assert rc == 0
    assert captured["args"].model == "ml_models/procedure_classifier.pkl"
    assert captured["args"].data == "remaining.csv"
    assert captured["args"].label_column is None
    assert captured["args"].hybrid_threshold == DEFAULT_ML_THRESHOLD


def test_run_command_chain_forwards_explicit_eval_label_column(
    tmp_path,
    monkeypatch,
):
    captured: dict[str, argparse.Namespace] = {}
    eval_data = tmp_path / "run-eval.csv"

    monkeypatch.setattr(workbench, "_train_command", lambda _args: 0)
    monkeypatch.setattr(
        workbench, "_resolve_eval_data_for_run", lambda _args: eval_data
    )
    monkeypatch.setattr(workbench, "_print_next_review_step", lambda *_args: None)

    def fake_evaluate_command(eval_args: argparse.Namespace) -> int:
        """
        Capture evaluation command arguments into the test's captured dictionary.

        Parameters:
            eval_args (argparse.Namespace): The evaluation command arguments to capture.

        Returns:
            int: `0` to indicate successful capture.
        """
        captured["args"] = eval_args
        return 0

    monkeypatch.setattr(workbench, "_evaluate_command", fake_evaluate_command)

    rc = workbench._run_command_chain(
        argparse.Namespace(
            model="ml_models/procedure_classifier.pkl",
            label_column="rule_category",
            eval_label_column="human_category",
            skip_evaluate=False,
            eval_data=None,
            prepared_data="prepared.csv",
            unseen_data="unseen.csv",
            skip_split=False,
        )
    )

    assert rc == 0
    assert captured["args"].label_column == "human_category"


def test_run_and_retrain_parsers_accept_hybrid_threshold():
    run_args = workbench.build_parser().parse_args([
        "run",
        "--hybrid-threshold",
        "0.55",
    ])
    retrain_args = workbench.build_parser().parse_args([
        "retrain",
        "--hybrid-threshold",
        "0.65",
    ])

    assert run_args.hybrid_threshold == pytest.approx(0.55)
    assert retrain_args.hybrid_threshold == pytest.approx(0.65)


def test_review_parser_accepts_auto_retrain_flags():
    args = workbench.build_parser().parse_args([
        "review",
        "--retrain-on-complete",
        "--force",
        "--skip-evaluate",
        "--cross-validate",
        "--hybrid-threshold",
        "0.55",
    ])

    assert args.retrain_on_complete is True
    assert args.force is True
    assert args.skip_evaluate is True
    assert args.cross_validate is True
    assert args.hybrid_threshold == pytest.approx(0.55)


def test_run_command_chain_forwards_explicit_hybrid_threshold(
    tmp_path,
    monkeypatch,
):
    captured: dict[str, argparse.Namespace] = {}
    eval_data = tmp_path / "run-eval.csv"

    monkeypatch.setattr(workbench, "_train_command", lambda _args: 0)
    monkeypatch.setattr(
        workbench, "_resolve_eval_data_for_run", lambda _args: eval_data
    )
    monkeypatch.setattr(workbench, "_print_next_review_step", lambda *_args: None)

    def fake_evaluate_command(eval_args: argparse.Namespace) -> int:
        """
        Capture evaluation command arguments into the test's captured dictionary.

        Parameters:
            eval_args (argparse.Namespace): The evaluation command arguments to capture.

        Returns:
            int: `0` to indicate successful capture.
        """
        captured["args"] = eval_args
        return 0

    monkeypatch.setattr(workbench, "_evaluate_command", fake_evaluate_command)

    rc = workbench._run_command_chain(
        argparse.Namespace(
            model="ml_models/procedure_classifier.pkl",
            label_column="rule_category",
            eval_label_column=None,
            hybrid_threshold=0.55,
            skip_evaluate=False,
            eval_data=None,
            prepared_data="prepared.csv",
            unseen_data="unseen.csv",
            skip_split=False,
        )
    )

    assert rc == 0
    assert captured["args"].hybrid_threshold == pytest.approx(0.55)


def test_run_review_interface_mentions_classic_fallback_on_tui_failure(monkeypatch):
    printed: list[str] = []
    expected = workbench.ReviewSessionMetrics(reviewed_this_session=1)
    runtime = workbench.ReviewRuntime(
        paths=workbench.ReviewPaths(
            model_path=Path("model.pkl"),
            data_path=Path("data.csv"),
            output_path=Path("out.csv"),
            progress_path=Path("progress.json"),
        ),
        config=workbench.ReviewConfig(
            focus="priority",
            low_confidence=0.8,
            max_cases=10,
            ui_mode="tui",
            resume=False,
            retrain_on_complete=False,
        ),
        reviewed_indices=set(),
    )

    monkeypatch.setattr(workbench, "_resolve_review_ui_mode", lambda _config: "tui")
    monkeypatch.setattr(
        workbench,
        "_run_tui_review_session",
        lambda _queue, _runtime: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        workbench,
        "_run_review_classic",
        lambda _queue, _runtime: expected,
    )
    monkeypatch.setattr(
        workbench.console,
        "print",
        lambda message: printed.append(str(message)),
    )

    result = workbench._run_review_interface([], runtime)

    assert result is expected
    assert any("falling back to classic mode" in message for message in printed)


def test_review_command_auto_retrains_after_completed_session(monkeypatch):
    runtime = workbench.ReviewRuntime(
        paths=workbench.ReviewPaths(
            model_path=Path("model.pkl"),
            data_path=Path("data.csv"),
            output_path=Path("review_labels.csv"),
            progress_path=Path("progress.json"),
        ),
        config=workbench.ReviewConfig(
            focus="priority",
            low_confidence=0.8,
            max_cases=10,
            ui_mode="tui",
            resume=False,
            retrain_on_complete=True,
        ),
        reviewed_indices=set(),
    )
    metrics = workbench.ReviewSessionMetrics(
        reviewed_this_session=2,
        labels_recorded=2,
        staged_labels=[
            {
                "procedure": "PROC A",
                "human_category": "Vaginal del",
            }
        ],
    )
    captured: dict[str, argparse.Namespace] = {}

    monkeypatch.setattr(workbench, "_build_review_runtime", lambda _args: runtime)
    monkeypatch.setattr(
        workbench, "_build_review_queue", lambda _runtime: [object(), object()]
    )
    monkeypatch.setattr(
        workbench, "_run_review_interface", lambda _queue, _runtime: metrics
    )
    monkeypatch.setattr(workbench, "_save_review_labels", lambda *_args: None)
    monkeypatch.setattr(workbench, "_print_review_summary", lambda *_args: None)

    def fake_retrain_command(retrain_args: argparse.Namespace) -> int:
        captured["args"] = retrain_args
        return 23

    monkeypatch.setattr(workbench, "_retrain_command", fake_retrain_command)

    args = workbench.build_parser().parse_args([
        "review",
        "--retrain-on-complete",
        "--force",
        "--skip-evaluate",
        "--cross-validate",
        "--hybrid-threshold",
        "0.55",
        "--eval-label-column",
        "human_category",
    ])

    rc = workbench._review_command(args)

    assert rc == 23
    assert captured["args"].review_labels == str(runtime.paths.output_path)
    assert captured["args"].label_column == "rule_category"
    assert captured["args"].force is True
    assert captured["args"].skip_evaluate is True
    assert captured["args"].cross_validate is True
    assert captured["args"].eval_label_column == "human_category"
    assert captured["args"].hybrid_threshold == pytest.approx(0.55)


def test_review_command_does_not_retrain_when_user_quits(monkeypatch):
    runtime = workbench.ReviewRuntime(
        paths=workbench.ReviewPaths(
            model_path=Path("model.pkl"),
            data_path=Path("data.csv"),
            output_path=Path("review_labels.csv"),
            progress_path=Path("progress.json"),
        ),
        config=workbench.ReviewConfig(
            focus="priority",
            low_confidence=0.8,
            max_cases=10,
            ui_mode="tui",
            resume=False,
            retrain_on_complete=True,
        ),
        reviewed_indices=set(),
    )
    metrics = workbench.ReviewSessionMetrics(
        reviewed_this_session=1,
        labels_recorded=1,
        quit_requested=True,
    )
    printed: list[str] = []

    monkeypatch.setattr(workbench, "_build_review_runtime", lambda _args: runtime)
    monkeypatch.setattr(workbench, "_build_review_queue", lambda _runtime: [object()])
    monkeypatch.setattr(
        workbench, "_run_review_interface", lambda _queue, _runtime: metrics
    )
    monkeypatch.setattr(workbench, "_print_review_summary", lambda *_args: None)
    monkeypatch.setattr(workbench, "_save_review_labels", lambda *_args: None)
    monkeypatch.setattr(
        workbench.console,
        "print",
        lambda message: printed.append(str(message)),
    )
    monkeypatch.setattr(
        workbench,
        "_retrain_command",
        lambda _args: pytest.fail("retrain should not run after quit"),
    )

    args = workbench.build_parser().parse_args([
        "review",
        "--retrain-on-complete",
    ])

    rc = workbench._review_command(args)

    assert rc == 0
    assert any("Review ended early" in message for message in printed)
