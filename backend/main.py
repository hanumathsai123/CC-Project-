from contextlib import contextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pathlib import Path
from PIL import Image
import csv, io, os, uuid, json, math, secrets, sqlite3, time
import numpy as np
import requests

try:
    import boto3
except Exception:
    boto3 = None

BASE = Path(__file__).resolve().parent.parent
UPLOADS = BASE / "data" / "uploads"
RESULTS = BASE / "data" / "results"
UPLOADS.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)
BIOLOGY_DB = BASE / "data" / "biology_analysis.sqlite3"

@contextmanager
def connect_biology_db():
    connection = sqlite3.connect(BIOLOGY_DB)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()

with connect_biology_db() as connection:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS biology_runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            sample_count INTEGER NOT NULL,
            gene_count INTEGER NOT NULL,
            correct_count INTEGER NOT NULL,
            accuracy_percent REAL NOT NULL,
            groups_json TEXT NOT NULL,
            genes_json TEXT NOT NULL,
            predictions_json TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS satellite_runs (
            run_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            filename TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            source_url TEXT NOT NULL,
            result_url TEXT NOT NULL,
            storage TEXT NOT NULL
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS satellite_catalog_searches (
            search_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            bbox_json TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            cloud_cover REAL NOT NULL,
            source TEXT NOT NULL,
            items_json TEXT NOT NULL,
            warning TEXT
        )
    """)

class Settings(BaseSettings):
    app_name: str = "GeoSight"
    admin_email: str = "admin@geosight.local"
    admin_password: str = "Admin@123"
    cdse_stac_url: str = "https://stac.dataspace.copernicus.eu/v1"
    aws_region: str = "ap-south-1"
    aws_s3_bucket: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_session_token: str = ""
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
admin_sessions = {}
app = FastAPI(title="GeoSight API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/files", StaticFiles(directory=str(BASE / "data")), name="files")

class LoginRequest(BaseModel):
    email: str
    password: str

class SearchRequest(BaseModel):
    bbox: list[float] = [80.30, 15.95, 80.75, 16.35]
    start_date: str = "2026-01-01"
    end_date: str = "2026-12-31"
    cloud_cover: float = 20

@app.get("/api/health")
def health():
    return {"status":"online","service":"GeoSight API","aws_configured": bool(settings.aws_s3_bucket)}

@app.post("/api/admin/login")
def admin_login(req: LoginRequest):
    valid_email = secrets.compare_digest(req.email.strip().lower(), settings.admin_email.lower())
    valid_password = secrets.compare_digest(req.password, settings.admin_password)
    if not valid_email or not valid_password:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    token = secrets.token_urlsafe(32)
    admin_sessions[token] = time.time() + 8 * 60 * 60
    return {"token": token, "user": {"email": settings.admin_email, "role": "Administrator"}}

def require_admin(authorization: str = Header(default="")):
    scheme, separator, token = authorization.partition(" ")
    expiry = admin_sessions.get(token)
    if scheme.lower() != "bearer" or not separator or expiry is None or expiry <= time.time():
        admin_sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Admin sign-in required")
    return token

@app.get("/api/stats")
def stats():
    return {"images_analyzed": 1284, "live_sources": 3, "cloud_status":"Connected", "processing_ms": 842, "storage":"S3 Ready" if settings.aws_s3_bucket else "Local Demo Storage"}

def analyze_image(im: Image.Image):
    rgb = np.asarray(im.convert("RGB").resize((512,512))).astype(np.float32)
    r,g,b = rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
    green = (g > r*1.08) & (g > b*1.05) & (g > 55)
    water = (b > r*1.15) & (b > g*1.02) & (b > 65)
    urban = (np.std(rgb, axis=2) < 24) & (r > 70) & (g > 70) & (b > 70)
    other = ~(green | water | urban)
    counts = np.array([green.sum(), water.sum(), urban.sum(), other.sum()], dtype=float)
    pct = counts / counts.sum() * 100
    out = rgb.copy()
    out[green] = [40,210,100]
    out[water] = [40,130,245]
    out[urban] = [240,80,70]
    out[other] = [235,205,80]
    result = Image.fromarray(out.astype(np.uint8)).resize(im.size)
    return result, {"vegetation":round(float(pct[0]),1),"water":round(float(pct[1]),1),"built_up":round(float(pct[2]),1),"other":round(float(pct[3]),1)}

def analyze_gene_expression(raw: bytes, delimiter: str):
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "Gene-expression files must use UTF-8 encoding") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(400, "The file must include a header row")

    headers = [header.strip() if header else "" for header in reader.fieldnames]
    if any(not header for header in headers) or len(set(headers)) != len(headers):
        raise HTTPException(400, "Column names must be non-empty and unique")
    reader.fieldnames = headers
    label_columns = {"diagnosis", "label", "class", "target", "cancer_status", "status"}
    label_column = next((h for h in headers if h.strip().lower() in label_columns), None)
    if label_column is None:
        raise HTTPException(400, "Add a diagnosis column containing the two known sample groups")

    id_columns = {"sample", "sample_id", "id", "patient_id"}
    sample_column = next((h for h in headers if h.lower() in id_columns), None)
    gene_columns = [h for h in headers if h != label_column and h.lower() not in id_columns]
    if len(gene_columns) < 2:
        raise HTTPException(400, "Include at least two numeric gene-expression columns")

    try:
        rows = list(reader)
    except csv.Error as exc:
        raise HTTPException(400, "The uploaded file is not valid CSV/TSV data") from exc
    if not 4 <= len(rows) <= 5000:
        raise HTTPException(400, "The dataset must contain between 4 and 5,000 samples")
    if len(gene_columns) > 2000:
        raise HTTPException(400, "The dataset can contain at most 2,000 gene columns")

    labels = []
    sample_ids = []
    values = []
    for row_number, row in enumerate(rows, start=2):
        label = (row.get(label_column) or "").strip()
        if not label:
            raise HTTPException(400, f"Missing diagnosis label on row {row_number}")
        labels.append(label)
        sample_id = (row.get(sample_column) or "").strip() if sample_column else ""
        sample_ids.append(sample_id[:128] or f"Sample {row_number - 1}")
        expression = []
        for gene in gene_columns:
            value = (row.get(gene) or "").strip()
            try:
                number = float(value)
            except ValueError as exc:
                raise HTTPException(400, f"Expected a numeric value for {gene} on row {row_number}") from exc
            if not math.isfinite(number):
                raise HTTPException(400, f"Expression values must be finite (row {row_number}, {gene})")
            expression.append(number)
        values.append(expression)

    groups = sorted(set(labels))
    if len(groups) != 2:
        raise HTTPException(400, "The diagnosis column must contain exactly two sample groups")
    group_indices = {group: np.flatnonzero(np.asarray(labels) == group) for group in groups}
    if any(len(indices) < 2 for indices in group_indices.values()):
        raise HTTPException(400, "Include at least two samples in each diagnosis group")

    expression = np.asarray(values, dtype=np.float64)
    group_sums = {
        group: expression[indices].sum(axis=0)
        for group, indices in group_indices.items()
    }
    total_sum = expression.sum(axis=0)
    total_square_sum = np.square(expression).sum(axis=0)
    sample_predictions = []
    for row_index, actual in enumerate(labels):
        training_count = len(rows) - 1
        training_mean = (total_sum - expression[row_index]) / training_count
        training_variance = (
            (total_square_sum - np.square(expression[row_index])) / training_count
            - np.square(training_mean)
        )
        training_scale = np.sqrt(np.maximum(training_variance, 0))
        training_scale[training_scale == 0] = 1
        distances = {
            group: float(np.linalg.norm((expression[row_index] - (
                (group_sums[group] - expression[row_index]) / (len(group_indices[group]) - 1)
                if group == actual
                else group_sums[group] / len(group_indices[group])
            )) / training_scale))
            for group in groups
        }
        predicted = min(distances, key=distances.get)
        distance_values = np.asarray([distances[group] for group in groups], dtype=np.float64)
        scores = np.exp(-(distance_values - distance_values.min()))
        predicted_score = float(scores[groups.index(predicted)] / scores.sum() * 100)
        sample_predictions.append({
            "sample_id": sample_ids[row_index],
            "actual": actual,
            "predicted": predicted,
            "score_percent": round(predicted_score, 2),
            "correct": actual == predicted,
        })

    correct = sum(prediction["correct"] for prediction in sample_predictions)
    full_scale = expression.std(axis=0)
    full_scale[full_scale == 0] = 1
    differential = []
    for index, gene in enumerate(gene_columns):
        group_means = {
            group: float(expression[group_indices[group], index].mean())
            for group in groups
        }
        effect = (group_means[groups[1]] - group_means[groups[0]]) / full_scale[index]
        differential.append({
            "gene": gene,
            "standardized_difference": round(effect, 3),
            "mean_by_group": {group: round(mean, 4) for group, mean in group_means.items()},
        })
    differential.sort(key=lambda item: abs(item["standardized_difference"]), reverse=True)

    return {
        "sample_count": len(rows),
        "gene_count": len(gene_columns),
        "groups": [
            {"name": group, "sample_count": int(len(group_indices[group]))}
            for group in groups
        ],
        "correct_count": correct,
        "incorrect_count": len(rows) - correct,
        "leave_one_out_accuracy_percent": round(correct / len(rows) * 100, 2),
        "top_differential_genes": differential[:10],
        "sample_predictions": sample_predictions,
    }

@app.post("/api/biology/analyze")
async def biology_analyze(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name.replace("\\", "_")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".csv", ".tsv"}:
        raise HTTPException(400, "Upload a .csv or .tsv gene-expression file")
    raw = await file.read(10 * 1024 * 1024 + 1)
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(413, "Gene-expression files must be 10 MB or smaller")

    report = analyze_gene_expression(raw, "\t" if suffix == ".tsv" else ",")
    job = uuid.uuid4().hex[:10]
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    predictions = report["sample_predictions"]
    with connect_biology_db() as connection:
        connection.execute(
            """
            INSERT INTO biology_runs (
                run_id, created_at, sample_count, gene_count, correct_count,
                accuracy_percent, groups_json, genes_json, predictions_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job,
                created_at,
                report["sample_count"],
                report["gene_count"],
                report["correct_count"],
                report["leave_one_out_accuracy_percent"],
                json.dumps(report["groups"]),
                json.dumps(report["top_differential_genes"]),
                json.dumps(predictions),
            ),
        )

    storage = "Local"
    if boto3 and settings.aws_s3_bucket:
        try:
            kwargs = {"region_name": settings.aws_region}
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                kwargs.update({
                    "aws_access_key_id": settings.aws_access_key_id,
                    "aws_secret_access_key": settings.aws_secret_access_key,
                    "aws_session_token": settings.aws_session_token or None,
                })
            s3 = boto3.client("s3", **kwargs)
            s3.put_object(
                Bucket=settings.aws_s3_bucket,
                Key=f"biology/uploads/{job}_{filename}",
                Body=raw,
            )
            s3.put_object(
                Bucket=settings.aws_s3_bucket,
                Key=f"biology/reports/{job}.json",
                Body=json.dumps(report, indent=2).encode("utf-8"),
                ContentType="application/json",
            )
            storage = "AWS S3"
        except Exception as exc:
            print("Biology S3 upload failed:", exc)

    return {
        "job_id": job,
        "report": report,
        "storage": storage,
        "created_at": created_at,
    }

