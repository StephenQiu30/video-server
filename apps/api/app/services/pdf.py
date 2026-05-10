import os
import markdown
from bs4 import BeautifulSoup
from fpdf import FPDF
from app.models import DownloadTask

class PDFService:
    def __init__(self):
        # Path to a Chinese font. On Debian/Ubuntu after apt install fonts-wqy-microhei
        self.font_path = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
        if not os.path.exists(self.font_path):
            self.font_path = None

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
        pdf.cell(200, 10, txt="视频分析报告", ln=True, align="C")
        pdf.ln(10)
        
        # Basic Info
        if self.font_path: pdf.set_font("MicroHei", size=11)
        else: pdf.set_font("Arial", size=11)
        
        pdf.cell(0, 8, txt=f"任务标题: {task.title or task.id}", ln=True)
        pdf.cell(0, 8, txt=f"完成时间: {task.updated_at.strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
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
                    pdf.multi_cell(0, 10, txt=element.get_text())
                    pdf.ln(2)
                elif element.name == 'li':
                    if self.font_path: pdf.set_font("MicroHei", size=11)
                    else: pdf.set_font("Arial", size=11)
                    pdf.multi_cell(0, 8, txt=f"• {element.get_text()}")
                else:
                    if self.font_path: pdf.set_font("MicroHei", size=11)
                    else: pdf.set_font("Arial", size=11)
                    pdf.multi_cell(0, 8, txt=element.get_text())
                    pdf.ln(3)
        else:
            pdf.cell(0, 10, txt="暂无智能分析内容", ln=True)
            
        return pdf.output()
