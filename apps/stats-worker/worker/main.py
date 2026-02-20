"""
Stats Worker: Python + R microservice for meta-analysis computations.

Receives jobs from Redis queue, runs R scripts via rpy2 or subprocess,
and returns results (forest plot data, heterogeneity stats, etc.).
"""

import os
import json
import logging
import subprocess
import tempfile
from pathlib import Path

import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = "stats_jobs"


def run_r_script(script: str, data: dict) -> dict:
    """Execute an R script with input data, return parsed JSON output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.json"
        output_path = Path(tmpdir) / "output.json"
        r_script_path = Path(tmpdir) / "analysis.R"

        input_path.write_text(json.dumps(data))
        r_script_path.write_text(script)

        result = subprocess.run(
            ["Rscript", str(r_script_path), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error("R script failed: %s", result.stderr)
            raise RuntimeError(f"R script error: {result.stderr}")

        if output_path.exists():
            return json.loads(output_path.read_text())
        return {}


def process_job(job: dict) -> dict:
    """Dispatch job to appropriate analysis function."""
    job_type = job.get("type")

    if job_type == "meta_analysis":
        return run_meta_analysis(job["data"])
    elif job_type == "heterogeneity":
        return run_heterogeneity_test(job["data"])
    elif job_type == "forest_plot":
        return generate_forest_plot_data(job["data"])
    else:
        raise ValueError(f"Unknown job type: {job_type}")


def run_meta_analysis(data: dict) -> dict:
    script = """
library(meta)
library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
input <- fromJSON(args[1])
output_path <- args[2]

ma <- metagen(
  TE = input$effect_sizes,
  seTE = input$standard_errors,
  studlab = input$study_labels,
  method.tau = "REML",
  hakn = TRUE
)

result <- list(
  pooled_effect = ma$TE.random,
  pooled_se = ma$seTE.random,
  ci_lower = ma$lower.random,
  ci_upper = ma$upper.random,
  i_squared = ma$I2,
  tau_squared = ma$tau2,
  p_value = ma$pval.random,
  k = ma$k
)

write(toJSON(result, auto_unbox = TRUE), output_path)
"""
    return run_r_script(script, data)


def run_heterogeneity_test(data: dict) -> dict:
    script = """
library(meta)
library(jsonlite)

args <- commandArgs(trailingOnly = TRUE)
input <- fromJSON(args[1])
output_path <- args[2]

ma <- metagen(
  TE = input$effect_sizes,
  seTE = input$standard_errors,
  studlab = input$study_labels
)

result <- list(
  Q = ma$Q,
  df = ma$df.Q,
  p_Q = ma$pval.Q,
  I2 = ma$I2,
  tau2 = ma$tau2,
  H = ma$H
)

write(toJSON(result, auto_unbox = TRUE), output_path)
"""
    return run_r_script(script, data)


def generate_forest_plot_data(data: dict) -> dict:
    """Return structured data for frontend forest plot rendering."""
    studies = data.get("studies", [])
    return {
        "studies": studies,
        "pooled": data.get("pooled", {}),
        "plot_config": {
            "x_label": data.get("x_label", "Effect Size"),
            "null_value": data.get("null_value", 0),
        },
    }


def main():
    r = redis.from_url(REDIS_URL)
    logger.info("Stats worker started, listening on queue: %s", QUEUE_NAME)

    while True:
        try:
            _, raw = r.blpop(QUEUE_NAME, timeout=5)
            if raw is None:
                continue

            job = json.loads(raw)
            job_id = job.get("id", "unknown")
            logger.info("Processing job %s (type=%s)", job_id, job.get("type"))

            result = process_job(job)

            result_key = f"result:{job_id}"
            r.setex(result_key, 3600, json.dumps(result))
            logger.info("Job %s completed, result stored at %s", job_id, result_key)

        except redis.exceptions.ConnectionError as e:
            logger.error("Redis connection error: %s", e)
        except Exception as e:
            logger.exception("Job processing error: %s", e)


if __name__ == "__main__":
    main()
