# เพิ่มใน main.py สำหรับ static files
from fastapi.staticfiles import StaticFiles
import os

# เพิ่มหลัง app = FastAPI()
# สร้างโฟลเดอร์ static ถ้ายังไม่มี
os.makedirs("static/images", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# รูปจะอยู่ที่: https://your-app.onrender.com/static/images/image.jpg