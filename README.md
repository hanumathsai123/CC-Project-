# GeoSight — Cloud-Based Satellite Image Analysis

A demo-ready full-stack **Geo Science: Satellite Image Application** for a Cloud Applications course.

## What works
- Two-project launcher: Biology gene-expression analysis and Geo Science satellite analysis
- Real-time processing of labeled gene-expression CSV/TSV uploads with an educational baseline comparison
- Animated Earth with an orbiting satellite and space UI
- Separate authenticated admin portal at `/admin`
- React + Vite frontend
- FastAPI + Python backend
- Image upload and deterministic land-cover demo analysis
- Original vs classified result viewer
- Live Sentinel-2 product metadata search through Copernicus Data Space STAC
- Optional AWS S3 upload for source/result images
- AWS-ready architecture explanation page
- Dockerfiles + docker-compose
- Sample satellite-style image: `data/demo_satellite.png`

## Admin portal
Open `http://localhost:5173/admin` to review Biology analysis runs, validation accuracy, and per-sample actual versus predicted labels and scores, as well as Geo Science image uploads, original/classified previews, land-cover metrics, and Sentinel-2 search/product history. The portal uses `ADMIN_EMAIL` and `ADMIN_PASSWORD` from `backend/.env`; change the demo credentials before deployment.

## Start locally — easiest method
The backend expects a Python 3.9 environment because the pinned NumPy version has macOS arm64 wheels for this runtime.

### Terminal 1
```bash
./run-backend.sh
```

### Terminal 2
```bash
./run-frontend.sh
```

Open: `http://localhost:5173`

If the browser asks for a port, use the Vite URL shown in Terminal 2.

The first screen lets you choose Biology or Geo Science. Geo Science opens without login. Its analyzed image uploads, land-cover metrics, and Sentinel-2 catalog search results/filters appear in the Geo Science section of `/admin`. Biology accepts UTF-8 CSV/TSV files with samples as rows, numeric gene columns, and a two-group `diagnosis` column; a demo file is available from the Biology page. Analysis runs immediately on the backend. When an S3 bucket is configured, the uploaded dataset and JSON report are also uploaded to S3. The admin review database stores summary statistics and sample-level predictions, not raw gene-expression values. Accuracy is a dataset validation score, not clinical diagnostic performance.

The first screen lets you choose Biology or Geo Science. Biology accepts UTF-8 CSV/TSV files with samples as rows, numeric gene columns, and a two-group `diagnosis` column; a demo file is available from the Biology page. The analysis runs immediately on the backend. When an S3 bucket is configured, the uploaded dataset and JSON report are also stored in S3. This educational baseline is not a validated clinical diagnostic test.

## Demo flow for your guide
1. Open GeoSight and show the animated Earth + satellite.
2. Open Biology to analyze gene-expression data, or visit `/admin` and sign in with the backend admin credentials to review predictions.
3. Click **Analysis**.
4. Upload `data/demo_satellite.png`.
5. Click **Run Analysis**.
6. Explain: React → FastAPI → image processing → result → optional S3 storage.
7. Open **Datasets** → **Search Live Data** to query Sentinel-2 catalog metadata.
8. Open **Architecture** and explain Frontend → Backend → Sentinel-2/STAC → AWS.

## AWS setup
Copy the example file:
```bash
cp backend/.env.example backend/.env
```

Then set:
```env
AWS_REGION=ap-south-1
AWS_S3_BUCKET=your-unique-bucket-name
AWS_ACCESS_KEY_ID=YOUR_KEY
AWS_SECRET_ACCESS_KEY=YOUR_SECRET
```

The backend uploads the original image and classified result to S3 when valid AWS credentials and a bucket are configured. **Never put AWS credentials in the React frontend.** For deployment, prefer an IAM role on EC2/ECS instead of long-lived access keys.

## Real satellite data
The application queries:
`https://stac.dataspace.copernicus.eu/v1`

It searches the `sentinel-2-l2a` collection using bounding box, date range, and cloud-cover parameters. The response is satellite-product metadata; it should not be described as live video. Earth-observation imagery is captured when the satellite passes over the area.

## Technology stack
- Frontend: React, Vite, Lucide icons, CSS animations
- Backend: FastAPI, Pillow, NumPy, Boto3
- Earth Observation: Copernicus Data Space STAC / Sentinel-2
- Cloud: AWS S3; EC2-ready deployment

## Production upgrade path
Replace the demo classifier with a trained multispectral land-cover segmentation model, add PostgreSQL/RDS for analysis history, use Cognito/real identity management, and serve signed S3 URLs rather than public objects.

## AWS EC2 deployment

1. Launch a Linux EC2 instance and allow SSH (22) from your IP and HTTP (80) from the internet.
2. Install Docker and Docker Compose.
3. Copy this project to the instance.
4. Create `backend/.env` from `backend/.env.example`.
5. Set `AWS_REGION` and `AWS_S3_BUCKET`. Prefer an EC2 IAM role for S3 access instead of putting long-lived AWS keys in `.env`.
6. Run `./deploy-aws.sh`.
7. Open `http://YOUR_EC2_PUBLIC_IP/`.

The frontend uses `/api` and Nginx proxies API requests to the FastAPI container, so the browser does not call `localhost`.

For HTTPS/custom domain, put a domain in front of the EC2 instance and add TLS with a reverse proxy or load balancer.

## Batch 10 Team Workspace

Project team registration numbers currently configured in the notification system:
- 231FA04204
- 231FA04239
- 231FA04243

Replace the placeholder team member names in `backend/main.py` when the final names are available.

## Real-time architecture

React refreshes API health and project notifications every 30 seconds. Live satellite discovery calls the Copernicus Data Space STAC catalog for Sentinel-2 Level-2A products. The system treats “real-time” as current/near-real-time Earth-observation catalog access and time-stamped satellite observations, not continuous live video.
# CC-Project
# CC-Project-
