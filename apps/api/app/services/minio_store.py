from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

_BUCKET = None


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        region_name="us-east-1",
    )


def _ensure_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code == 404:
            client.create_bucket(Bucket=bucket)
        else:
            raise


def _put_object_sync(bucket: str, key: str, body: str, content_type: str) -> None:
    client = _get_s3_client()
    _ensure_bucket(client, bucket)
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType=content_type,
    )


async def put_object(key: str, body: str, content_type: str = "text/plain") -> str:
    """Upload a string object to MinIO and return the full key."""
    bucket = settings.minio_bucket
    await asyncio.to_thread(_put_object_sync, bucket, key, body, content_type)
    return key


async def put_protocol_files(
    review_id: str,
    version: int,
    pico_schema: Dict[str, Any],
    research_question: str,
) -> str:
    """Write protocol_v{n}.md and pico_schema.json to MinIO. Returns prefix."""
    prefix = f"reviews/{review_id}/protocols/v{version}"

    md_content = f"# Systematic Review Protocol\n\n## Research Question\n\n{research_question}\n\n## PICO\n\n"
    md_content += f"**Population**: {pico_schema.get('population', '')}\n\n"
    md_content += f"**Intervention**: {pico_schema.get('intervention', '')}\n\n"
    md_content += f"**Comparator**: {pico_schema.get('comparator', '')}\n\n"
    md_content += "**Outcomes**:\n"
    for o in pico_schema.get("outcomes", []):
        md_content += f"- {o}\n"
    md_content += "\n**Study Designs**:\n"
    for sd in pico_schema.get("study_designs", []):
        md_content += f"- {sd}\n"

    await put_object(
        key=f"{prefix}/protocol_v{version}.md",
        body=md_content,
        content_type="text/markdown",
    )
    await put_object(
        key=f"{prefix}/pico_schema.json",
        body=json.dumps(pico_schema, indent=2),
        content_type="application/json",
    )

    return prefix
