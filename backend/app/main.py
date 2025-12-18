from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import os
import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from .api import people

app = FastAPI(title="Elvanto Export API")

# Configure CORS to allow frontend to connect
# In production, allow all origins since frontend URL is unknown
# In development, restrict to localhost
env = os.getenv("ENV", "development")
if env == "production":
    # In production, allow all origins (credentials must be False when using *)
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = ["http://localhost:4000", "http://localhost:3000"]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(people.router)

@app.get("/")
async def root():
    return {"message": "Elvanto Export API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/health")
async def api_health():
    return {"status": "healthy"}

@app.post("/api/export/xlsx")
async def export_to_xlsx(request: Request):
    """Export filtered people data to XLSX"""
    try:
        data = await request.json()
        people_list = data.get("people", [])
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Elvanto Export"
        
        # Headers
        headers = ["First Name", "Preferred Name", "Last Name", "Email", "Groups", "Service Positions"]
        ws.append(headers)
        
        # Style headers
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")
        
        # Add data
        for person in people_list:
            firstname = person.get("firstname", "")
            preferred_name = person.get("preferred_name", "")
            lastname = person.get("lastname", "")
            email = person.get("email", "")
            
            # Format groups
            groups = person.get("groups", [])
            groups_str = "; ".join([f"{g.get('name', 'Unknown')} ({g.get('role', 'Member')})" for g in groups])
            
            # Format service positions
            service_positions = person.get("service_positions", [])
            positions_str = "; ".join([sp.get('name', 'Unknown') for sp in service_positions])
            
            ws.append([firstname, preferred_name, lastname, email, groups_str, positions_str])
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=elvanto_export.xlsx"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

