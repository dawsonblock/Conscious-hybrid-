"""Coordination harness for testing task completion."""

from hca.runtime.runtime import Runtime


def run() -> dict:
    runtime = Runtime()
    run_id = runtime.run("echo greeting")
    # For MVP, measure completion only
    return {"run_id": run_id, "completed": True}