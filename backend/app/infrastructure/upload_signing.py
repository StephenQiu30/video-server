"""S3 upload signatures bind each browser-generated Content-Length."""

from dataclasses import dataclass, field
from urllib.parse import quote, urlencode

from botocore.auth import S3SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials


@dataclass(frozen=True)
class UploadSigner:
    origin: str
    region: str
    access_key: str = field(repr=False)
    secret_key: str = field(repr=False)

    def part_url(
        self,
        bucket: str,
        key: str,
        upload_id: str,
        part_number: int,
        *,
        size_bytes: int,
        ttl_seconds: int,
    ) -> str:
        if isinstance(size_bytes, bool) or not 0 < size_bytes <= 5 * 1024**3:
            raise ValueError("upload part length must be between 1 byte and 5 GiB")
        path = f"/{quote(bucket, safe='')}/{quote(key, safe='/')}"
        query = urlencode({"uploadId": upload_id, "partNumber": part_number})
        request = AWSRequest(
            method="PUT",
            url=f"{self.origin}{path}?{query}",
            headers={"Content-Length": str(size_bytes)},
        )
        S3SigV4QueryAuth(
            Credentials(self.access_key, self.secret_key),
            "s3",
            self.region,
            expires=ttl_seconds,
        ).add_auth(request)
        assert request.url is not None
        return request.url