@app.get("/api/admin/biology/runs")
def admin_biology_runs(_admin: str = Header(default="", alias="Authorization")):
    require_admin(_admin)
    with connect_biology_db() as connection:
        totals = connection.execute(
            """
            SELECT COUNT(*) AS run_count, COALESCE(SUM(sample_count), 0) AS sample_count,
                   COALESCE(SUM(correct_count), 0) AS correct_count
            FROM biology_runs
            """
        ).fetchone()
        runs = connection.execute(
            """
            SELECT run_id, created_at, sample_count, gene_count, correct_count,
                   accuracy_percent, groups_json, genes_json
            FROM biology_runs ORDER BY created_at DESC, rowid DESC LIMIT 100
            """
        ).fetchall()

    sample_count = int(totals["sample_count"])
    correct_count = int(totals["correct_count"])
    return {
        "summary": {
            "run_count": int(totals["run_count"]),
            "sample_count": sample_count,
            "correct_count": correct_count,
            "incorrect_count": sample_count - correct_count,
            "overall_accuracy_percent": round(correct_count / sample_count * 100, 2) if sample_count else 0,
        },
        "runs": [
            {
                "run_id": row["run_id"],
                "created_at": row["created_at"],
                "sample_count": row["sample_count"],
                "gene_count": row["gene_count"],
                "correct_count": row["correct_count"],
                "accuracy_percent": row["accuracy_percent"],
                "groups": json.loads(row["groups_json"]),
                "top_genes": json.loads(row["genes_json"]),
            }
            for row in runs
        ],
    }

