import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  deleteS3Object,
  deleteS3ObjectsBatch,
  createS3Folder,
  fetchS3UploadConfig,
} from '@/lib/api'

const mockFetch = vi.fn()
global.fetch = mockFetch

beforeEach(() => {
  mockFetch.mockReset()
})

function mockOk(data: unknown) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(data),
  })
}

function mockError(status: number) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    statusText: 'Error',
  })
}

describe('fetchS3UploadConfig', () => {
  it('returns max_upload_bytes from the API', async () => {
    mockOk({ max_upload_bytes: 100 * 1024 * 1024 })
    const cfg = await fetchS3UploadConfig()
    expect(cfg.max_upload_bytes).toBe(100 * 1024 * 1024)
    expect(mockFetch).toHaveBeenCalledWith('/api/s3/upload-config')
  })
})

describe('deleteS3Object', () => {
  it('calls DELETE with encoded bucket', async () => {
    mockOk({ bucket: 'b', deleted: true, key: 'a/b.txt' })
    await deleteS3Object('my bucket', 'a/b.txt')
    expect(mockFetch).toHaveBeenCalledWith('/api/s3/buckets/my%20bucket/objects/a/b.txt', {
      method: 'DELETE',
    })
  })

  it('throws on error', async () => {
    mockError(500)
    await expect(deleteS3Object('b', 'k')).rejects.toThrow('500')
  })
})

describe('deleteS3ObjectsBatch', () => {
  it('posts keys JSON', async () => {
    mockOk({ bucket: 'b', deleted: 2, keys: ['a', 'b'] })
    await deleteS3ObjectsBatch('bkt', { keys: ['a', 'b'] })
    expect(mockFetch).toHaveBeenCalledWith('/api/s3/buckets/bkt/objects/delete-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keys: ['a', 'b'] }),
    })
  })

  it('posts prefix JSON', async () => {
    mockOk({ bucket: 'b', deleted: 1, keys: ['p/x'] })
    await deleteS3ObjectsBatch('bkt', { prefix: 'p/' })
    expect(mockFetch).toHaveBeenCalledWith('/api/s3/buckets/bkt/objects/delete-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prefix: 'p/' }),
    })
  })
})

describe('createS3Folder', () => {
  it('posts folder prefix', async () => {
    mockOk({ bucket: 'b', prefix: 'foo/' })
    await createS3Folder('bkt', 'foo/')
    expect(mockFetch).toHaveBeenCalledWith('/api/s3/buckets/bkt/folders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prefix: 'foo/' }),
    })
  })
})
