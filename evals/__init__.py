"""lgtmaybe evals — measure whether a model/setting produces usable reviews.

Not part of the per-PR test gate (the runner needs a live model). The scorer is
pure and unit-tested; the runner is invoked on demand:

    python -m evals.run --provider ollama --model qwen3.6:35b \
        --api-base http://localhost:11434
"""