@app.get("/api/admin/biology/runs/{run_id}")
def admin_biology_run(run_id: str, _admin: str = Header(default="", alias="Authorization")):
    require_admin(_admin)
    with connect_biology_db() as connection:
        run = connection.execute(
            "SELECT * FROM biology_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    if run is None:
        raise HTTPException(404, "Analysis run not found")
    return {
        "run_id": run["run_id"],
        "created_at": run["created_at"],
        "sample_count": run["sample_count"],
        "gene_count": run["gene_count"],
        "correct_count": run["correct_count"],
        "accuracy_percent": run["accuracy_percent"],
        "groups": json.loads(run["groups_json"]),
        "top_genes": json.loads(run["genes_json"]),
        "predictions": json.loads(run["predictions_json"]),
    }

@app.get("/api/admin/satellite/runs")
def admin_satellite_runs(_admin: str = Header(default="", alias="Authorization")):
    require_admin(_admin)
    with connect_biology_db() as connection:
        runs = connection.execute(
            """
            SELECT run_id, created_at, filename, metrics_json, storage
            FROM satellite_runs ORDER BY created_at DESC, rowid DESC LIMIT 100
            """
        ).fetchall()
        searches = connection.execute(
            """
            SELECT search_id, created_at, bbox_json, start_date, end_date,
                   cloud_cover, source, items_json, warning
            FROM satellite_catalog_searches ORDER BY created_at DESC, rowid DESC LIMIT 100
            """
        ).fetchall()
    return {
        "summary": {
            "run_count": len(runs),
            "images_analyzed": len(runs),
            "storage": "AWS S3" if any(row["storage"] == "AWS S3" for row in runs) else "Local",
            "catalog_search_count": len(searches),
        },
        "runs": [
            {
                "run_id": row["run_id"],
                "created_at": row["created_at"],
                "filename": row["filename"],
                "metrics": json.loads(row["metrics_json"]),
                "storage": row["storage"],
            }
            for row in runs
        ],
        "searches": [
            {
                "search_id": row["search_id"],
                "created_at": row["created_at"],
                "bbox": json.loads(row["bbox_json"]),
                "start_date": row["start_date"],
                "end_date": row["end_date"],
                "cloud_cover": row["cloud_cover"],
                "source": row["source"],
                "items": json.loads(row["items_json"]),
                "warning": row["warning"],
            }
            for row in searches
        ],
    }

@app.get("/api/admin/satellite/runs/{run_id}")
def admin_satellite_run(run_id: str, _admin: str = Header(default="", alias="Authorization")):
    require_admin(_admin)
    with connect_biology_db() as connection:
        run = connection.execute(
            "SELECT * FROM satellite_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
    if run is None:
        raise HTTPException(404, "Satellite analysis run not found")
    return {
        "run_id": run["run_id"],
        "created_at": run["created_at"],
        "filename": run["filename"],
        "metrics": json.loads(run["metrics_json"]),
        "storage": run["storage"],
        "source_url": run["source_url"],
        "result_url": run["result_url"],
    }

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Please upload an image file")
    raw = await file.read()
    try: im = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception: raise HTTPException(400, "Invalid image")
    job = uuid.uuid4().hex[:10]
    filename = Path(file.filename or "satellite-image").name.replace("\\", "_")
    source = UPLOADS / f"{job}_{filename}"
    result = RESULTS / f"{job}_classified.png"
    source.write_bytes(raw)
    classified, metrics = analyze_image(im)
    classified.save(result)
    storage = "Local"
    if boto3 and settings.aws_s3_bucket:
        try:
            # On EC2, boto3 automatically uses the attached IAM role.
            # Local development may optionally use explicit credentials from .env.
            kwargs = {"region_name": settings.aws_region}
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                kwargs.update({"aws_access_key_id": settings.aws_access_key_id, "aws_secret_access_key": settings.aws_secret_access_key, "aws_session_token": settings.aws_session_token or None})
            s3 = boto3.client("s3", **kwargs)
            s3.upload_file(str(source), settings.aws_s3_bucket, f"uploads/{source.name}")
            s3.upload_file(str(result), settings.aws_s3_bucket, f"results/{result.name}")
            storage = "AWS S3"
        except Exception as exc:
            print("Satellite S3 upload failed:", exc)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    source_url = f"/files/uploads/{source.name}"
    result_url = f"/files/results/{result.name}"
    with connect_biology_db() as connection:
        connection.execute(
            """
            INSERT INTO satellite_runs (
                run_id, created_at, filename, metrics_json,
                source_url, result_url, storage
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (job, created_at, filename, json.dumps(metrics), source_url, result_url, storage),
        )
    return {
        "job_id": job,
        "source_url": source_url,
        "result_url": result_url,
        "metrics": metrics,
        "storage": storage,
        "created_at": created_at,
        "message": "Analysis completed",
    }

@app.post("/api/satellite/search")
def satellite_search(req: SearchRequest):
    # STAC supports spatial/temporal/cloud-cover search for Sentinel-2 L2A.
    payload = {"collections":["sentinel-2-l2a"],"bbox":req.bbox,"datetime":f"{req.start_date}T00:00:00Z/{req.end_date}T23:59:59Z","query":{"eo:cloud_cover":{"lte":req.cloud_cover}},"limit":8,"sortby":[{"field":"datetime","direction":"desc"}]}
    search_id = uuid.uuid4().hex[:10]
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    warning = None
    try:
        r = requests.post(settings.cdse_stac_url + "/search", json=payload, timeout=15)
        r.raise_for_status(); data=r.json()
        features=[]
        for f in data.get("features",[]):
            p=f.get("properties",{})
            assets=f.get("assets",{})
            thumb=None
            for key in ["thumbnail","rendered_preview","visual"]:
                if key in assets: thumb=assets[key].get("href"); break
            features.append({"id":f.get("id"),"date":p.get("datetime"),"cloud_cover":p.get("eo:cloud_cover"),"thumbnail":thumb})
        source = "Copernicus Data Space STAC"
    except requests.RequestException as exc:
        source = "Demo fallback"
        warning = str(exc)[:500]
        features = [
            {"id":"S2-DEMO-2026-001","date":"2026-09-20T05:30:00Z","cloud_cover":8.2},
            {"id":"S2-DEMO-2026-002","date":"2026-09-15T05:28:00Z","cloud_cover":12.6},
            {"id":"S2-DEMO-2026-003","date":"2026-09-09T05:25:00Z","cloud_cover":4.1},
        ]
    response = {
        "search_id": search_id,
        "created_at": created_at,
        "source": source,
        "count": len(features),
        "items": features,
        "warning": warning,
    }
    with connect_biology_db() as connection:
        connection.execute(
            """
            INSERT INTO satellite_catalog_searches (
                search_id, created_at, bbox_json, start_date, end_date,
                cloud_cover, source, items_json, warning
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                search_id,
                created_at,
                json.dumps(req.bbox),
                req.start_date,
                req.end_date,
                req.cloud_cover,
                source,
                json.dumps(features),
                warning,
            ),
        )
    return response


TEAM = [
    {"reg_no": "231FA04204", "name": "Team Member 01"},
    {"reg_no": "231FA04239", "name": "Team Member 02"},
    {"reg_no": "231FA04243", "name": "Team Member 03"},
]

@app.get("/api/notifications")
def notifications():
    return {
        "batch": "10",
        "team": TEAM,
        "items": [
            {"type": "team", "title": "Batch 10 • GeoSight Team", "message": "231FA04204 • 231FA04239 • 231FA04243", "priority": "info"},
            {"type": "live", "title": "Live Earth Observation", "message": "Sentinel-2 catalog connection is ready for current product discovery.", "priority": "live"},
            {"type": "cloud", "title": "AWS Cloud Pipeline", "message": "S3 storage + EC2 backend integration is enabled when AWS is configured.", "priority": "cloud"},
        ]
    }

@app.get("/api/architecture")
def architecture():
    return {"layers":[{"name":"Frontend","tech":"React + Vite","role":"Dashboard, upload, animation, maps/results"},{"name":"Backend","tech":"FastAPI + Python","role":"Authentication, image analysis, STAC search, AWS integration"},{"name":"Earth Observation","tech":"Copernicus Sentinel-2 / STAC","role":"Live satellite product discovery"},{"name":"Cloud","tech":"AWS S3 + optional EC2","role":"Object storage and deployment"}]}
