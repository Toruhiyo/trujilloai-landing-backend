import json
import logging
from pathlib import Path
from tempfile import gettempdir
from typing import Any, IO, Optional

from botocore.config import Config
from botocore.response import StreamingBody
from src.utils.json_toolbox import make_serializable
from pandas import DataFrame

from src.wrappers.aws.errors import S3ObjectNotFoundError
from ...utils.metaclasses import DynamicSingleton
from .errors import InvalidBucketPath
from .exception import AWSException
from .session import Boto3Session
from datetime import datetime

logger = logging.getLogger(__name__)
TMP_DIR = Path(gettempdir())

DEFAULT_MAX_POOL_CONNECTIONS = 100
DEFAULT_UPLOAD_PRESIGNED_URL_EXPIRATION = 3600


class S3Wrapper(metaclass=DynamicSingleton):

    # Public:
    @AWSException.error_handling
    def __init__(
        self,
        credentials: dict | None = None,
        region: Optional[str] = None,
        max_pool_connections: Optional[int] = DEFAULT_MAX_POOL_CONNECTIONS,
    ):
        config_data = {}
        config_data["max_pool_connections"] = max_pool_connections
        if region:
            config_data["region_name"] = region
        config = Config(**config_data)
        self.__client = Boto3Session(credentials=credentials).client(
            "s3", config=config
        )

    @AWSException.error_handling
    def list_buckets(self):
        s3_buckets = self.__client.list_buckets()
        return s3_buckets["Buckets"]

    @AWSException.error_handling
    def get_object_stream(self, bucket: str, key: str | Path) -> StreamingBody:
        key = key.as_posix() if isinstance(key, Path) else key
        logger.info(f"Getting S3 object - Bucket: '{bucket}' - Key: '{key}'")
        obj_stream = self.__client.get_object(Bucket=bucket, Key=key)
        logger.debug(f"Boto3 response: '{obj_stream}'")
        return obj_stream["Body"]

    @AWSException.error_handling
    def get_object_data(self, bucket: str, key: str | Path) -> dict | str | list:
        obj_stream = self.get_object_stream(bucket, key)
        return self.__get_stream_data(obj_stream)

    @AWSException.error_handling
    def get_objects_stream(
        self, bucket: str, prefix: str = "", suffix: str = ""
    ) -> dict[str, StreamingBody]:
        logger.info(
            f"Getting S3 objects - Bucket: '{bucket}' - Prefix: '{prefix}' - Suffix: '{suffix}'"
        )
        obj_streams = {}
        paginator = self.__client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if (
                    key.startswith(prefix)
                    and key.endswith(suffix)
                    and not key.endswith("/")
                ):
                    logger.debug(f"Match found: '{key}'")
                    obj_stream = self.__client.get_object(Bucket=bucket, Key=key)
                    obj_streams[key] = obj_stream["Body"]
        return obj_streams

    @AWSException.error_handling
    def get_objects_data(
        self, bucket: str, prefix: str = "", suffix: str = ""
    ) -> dict[str, dict | str]:
        obj_streams = self.get_objects_stream(bucket, prefix, suffix)
        return {
            key: self.__get_stream_data(obj_stream)
            for key, obj_stream in obj_streams.items()
        }

    @AWSException.error_handling
    def put_object_data(
        self, bucket: str, key: str | Path, data: Any, **kwargs
    ) -> bool:
        key = key.as_posix() if isinstance(key, Path) else key
        logger.debug(f"Inserting object - Bucket: '{bucket}' - Key: '{key}'")
        serializable_data = make_serializable(data, ensure_ascii=False)
        response = self.__client.put_object(
            Bucket=bucket,
            Key=key,
            Body=(
                serializable_data
                if isinstance(data, DataFrame)
                else json.dumps(serializable_data, ensure_ascii=False).encode("utf-8")
            ),
            **kwargs,
        )
        logger.debug(f"Boto3 response: '{response}'")
        return True

    @AWSException.error_handling
    def upload_file(self, bucket: str, local_filepath: Path, key: Path | str = ""):
        key = key.as_posix() if isinstance(key, Path) else key
        response = self.__client.upload_file(str(local_filepath), bucket, key)
        return response

    @AWSException.error_handling
    def download_file(
        self, bucket: str, key: Path | str, local_filepath: Optional[Path] = None
    ) -> Path:
        s3_client = self.__client
        local_filepath = (
            local_filepath or TMP_DIR / f"{datetime.now().isoformat()}_{Path(key).name}"
        )
        response = s3_client.download_file(bucket, str(key), str(local_filepath))
        key = key.as_posix() if isinstance(key, Path) else key
        response = self.__client.download_file(bucket, key, str(local_filepath))
        return local_filepath

    @AWSException.error_handling
    def upload_fileobj(
        self,
        bucket: str,
        file: IO,
        key: Path | str = "",
        content_type: Optional[str] = None,
        extra_args: Optional[dict] = None,
    ):
        extra_args = extra_args or {}
        if isinstance(content_type, str):
            extra_args["ContentType"] = content_type
        key = key.as_posix() if isinstance(key, Path) else key
        response = self.__client.upload_fileobj(
            file,
            bucket,
            key,
            ExtraArgs=extra_args,
        )
        return response

    @AWSException.error_handling
    def delete_object(self, bucket: str, key: str | Path):
        key = key.as_posix() if isinstance(key, Path) else key
        response = self.__client.delete_object(Bucket=bucket, Key=key)
        return response

    @AWSException.error_handling
    def generate_presigned_get_url(
        self,
        bucket: str,
        key: str | Path,
        expiration: int = DEFAULT_UPLOAD_PRESIGNED_URL_EXPIRATION,
    ) -> str:
        key = key.as_posix() if isinstance(key, Path) else key
        url = self.__client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket,
                "Key": key,
            },
            ExpiresIn=expiration,
        )
        return url

    @AWSException.error_handling
    def generate_presigned_put_url(
        self,
        bucket: str,
        key: str | Path,
        expiration: int = DEFAULT_UPLOAD_PRESIGNED_URL_EXPIRATION,
        content_type: Optional[str] = None,
    ) -> str:
        key = key.as_posix() if isinstance(key, Path) else key
        params = {
            "Bucket": bucket,
            "Key": key,
        }
        if content_type:
            params["ContentType"] = content_type
        url = self.__client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=expiration,
        )
        return url

    @AWSException.error_handling
    def generate_presigned_post_url(
        self,
        bucket: str,
        key: str | Path,
        expiration: int = DEFAULT_UPLOAD_PRESIGNED_URL_EXPIRATION,
        conditions: Optional[list[list[str]]] = None,
        fields: Optional[dict] = None,
    ) -> dict[str, str]:
        """Generate a presigned URL S3 POST request to upload a file with specific conditions"""
        key = key.as_posix() if isinstance(key, Path) else key
        response = self.__client.generate_presigned_post(
            bucket,
            key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration,
        )
        return response

    @AWSException.error_handling
    def move_file(self, bucket: str, src_key: Path | str, dst_key: Path | str) -> bool:
        src_key = src_key.as_posix() if isinstance(src_key, Path) else src_key
        dst_key = dst_key.as_posix() if isinstance(dst_key, Path) else dst_key
        src_path = f"{bucket}/{src_key}"
        try:
            self.__client.copy_object(
                CopySource=src_path,
                Bucket=bucket,
                Key=dst_key,
            )
        except Exception as e:
            if "NoSuchKey".lower() in str(e).lower():
                raise S3ObjectNotFoundError(f"Not found object with key: {src_key}")
            raise e
        self.__client.delete_object(Bucket=bucket, Key=src_key)
        return True

    @AWSException.error_handling
    def list_bucket_objects(
        self, bucket: str, prefix: str = "", exact_key: bool = False
    ) -> list[dict]:
        results = self.__client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        if "Contents" not in results:
            raise InvalidBucketPath(f"path: {prefix}")
        objects = [dict(item) for item in results["Contents"]]
        if exact_key:
            objects = list(filter(lambda obj: obj["Key"] == prefix, objects))
        return objects

    @AWSException.error_handling
    def list_bucket_objects_keys(
        self, bucket: str, prefix: str = "", exact_key: bool = False
    ) -> list[Path]:
        objects = self.list_bucket_objects(bucket, prefix=prefix, exact_key=exact_key)
        return [Path(object["Key"]) for object in objects]

    # Private:
    def __get_stream_data(self, stream: StreamingBody) -> dict | str:
        content_bytes = stream.read()
        try:
            return json.loads(content_bytes)
        except json.JSONDecodeError:
            return content_bytes.decode("utf-8")
