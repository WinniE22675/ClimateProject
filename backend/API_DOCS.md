# API Documentation

## Overview

This API is built with **FastAPI** and provides two primary sets of routes:

- **Authentication** (`/auth`) — user login and JWT token management.
- **Datasets & Shapefiles** (`/datasets`, `/shapefiles`, `/maps`) — file uploads, processing, index calculation, map generation, and workspace management.

---

## Authentication

All protected endpoints require a **Bearer token** in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are JWTs containing the user's `id` and `role`. They expire based on the server-configured `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 1440 minutes / 24 hours).

### Roles

| Role | Description |
|---|---|
| `viewer` | Can read datasets and files |
| `analyst` | Can upload, process, calculate, and delete |

---

## Auth Routes

### POST `/auth/login`

Authenticate a user and receive a JWT access token.

**Request Body**

```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response `200 OK`**

```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer"
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `401 Unauthorized` | Incorrect email or password |

---

## Dataset Routes

### POST `/datasets/{slot_id}/upload`

Upload one or more raw files into a **Preset slot**.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `slot_id` | `int` | Preset slot (1–4) |

**Request Body:** `multipart/form-data`

| Field | Type | Description |
|---|---|---|
| `files` | `File[]` | One or more files to upload |

**Response `200 OK`**

```json
{
  "message": "Saved 2 files",
  "files": ["file1.nc", "file2.nc"]
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `400 Bad Request` | Invalid slot ID (must be 1–4) |

---

### GET `/datasets/{slot_id}/files`

List all files uploaded to a **Preset slot** for the current user.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `slot_id` | `int` | Preset slot (1–4) |

**Response `200 OK`**

```json
["file1.nc", "file2.nc"]
```

---

### DELETE `/datasets/{slot_id}/files/{filename}`

Delete a specific file from a slot.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `slot_id` | `int` | Slot number (1–4) |
| `filename` | `string` | Name of the file to delete |

**Response `200 OK`**

```json
{
  "message": "Deleted file1.nc"
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `404 Not Found` | File not found |

---

### POST `/datasets/process_selection`

Trigger background processing of a dataset from a Preset slot with an optional spatial and temporal scope filter.

**Auth Required:** `analyst`

**Request Body**

```json
{
  "slot_id": 1,
  "dataset_name": "my_dataset",
  "scope": {
    "startYear": 2000,
    "endYear": 2020,
    "minLat": 10.0,
    "maxLat": 25.0,
    "minLon": 95.0,
    "maxLon": 110.0
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `slot_id` | `int` | Yes | Preset slot (1–4) |
| `dataset_name` | `string` | Yes | Unique name for the output dataset |
| `scope.startYear` | `int` | No | Start year filter |
| `scope.endYear` | `int` | No | End year filter |
| `scope.minLat` | `float` | No | Minimum latitude |
| `scope.maxLat` | `float` | No | Maximum latitude |
| `scope.minLon` | `float` | No | Minimum longitude |
| `scope.maxLon` | `float` | No | Maximum longitude |

**Response `200 OK`**

```json
{
  "status": "success",
  "dataset_name": "my_dataset"
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `400 Bad Request` | Dataset name already exists |
| `500 Internal Server Error` | Unexpected processing error |

---

### GET `/datasets`

List all available datasets that have a completed `merged.nc` file.

**Auth Required:** None

**Response `200 OK`**

```json
{
  "datasets": ["dataset_a", "dataset_b"]
}
```

---

### GET `/datasets/{dataset_name}/status`

Check the current processing status of a dataset.

**Auth Required:** None

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dataset_name` | `string` | Name of the dataset |

**Response `200 OK`**

```json
{
  "status": "processing"
}
```

---

### GET `/datasets/{dataset_name}/metadata`

Retrieve the metadata JSON for a processed dataset.

**Auth Required:** None

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dataset_name` | `string` | Name of the dataset |

**Response `200 OK`**

Returns the raw contents of `output/{dataset_name}/metadata.json`.

**Error Responses**

| Status | Detail |
|---|---|
| `404 Not Found` | Metadata not found or dataset empty |
| `500 Internal Server Error` | Failed to read metadata |

---

### GET `/datasets/{dataset_name}/download_merged`

Download the merged NetCDF file for a dataset.

**Auth Required:** None

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dataset_name` | `string` | Name of the dataset |

**Response `200 OK`**

Returns the file `output/{dataset_name}/merged.nc` as a file download named `{dataset_name}_merged.nc`.

**Error Responses**

| Status | Detail |
|---|---|
| `404 Not Found` | File not ready |

---

### POST `/datasets/{dataset_name}/calculate_indices`

Start a background job to calculate climate/drought indices for a dataset.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dataset_name` | `string` | Name of the dataset |

**Request Body**

```json
{
  "selected_indices": ["SPI", "SPEI"],
  "shapefile_name": "thailand_admin",
  "target_col": "NAME_1",
  "country": "Thailand",
  "baseline": {
    "start_year": 1981,
    "end_year": 2010
  },
  "spi_threshold": 1.0,
  "is_existing": false
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `selected_indices` | `string[]` | Yes | List of index names to calculate |
| `shapefile_name` | `string` | Yes | Name of the shapefile to use |
| `target_col` | `string` | Yes | Column in shapefile to use for aggregation |
| `country` | `string` | Yes | Country name for spatial context |
| `baseline.start_year` | `int` | No | Baseline period start year |
| `baseline.end_year` | `int` | No | Baseline period end year |
| `spi_threshold` | `float` | No | SPI threshold value (default: `1.0`) |
| `is_existing` | `bool` | No | Whether using an existing calculation (default: `false`) |

**Response `200 OK`**

```json
{
  "status": "processing",
  "message": "Indices calculation started in background"
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `500 Internal Server Error` | Unexpected error during scheduling |

---

### DELETE `/datasets/{dataset_name}`

Delete an entire dataset and its associated output files.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dataset_name` | `string` | Name of the dataset to delete |

**Response `200 OK`**

```json
{
  "status": "success",
  "dataset": "my_dataset",
  "deleted": ["output"],
  "missing": [],
  "deleted_by": "user@example.com"
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `404 Not Found` | Dataset not found |
| `500 Internal Server Error` | Failed to delete dataset directory |

---

### DELETE `/datasets/{dataset_name}/workspaces/{workspace_name}`

Delete a specific workspace (a calculation result set) within a dataset.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `dataset_name` | `string` | Name of the parent dataset |
| `workspace_name` | `string` | Name of the workspace to delete |

**Response `200 OK`**

```json
{
  "status": "success",
  "dataset": "my_dataset",
  "deleted_workspace": "workspace_1",
  "files_deleted": true,
  "deleted_by": "user@example.com"
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `404 Not Found` | Metadata not found, or workspace not found in metadata |
| `500 Internal Server Error` | Failed to delete workspace files |

---

## Map Routes

### POST `/maps/generate`

Synchronously generate Actual and Trend maps for a given index and date range. The client waits for this to complete before fetching map files.

**Auth Required:** `analyst`

**Request Body**

```json
{
  "indexName": "SPI",
  "datasetName": "my_dataset",
  "country": "Thailand",
  "province": "Chiang Mai",
  "startYear": 2010,
  "endYear": 2020,
  "shapefile_name": "thailand_admin",
  "target_col": "NAME_1",
  "supportsTrend": true,
  "spi_threshold": 1.0
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `indexName` | `string` | Yes | Climate index to visualize (e.g. `SPI`) |
| `datasetName` | `string` | Yes | Name of the dataset |
| `country` | `string` | Yes | Country for spatial filtering |
| `province` | `string` | No | Province/region to focus on |
| `startYear` | `int` | Yes | Start year of the map period |
| `endYear` | `int` | Yes | End year of the map period |
| `shapefile_name` | `string` | No | Shapefile used for boundary overlay |
| `target_col` | `string` | No | Column in shapefile for labelling |
| `supportsTrend` | `bool` | Yes | Whether to generate a trend map in addition to the actual map |
| `spi_threshold` | `float` | No | SPI threshold (default: `1.0`) |

**Response `200 OK`**

```json
{
  "status": "success",
  "message": "Maps generated for 2010-2020",
  "details": { }
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `500 Internal Server Error` | Map generation failed |

---

## Shapefile Routes

### POST `/shapefiles/upload`

Upload and validate a shapefile. Accepted formats: `.zip` or `.geojson`.

**Auth Required:** `analyst`

**Request Body:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | `File` | Yes | Shapefile in `.zip` or `.geojson` format |
| `custom_name` | `string` | No | Optional custom name to store the shapefile under |

**Response `200 OK`**

Returns the result from the validation service (structure may vary).

**Error Responses**

| Status | Detail |
|---|---|
| `400 Bad Request` | Invalid file type or validation failure |

---

### GET `/shapefiles`

List all available shapefiles (user-owned and/or global).

**Auth Required:** `analyst`

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `user_only` | `bool` | `false` | If `true`, returns only the current user's shapefiles |

**Response `200 OK`**

```json
{
  "shapefiles": [
    { "name": "thailand_admin", "is_global": false },
    { "name": "world_countries", "is_global": true }
  ]
}
```

---

### GET `/shapefiles/{shapefile_name}/columns`

Get the available text columns and a suggested default column from a specific shapefile.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `shapefile_name` | `string` | Name of the shapefile |

**Response `200 OK`**

Returns the column list and suggested column (structure defined by the service layer).

**Error Responses**

| Status | Detail |
|---|---|
| `404 Not Found` | Shapefile not found or unreadable |

---

### DELETE `/shapefiles/{shapefile_name}`

Delete a user-uploaded shapefile and its directory.

**Auth Required:** `analyst`

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `shapefile_name` | `string` | Name of the shapefile to delete |

**Response `200 OK`**

```json
{
  "message": "Deleted shapefile thailand_admin successfully"
}
```

**Error Responses**

| Status | Detail |
|---|---|
| `404 Not Found` | Shapefile not found |
| `500 Internal Server Error` | Failed to delete directory |

---

## Error Reference

| HTTP Status | Meaning |
|---|---|
| `400 Bad Request` | Invalid input or constraint violation |
| `401 Unauthorized` | Missing or invalid credentials |
| `403 Forbidden` | Authenticated but insufficient role |
| `404 Not Found` | Resource does not exist |
| `500 Internal Server Error` | Unexpected server-side failure |