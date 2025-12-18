# Elvanto Export

A web application for exporting filtered people data from Elvanto to XLSX format. Users can filter by group leadership, volunteer positions, demographics, and categories.

## Features

- 🔐 **Secure**: API keys are entered per-session and never stored
- 🎯 **Flexible Filtering**: Filter by groups, volunteer positions, demographics, and categories
- 📊 **Excel Export**: Export filtered results to XLSX format
- 🚀 **Multi-tenant**: Each user enters their own API key
- 💻 **Modern UI**: Clean, responsive interface with loading states

## Architecture

- **Backend**: FastAPI (Python) - Handles Elvanto API integration and data filtering
- **Frontend**: React - User interface for filtering and exporting
- **Database**: SQLite (optional, for future features)

## Prerequisites

- Docker and Docker Compose
- Elvanto API key (users enter this in the app)

## Quick Start (Development)

1. Clone the repository:
```bash
git clone https://github.com/isaaclee0/elvantoexport.git
cd elvantoexport
```

2. Start the services:
```bash
docker-compose up -d
```

3. Access the application:
- Frontend: http://localhost:4000
- Backend API: http://localhost:9000

## Production Deployment

### Building and Pushing to Docker Hub

To build multi-architecture images (AMD64 and ARM64) and push to Docker Hub:

1. **Create repositories on Docker Hub:**
   - Go to https://hub.docker.com/repositories/staugustine1
   - Create two repositories:
     - `elvanto-export-backend` (set to Private if desired)
     - `elvanto-export-frontend` (set to Private if desired)

2. **Login to Docker Hub:**
```bash
docker login
# Enter your Docker Hub username and password/token
```

3. **Install Docker Buildx** (if not already installed):
```bash
# Buildx usually comes with Docker Desktop
# For Linux, you may need to install it separately
docker buildx version
```

4. **Build and push images:**
```bash
# Make the script executable (if needed)
chmod +x build-and-push.sh

# Build and push (default API URL: http://localhost:9000)
./build-and-push.sh

# Or with custom API URL for your deployment
REACT_APP_API_URL=http://your-server-ip:9000 ./build-and-push.sh
```

This will build and push:
- `staugustine1/elvanto-export-backend:latest` (and git commit hash tag)
- `staugustine1/elvanto-export-frontend:latest` (and git commit hash tag)

**Note**: 
- The images are built for both `linux/amd64` and `linux/arm64` architectures, making them compatible with ARM-based servers (like Raspberry Pi, Apple Silicon, or ARM cloud instances).
- If your repositories are private, you'll need to authenticate in Portainer or wherever you're deploying.
- The frontend image is built with the API URL baked in at build time. If you need to change it, rebuild the image with a different `REACT_APP_API_URL`.

### Using Portainer with Docker Hub Images

1. In Portainer, go to **Stacks** → **Add Stack**
2. Select **Web editor** or **Upload**
3. Use the `docker-compose.hub.yml` file (or copy its contents)
4. Configure environment variables:
   - `REACT_APP_API_URL`: **REQUIRED** - The public URL where your backend will be accessible (e.g., `http://your-server-ip:9000` or `https://your-domain.com/api` if using reverse proxy)
   - `BACKEND_PORT`: Backend port (default: `9000`)
   - `FRONTEND_PORT`: Frontend port (default: `80`)
   - `ELVANTO_API_URL`: Elvanto API URL (default: `https://api.elvanto.com/v1`)
5. **Important**: Make sure you're logged into Docker Hub in Portainer if the repository is private
6. Deploy the stack

### Using Portainer with GitHub (Build from Source)

1. In Portainer, go to **Stacks** → **Add Stack**
2. Select **Git Repository**
3. Enter repository URL: `https://github.com/isaaclee0/elvantoexport.git`
4. Set the **Compose path** to: `docker-compose.prod.yml`
5. Configure environment variables:
   - `REACT_APP_API_URL`: **REQUIRED** - The public URL where your backend will be accessible (e.g., `http://your-server-ip:9000` or `https://your-domain.com/api` if using reverse proxy)
   - `BACKEND_PORT`: Backend port (default: `9000`)
   - `FRONTEND_PORT`: Frontend port (default: `80`)
   - `ELVANTO_API_URL`: Elvanto API URL (default: `https://api.elvanto.com/v1`)
6. Deploy the stack

**Important**: The `REACT_APP_API_URL` must be the **public URL** that browsers can access, not an internal Docker service name. This is because the frontend runs in the user's browser, not inside Docker.

### Manual Production Deployment

1. Clone the repository on your server
2. Create a `.env` file (optional, for default API URL):
```bash
ELVANTO_API_URL=https://api.elvanto.com/v1
REACT_APP_API_URL=http://your-backend-url:9000
```

3. Start the production stack:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

4. Access the application:
- Frontend: http://your-server-ip (port 80)
- Backend API: http://your-server-ip:9000

### Reverse Proxy Setup (Recommended)

For production, it's recommended to use a reverse proxy (like Nginx or Traefik) in front of the application:

**Nginx Example:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Variables

### Backend
- `ELVANTO_API_URL`: Elvanto API base URL (default: `https://api.elvanto.com/v1`)
- `DATABASE_URL`: Database connection string (default: `sqlite:///./data/elvanto.db`)
- `ENV`: Environment mode (`development` or `production`)

### Frontend
- `REACT_APP_API_URL`: Backend API URL (default: `http://localhost:9000`)

**Note**: The Elvanto API key is entered by users in the application interface and is not stored.

## API Endpoints

- `GET /health` - Health check
- `POST /api/categories` - Get people categories
- `POST /api/group-categories` - Get group categories
- `POST /api/groups-and-services` - Get groups and volunteer positions
- `POST /api/filter` - Filter people based on selections
- `POST /api/export/xlsx` - Export filtered people to XLSX

All API endpoints require an `api_key` in the request body (except `/health`).

## Development

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── elvanto_client.py  # Elvanto API client
│   │   └── main.py       # FastAPI application
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main React component
│   │   └── App.css       # Styles
│   ├── Dockerfile
│   ├── Dockerfile.prod   # Production Dockerfile
│   └── package.json
├── docker-compose.yml    # Development compose
├── docker-compose.prod.yml  # Production compose
└── README.md
```

## Security Notes

- API keys are never stored on the server
- API keys are only kept in browser memory during the session
- No persistent storage of user data
- All API calls are made server-side to protect API keys

## License

MIT

## Support

For issues or questions, please open an issue on GitHub.

