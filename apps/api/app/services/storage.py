from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode


class ObjectStorage:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self, public: bool = False):
        try:
            import boto3
            from botocore.client import Config
        except ModuleNotFoundError as exc:
            raise AppError(ErrorCode.STORAGE_UNAVAILABLE, "对象存储客户端未安装", 503) from exc
        
        endpoint = self.settings.s3_public_endpoint_url if public and self.settings.s3_public_endpoint_url else self.settings.s3_endpoint_url
        
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=self.settings.s3_access_key_id,
            aws_secret_access_key=self.settings.s3_secret_access_key,
            region_name=self.settings.s3_region,
            config=Config(s3={"addressing_style": "path" if self.settings.s3_force_path_style else "auto"}),
        )

    def ensure_bucket(self) -> None:
        client = self._client()
        buckets = client.list_buckets().get("Buckets", [])
        if any(bucket.get("Name") == self.settings.s3_bucket for bucket in buckets):
            return
        client.create_bucket(Bucket=self.settings.s3_bucket)

    def upload_file(self, local_path: str, object_key: str, content_type: str = "application/octet-stream") -> None:
        self.ensure_bucket()
        self._client().upload_file(
            local_path,
            self.settings.s3_bucket,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

    def presign_download_url(self, object_key: str) -> str:
        return self._client(public=True).generate_presigned_url(
            "get_object",
            Params={"Bucket": self.settings.s3_bucket, "Key": object_key},
            ExpiresIn=self.settings.presigned_url_ttl_seconds,
        )

    def get_object(self, object_key: str):
        try:
            return self._client().get_object(Bucket=self.settings.s3_bucket, Key=object_key)
        except Exception as exc:
            response = getattr(exc, "response", {})
            error_code = response.get("Error", {}).get("Code")
            if error_code in {"NoSuchKey", "404", "NotFound"}:
                raise AppError(ErrorCode.RETENTION_EXPIRED, "文件不存在或已过期，请重新创建任务", 410) from exc
            raise

    def delete_object(self, object_key: str) -> None:
        self._client().delete_object(Bucket=self.settings.s3_bucket, Key=object_key)
