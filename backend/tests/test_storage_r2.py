from __future__ import annotations

import io
import unittest

from botocore.exceptions import ClientError

from backend.services.storage import R2AssetStorage


class FakeS3Client:
    """内存版 S3 client，支持分页列举以覆盖 list_objects_v2 分页逻辑。"""

    def __init__(self, objects: dict[str, bytes] | None = None, page_size: int = 1000) -> None:
        self.objects = dict(objects or {})
        self.page_size = page_size
        self.last_list_bucket: str | None = None

    def get_paginator(self, name: str):
        assert name == "list_objects_v2"
        client = self

        class _Paginator:
            def paginate(self, *, Bucket: str, Prefix: str):
                client.last_list_bucket = Bucket
                keys = sorted(key for key in client.objects if key.startswith(Prefix))
                for start in range(0, len(keys), client.page_size):
                    chunk = keys[start:start + client.page_size]
                    yield {
                        "Contents": [
                            {"Key": key, "Size": len(client.objects[key])}
                            for key in chunk
                        ]
                    }

        return _Paginator()

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "not found"}},
                "GetObject",
            )
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        self.objects[Key] = bytes(Body)

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)

    def head_object(self, *, Bucket: str, Key: str) -> dict:
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "404", "Message": "not found"}},
                "HeadObject",
            )
        return {"ContentLength": len(self.objects[Key])}


PREFIX = "assets/images/2026-05-26"


def build_storage(client: FakeS3Client) -> R2AssetStorage:
    return R2AssetStorage(client, bucket="tzlb-assets", prefix=PREFIX)


class R2AssetStorageTest(unittest.TestCase):
    def test_write_read_roundtrip_uses_prefixed_key(self) -> None:
        client = FakeS3Client()
        storage = build_storage(client)

        storage.write("MQ001-1.jpg", b"image-bytes")

        self.assertEqual(client.objects, {f"{PREFIX}/MQ001-1.jpg": b"image-bytes"})
        self.assertEqual(storage.read("MQ001-1.jpg"), b"image-bytes")

    def test_list_filters_nested_and_foreign_prefixes(self) -> None:
        client = FakeS3Client(
            {
                f"{PREFIX}/MQ001-1.jpg": b"1234",
                f"{PREFIX}/MQ001-2.jpg": b"12",
                f"{PREFIX}/nested/MQ002-1.jpg": b"x",
                "assets/images/2026-05-27/MQ001-1.jpg": b"other-date",
                "assets/points/MQ001.jpg": b"other-prefix",
            }
        )

        objects = build_storage(client).list()

        self.assertEqual(
            {(obj.name, obj.size_bytes) for obj in objects},
            {("MQ001-1.jpg", 4), ("MQ001-2.jpg", 2)},
        )
        self.assertEqual(client.last_list_bucket, "tzlb-assets")

    def test_list_follows_pagination(self) -> None:
        client = FakeS3Client(page_size=2)
        storage = build_storage(client)
        for index in range(5):
            storage.write(f"MQ001-{index}.jpg", bytes([index]))

        self.assertEqual(len(storage.list()), 5)

    def test_read_missing_raises_not_found(self) -> None:
        storage = build_storage(FakeS3Client())
        with self.assertRaises(FileNotFoundError):
            storage.read("missing.jpg")

    def test_exists_and_delete(self) -> None:
        client = FakeS3Client({f"{PREFIX}/MQ001-1.jpg": b"x"})
        storage = build_storage(client)

        self.assertTrue(storage.exists("MQ001-1.jpg"))
        self.assertFalse(storage.exists("MQ001-9.jpg"))

        storage.delete("MQ001-1.jpg")
        self.assertFalse(storage.exists("MQ001-1.jpg"))
        # 删除不存在的对象保持幂等
        storage.delete("MQ001-1.jpg")

    def test_rejects_path_traversal_names(self) -> None:
        storage = build_storage(FakeS3Client())
        with self.assertRaisesRegex(ValueError, "文件名不合法"):
            storage.write("../escape.jpg", b"x")
        with self.assertRaisesRegex(ValueError, "文件名不合法"):
            storage.read("nested/MQ001.jpg")


if __name__ == "__main__":
    unittest.main()
