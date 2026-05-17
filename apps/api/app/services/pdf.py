import os
import markdown
from bs4 import BeautifulSoup
from fpdf import FPDF
from app.models import DownloadTask

class PDFService:
    def __init__(self):
        # Fallback paths for Chinese fonts (supporting both macOS local dev and Debian/Ubuntu production docker)
        FONT_PATHS = [
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/fonts-wqy-microhei.ttc",
            "/usr/share/fonts/truetype/wqy-microhei/wqy-microhei.ttc",
        ]
        self.font_path = None
        for path in FONT_PATHS:
            if os.path.exists(path):
                self.font_path = path
                break

    def generate_task_report(self, task: DownloadTask) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        
        # Use simple standard fonts or CJK font if available
        if self.font_path:
            pdf.add_font("MicroHei", "", self.font_path)
            pdf.set_font("MicroHei", size=16)
        else:
            pdf.set_font("Arial", "B", 16)
            
        # Minimal Header
        pdf.cell(0, 10, text="视频分析报告", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)
        
        # Basic Info
        if self.font_path: pdf.set_font("MicroHei", size=11)
        else: pdf.set_font("Arial", size=11)
        
        pdf.cell(0, 8, text=f"任务标题: {task.title or task.id}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, text=f"完成时间: {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)
        
        # Markdown Content
        if task.ai_summary:
            # Parse Markdown to text while maintaining some structure
            html = markdown.markdown(task.ai_summary)
            soup = BeautifulSoup(html, "html.parser")
            
            # Simple iteration over elements to handle basic structure
            for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                if element.name in ['h1', 'h2', 'h3']:
                    if self.font_path: pdf.set_font("MicroHei", style="", size=13)
                    else: pdf.set_font("Arial", "B", 13)
                    pdf.multi_cell(pdf.epw, 10, text=element.get_text())
                    pdf.ln(2)
                elif element.name == 'li':
                    if self.font_path: pdf.set_font("MicroHei", size=11)
                    else: pdf.set_font("Arial", size=11)
                    pdf.multi_cell(pdf.epw, 8, text=f"• {element.get_text()}")
                else:
                    if self.font_path: pdf.set_font("MicroHei", size=11)
                    else: pdf.set_font("Arial", size=11)
                    pdf.multi_cell(pdf.epw, 8, text=element.get_text())
                    pdf.ln(3)
        else:
            pdf.cell(0, 10, text="暂无智能分析内容", new_x="LMARGIN", new_y="NEXT")
            
        return bytes(pdf.output())
