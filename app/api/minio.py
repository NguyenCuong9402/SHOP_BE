# init minio (s3 local)
from io import BytesIO

from minio import S3Error, Minio

from app.utils import get_timestamp_now


class MinioClient:
    def __init__(self):
        # self.minio_url = f"{config.MINIO_URL}:{config.MINIO_PORT}"
        self.minio_url = "127.0.0.1:9000"
        self.access_key = "minioadmin"
        self.secret_key = "minioadmin"
        self.bucket_name = "viettin-image"
        self.client = Minio(
            self.minio_url,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )
        self.make_bucket()

    def make_bucket(self) -> str:
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        return self.bucket_name

    def upload_image(self, file_data: str, file_path: str):
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=file_path,
                data=file_data,
                length=-1,
                part_size=10 * 1024 * 1024
            )
            return True, ""
        except S3Error as exc:
            return False, exc

    def download_image_stream(self, file_path: str):
        try:
            response = self.client.get_object(self.bucket_name, file_path)
            return True, response
        except S3Error as exc:
            return False, str(exc)


def handle_image_upload(minio_client, image):
    file_path = f"{str(get_timestamp_now())}_{image.filename}"
    file_data = BytesIO(image.read())
    try:
        success, message = minio_client.upload_image(file_data=file_data, file_path=file_path)
        if not success:
            return False, message
        return True, None  # Or a meaningful success value

    except Exception as e:
        return False, str(e)
