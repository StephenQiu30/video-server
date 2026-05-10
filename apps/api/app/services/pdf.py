import os
from fpdf import FPDF
from app.models import DownloadTask
import markdown
from bs4 import BeautifulSoup

class PDFService:
    def __init__(self):
        # Path to a Chinese font. On Debian/Ubuntu after apt install fonts-wqy-microhei
        self.font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
        if not os.path.exists(self.font_path):
            # Fallback for local development on Mac if available
            mac_font = "/Library/Fonts/Arial Unicode.ttf"
            if os.path.exists(mac_font):
                self.font_path = mac_font
            else:
                self.font_path = None

    def generate_task_report(self, task: DownloadTask) -> bytes:
        pdf = FPDF()
        pdf.add_page()
        
        if self.font_path:
            pdf.add_font("MicroHei", "", self.font_path)
            pdf.set_font("MicroHei", size=16)
        else:
            pdf.set_font("Arial", "B", 16)
            
        # Title
        pdf.cell(200, 10, txt="视频智能分析报告", ln=True, align="C")
        pdf.ln(10)
        
        # Task Info
        if self.font_path: pdf.set_font("MicroHei", size=12)
        else: pdf.set_font("Arial", size=12)
        
        pdf.cell(200, 10, txt=f"视频名称: {task.title or task.id}", ln=True)
        pdf.cell(200, 10, txt=f"视频链接: {task.source_url}", ln=True)
        pdf.cell(200, 10, txt=f"生成时间: {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.ln(10)
        
        # AI Summary
        pdf.set_font("Arial", "B", 14)
        if self.font_path: pdf.set_font("MicroHei", size=14)
        pdf.cell(200, 10, txt="内容总结", ln=True)
        pdf.ln(5)
        
        if self.font_path: pdf.set_font("MicroHei", size=11)
        else: pdf.set_font("Arial", size=11)
        
        if task.ai_summary:
            # Simple Markdown to Plain Text conversion for PDF
            html = markdown.markdown(task.ai_summary)
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text()
            pdf.multi_cell(0, 8, txt=text)
        else:
            pdf.cell(200, 10, txt="暂无分析内容", ln=True)
            
        return pdf.output()
