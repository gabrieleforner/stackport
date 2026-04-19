"""Tests for S3 API routes (write operations and reads)."""

import io
import os

os.environ.setdefault("AWS_ENDPOINT_URL", "http://localhost:4566")

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


class TestUploadObject:
    @patch("backend.routes.s3.get_client")
    def test_upload_puts_object(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        files = {"file": ("hello.txt", io.BytesIO(b"hello world"), "text/plain")}
        resp = client.post(
            "/api/s3/buckets/my-bucket/objects",
            files=files,
            params={"prefix": "p/"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["bucket"] == "my-bucket"
        assert data["key"] == "p/hello.txt"
        assert data["size"] == 11
        mock_s3.put_object.assert_called_once()
        call_kw = mock_s3.put_object.call_args.kwargs
        assert call_kw["Bucket"] == "my-bucket"
        assert call_kw["Key"] == "p/hello.txt"
        assert call_kw["Body"] == b"hello world"
        assert call_kw["ContentType"] == "text/plain"

    @patch("backend.routes.s3.get_client")
    def test_upload_uses_guess_when_browser_octet_stream(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        files = {"file": ("note.txt", io.BytesIO(b"x"), "application/octet-stream")}
        resp = client.post("/api/s3/buckets/b/objects", files=files)
        assert resp.status_code == 200
        assert resp.json()["content_type"] == "text/plain"
        assert mock_s3.put_object.call_args.kwargs["ContentType"] == "text/plain"

    @patch("backend.routes.s3.get_client")
    def test_upload_prefers_extension_when_browser_disagrees(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        files = {"file": ("photo.png", io.BytesIO(b"x"), "image/jpeg")}
        resp = client.post("/api/s3/buckets/b/objects", files=files)
        assert resp.status_code == 200
        assert resp.json()["content_type"] == "image/png"
        assert mock_s3.put_object.call_args.kwargs["ContentType"] == "image/png"

    @patch("backend.routes.s3.S3_MAX_UPLOAD_BYTES", 10)
    @patch("backend.routes.s3.get_client")
    def test_upload_rejects_large_file(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        files = {"file": ("big.bin", io.BytesIO(b"x" * 11), "application/octet-stream")}
        resp = client.post("/api/s3/buckets/b/objects", files=files)
        assert resp.status_code == 413


class TestS3UploadConfig:
    @patch("backend.routes.s3.S3_MAX_UPLOAD_BYTES", 99)
    def test_upload_config_returns_limit(self):
        resp = client.get("/api/s3/upload-config")
        assert resp.status_code == 200
        assert resp.json() == {"max_upload_bytes": 99}


class TestDeleteObject:
    @patch("backend.routes.s3.get_client")
    def test_delete_single(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        resp = client.delete("/api/s3/buckets/bkt/objects/foo/bar.txt")
        assert resp.status_code == 200
        assert resp.json() == {"bucket": "bkt", "deleted": True, "key": "foo/bar.txt"}
        mock_s3.delete_object.assert_called_once_with(Bucket="bkt", Key="foo/bar.txt")


class TestDeleteBatch:
    @patch("backend.routes.s3.get_client")
    def test_delete_by_keys(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3
        mock_s3.delete_objects.return_value = {}

        resp = client.post(
            "/api/s3/buckets/bkt/objects/delete-batch",
            json={"keys": ["a.txt", "b.txt"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] == 2
        assert len(data["keys"]) == 2
        mock_s3.delete_objects.assert_called_once()

    @patch("backend.routes.s3.get_client")
    def test_delete_by_prefix_lists_and_deletes(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        paginator = MagicMock()
        mock_s3.get_paginator.return_value = paginator
        paginator.paginate.return_value = [
            {"Contents": [{"Key": "p/a.txt"}, {"Key": "p/b.txt"}]},
        ]
        mock_s3.delete_objects.return_value = {}

        resp = client.post(
            "/api/s3/buckets/bkt/objects/delete-batch",
            json={"prefix": "p/"},
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2


class TestCreateFolder:
    @patch("backend.routes.s3.get_client")
    def test_create_folder_marker(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        resp = client.post(
            "/api/s3/buckets/bkt/folders",
            json={"prefix": "new-folder/"},
        )
        assert resp.status_code == 200
        mock_s3.put_object.assert_called_once_with(
            Bucket="bkt",
            Key="new-folder/",
            Body=b"",
            ContentType="application/x-directory",
        )


class TestValidation:
    def test_delete_batch_requires_one_mode(self):
        resp = client.post("/api/s3/buckets/b/objects/delete-batch", json={})
        assert resp.status_code == 422

    def test_create_folder_requires_trailing_slash(self):
        resp = client.post(
            "/api/s3/buckets/b/folders",
            json={"prefix": "bad"},
        )
        assert resp.status_code == 422
