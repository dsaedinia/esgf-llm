#!/usr/bin/env python3
"""
Utility script to benchmark Ollama-based LLM inference performance.

Collected metrics per trial:
  - Time to First Token (TTFT): latency between request start and first streamed token.
  - Prompt processing speed: prompt tokens per second (derived from Ollama's prompt_eval_* telemetry).
  - Generation throughput: generated tokens per second (derived from eval_* telemetry).

The script streams responses to measure TTFT accurately and surfaces summary statistics
across multiple trials so you can compare CPU- vs GPU-backed runs or even different runtimes.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import ollama


@dataclass
class TrialResult:
    """Container for per-trial telemetry."""

    index: int
    total_duration_s: float
    ttft_s: Optional[float]
    prompt_tokens: int
    prompt_eval_duration_s: Optional[float]
    prompt_tps: Optional[float]
    generation_tokens: int
    generation_duration_s: Optional[float]
    generation_tps: Optional[float]
    load_duration_s: Optional[float]
    reported_total_duration_s: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt
    if args.prompt_file is not None:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    return (
        "Write a concise technical summary of the tradeoffs between CPU and GPU "
        "inference for large language models."
    )


def _build_options(args: argparse.Namespace) -> Dict[str, Any]:
    options: Dict[str, Any] = {}
    if args.max_tokens is not None:
        options["num_predict"] = args.max_tokens
    if args.temperature is not None:
        options["temperature"] = args.temperature
    if args.top_p is not None:
        options["top_p"] = args.top_p
    if args.top_k is not None:
        options["top_k"] = args.top_k
    if args.repeat_penalty is not None:
        options["repeat_penalty"] = args.repeat_penalty
    if args.num_ctx is not None:
        options["num_ctx"] = args.num_ctx
    return options


def _nan_safe_rate(count: int, duration_s: Optional[float]) -> Optional[float]:
    if not count or duration_s is None or duration_s <= 0:
        return None
    return count / duration_s


def _collect_stream(
    *, model: str, prompt: str, options: Dict[str, Any], keep_alive: Optional[str]
) -> Iterable[Dict[str, Any]]:
    kwargs: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": options or None,
    }
    if keep_alive is not None:
        kwargs["keep_alive"] = keep_alive
    return ollama.generate(**kwargs)


def run_trial(*, trial_index: int, model: str, prompt: str, options: Dict[str, Any], keep_alive: Optional[str]) -> TrialResult:
    start = time.perf_counter()
    first_token_time: Optional[float] = None
    final_chunk: Optional[Dict[str, Any]] = None

    for chunk in _collect_stream(model=model, prompt=prompt, options=options, keep_alive=keep_alive):
        if first_token_time is None and chunk.get("response"):
            first_token_time = time.perf_counter()
        if chunk.get("done"):
            final_chunk = chunk

    end = time.perf_counter()

    if final_chunk is None:
        raise RuntimeError(
            "Stream ended without receiving a terminating chunk from Ollama.")

    ttft = (first_token_time - start) if first_token_time is not None else None

    prompt_tokens = int(final_chunk.get("prompt_eval_count") or 0)
    prompt_eval_duration_s = _nan_safe_divide(
        final_chunk.get("prompt_eval_duration"))
    prompt_tps = _nan_safe_rate(prompt_tokens, prompt_eval_duration_s)

    generation_tokens = int(final_chunk.get("eval_count") or 0)
    generation_duration_s = _nan_safe_divide(final_chunk.get("eval_duration"))
    generation_tps = _nan_safe_rate(generation_tokens, generation_duration_s)

    load_duration_s = _nan_safe_divide(final_chunk.get("load_duration"))
    reported_total_duration_s = _nan_safe_divide(
        final_chunk.get("total_duration"))

    return TrialResult(
        index=trial_index,
        total_duration_s=end - start,
        ttft_s=ttft,
        prompt_tokens=prompt_tokens,
        prompt_eval_duration_s=prompt_eval_duration_s,
        prompt_tps=prompt_tps,
        generation_tokens=generation_tokens,
        generation_duration_s=generation_duration_s,
        generation_tps=generation_tps,
        load_duration_s=load_duration_s,
        reported_total_duration_s=reported_total_duration_s,
    )


def _nan_safe_divide(value_ns: Optional[int]) -> Optional[float]:
    if not value_ns:
        return None
    return value_ns / 1_000_000_000


def _format_float(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def _format_int(value: int) -> str:
    return f"{value:,}"


def _summarize(values: List[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [v for v in values if v is not None]
    if not clean:
        return {"mean": None, "stdev": None, "min": None, "max": None}
    return {
        "mean": statistics.fmean(clean),
        "stdev": statistics.stdev(clean) if len(clean) > 1 else 0.0,
        "min": min(clean),
        "max": max(clean),
    }


def print_table(trials: List[TrialResult]) -> None:
    header = (
        f"{'Trial':>5} | {'Total(s)':>8} | {'TTFT(s)':>8} | {'Prompt tok':>10} | "
        f"{'Prompt t/s':>10} | {'Gen tok':>8} | {'Gen t/s':>8}"
    )
    print(header)
    print("-" * len(header))
    for result in trials:
        row = (
            f"{result.index:>5} | "
            f"{_format_float(result.total_duration_s):>8} | "
            f"{_format_float(result.ttft_s):>8} | "
            f"{_format_int(result.prompt_tokens):>10} | "
            f"{_format_float(result.prompt_tps):>10} | "
            f"{_format_int(result.generation_tokens):>8} | "
            f"{_format_float(result.generation_tps):>8}"
        )
        print(row)


def print_summary(trials: List[TrialResult]) -> None:
    print("\nSummary statistics:")
    fields = [
        ("TTFT(s)", [t.ttft_s for t in trials]),
        ("Prompt t/s", [t.prompt_tps for t in trials]),
        ("Generation t/s", [t.generation_tps for t in trials]),
        ("Total time(s)", [t.total_duration_s for t in trials]),
    ]
    for label, values in fields:
        stats = _summarize(values)
        line = (
            f"  {label:<15} mean={_format_float(stats['mean'])}"
            f", stdev={_format_float(stats['stdev'])}"
            f", min={_format_float(stats['min'])}"
            f", max={_format_float(stats['max'])}"
        )
        print(line)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True,
                        help="Ollama model identifier (e.g. 'llama3:8b').")

    prompt_group = parser.add_mutually_exclusive_group()
    prompt_group.add_argument("--prompt", help="Prompt text to evaluate.")
    prompt_group.add_argument(
        "--prompt-file", help="Path to file containing the prompt.")

    parser.add_argument("--num-trials", type=int, default=3,
                        help="Number of benchmark trials to run.")
    parser.add_argument("--max-tokens", type=int,
                        help="Maximum new tokens to generate (maps to num_predict).")
    parser.add_argument("--temperature", type=float,
                        help="Sampling temperature.")
    parser.add_argument("--top-p", type=float, help="Top-p sampling value.")
    parser.add_argument("--top-k", type=int, help="Top-k sampling value.")
    parser.add_argument("--repeat-penalty", type=float,
                        help="Repeat penalty option.")
    parser.add_argument("--num-ctx", type=int,
                        help="Context window size to request.")
    parser.add_argument(
        "--tag", help="Optional label for this benchmark run (e.g. 'GPU', 'CPU').")
    parser.add_argument("--keep-alive", dest="keep_alive",
                        help="Override Ollama keep-alive setting (e.g. '0s').")
    parser.add_argument("--json", action="store_true",
                        help="Emit JSON instead of formatted text.")

    args = parser.parse_args(argv)

    if args.num_trials < 1:
        parser.error("num-trials must be >= 1")

    prompt = _read_prompt(args)
    options = _build_options(args)

    trials: List[TrialResult] = []
    for idx in range(1, args.num_trials + 1):
        try:
            result = run_trial(
                trial_index=idx,
                model=args.model,
                prompt=prompt,
                options=options,
                keep_alive=args.keep_alive,
            )
        except Exception as exc:  # pragma: no cover - surfaced to user
            print(f"Trial {idx} failed: {exc}", file=sys.stderr)
            raise
        trials.append(result)

    if args.json:
        payload = {
            "tag": args.tag,
            "model": args.model,
            "num_trials": args.num_trials,
            "results": [t.to_dict() for t in trials],
            "summary": {
                "ttft_s": _summarize([t.ttft_s for t in trials]),
                "prompt_tokens_per_s": _summarize([t.prompt_tps for t in trials]),
                "generation_tokens_per_s": _summarize([t.generation_tps for t in trials]),
                "total_time_s": _summarize([t.total_duration_s for t in trials]),
            },
        }
        json.dump(payload, sys.stdout, indent=2)
        print()
        return 0

    if args.tag:
        print(f"Benchmark tag: {args.tag}")
    print(f"Model: {args.model}")
    print(f"Prompt length (chars): {len(prompt)}")
    if options:
        print(f"Options: {options}")
    print_table(trials)
    print_summary(trials)
    return 0


if __name__ == "__main__":
    sys.exit(main())
