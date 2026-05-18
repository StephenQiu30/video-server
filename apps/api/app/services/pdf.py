import os
import markdown
from bs4 import BeautifulSoup
from fpdf import FPDF
from app.models import DownloadTask

class PremiumReport(FPDF):
    def __init__(self, font_path=None):
        super().__init__()
        self.font_path = font_path
        if font_path:
            self.add_font("Chinese", "", font_path)
            self.font_name = "Chinese"
            self.has_chinese = True
        else:
            self.font_name = "Arial"
            self.has_chinese = False

    def _safe_text(self, text: str) -> str:
        if self.has_chinese:
            return text
        return text.encode("latin-1", errors="ignore").decode("latin-1")
            
    def header(self):
        # Draw top brand accent line (Brand Indigo)
        self.set_fill_color(79, 70, 229)
        self.rect(0, 0, 210, 6, "F")
        
        # Render clean header on later pages
        if self.page_no() > 1:
            self.set_font(self.font_name, size=8)
            self.set_text_color(156, 163, 175)
            self.set_y(10)
            self.cell(0, 10, self._safe_text("Stephen Video Downloader - 智能分析报告"), align="R", new_x="LMARGIN", new_y="NEXT")
            
            # Subtle header divider line
            self.set_draw_color(243, 244, 246)
            self.set_line_width(0.2)
            self.line(20, 18, 190, 18)
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, size=8)
        self.set_text_color(156, 163, 175)
        self.cell(0, 10, self._safe_text(f"第 {self.page_no()} 页"), align="C")

class PDFService:
    def __init__(self):
        # Fallback paths for Chinese fonts (STHeiti Medium is chosen first for optimal thick-stroke legibility)
        FONT_PATHS = [
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
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
        pdf = PremiumReport(self.font_path)
        pdf.set_margins(20, 20, 20)
        pdf.add_page()
        
        # 1. Branding Header Title
        pdf.set_font(pdf.font_name, size=22)
        pdf.set_text_color(31, 41, 55) # Deep charcoal dark text
        pdf.cell(0, 15, pdf._safe_text("视频智能分析报告"), new_x="LMARGIN", new_y="NEXT", align="L")
        
        # Brand subtitle
        pdf.set_font(pdf.font_name, size=9)
        pdf.set_text_color(99, 102, 241) # Brand Indigo accent color
        pdf.cell(0, 5, pdf._safe_text("STEPHEN VIDEO DOWNLOADER • AI INTELLIGENCE SUITE"), new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.ln(8)
        
        # 2. Exquisite Metadata Summary Card
        pdf.set_fill_color(249, 250, 251) # Sleek grey card fill
        pdf.set_draw_color(229, 231, 235) # Soft grey border
        pdf.set_line_width(0.3)
        
        card_y = pdf.get_y()
        pdf.rect(20, card_y, 170, 36, "DF") # Draw background + border
        
        # Card inner content
        pdf.set_y(card_y + 4)
        
        # Title text (limit length to prevent layout overflows)
        pdf.set_font(pdf.font_name, size=11)
        pdf.set_text_color(31, 41, 55)
        pdf.cell(10) # Left padding
        title_text = task.title or "未命名处理任务"
        if len(title_text) > 42:
            title_text = title_text[:40] + "..."
        pdf.cell(0, 6, pdf._safe_text(f"任务名称: {title_text}"), new_x="LMARGIN", new_y="NEXT")
        
        # Task ID
        pdf.set_font(pdf.font_name, size=10)
        pdf.set_text_color(107, 114, 128)
        pdf.cell(10)
        pdf.cell(0, 6, pdf._safe_text(f"任务标识: {task.id}"), new_x="LMARGIN", new_y="NEXT")
        
        # Video Duration
        pdf.cell(10)
        duration_str = "未知"
        if task.duration_seconds:
            duration_str = f"{task.duration_seconds // 60} 分 {task.duration_seconds % 60} 秒"
        pdf.cell(0, 6, pdf._safe_text(f"视频时长: {duration_str}"), new_x="LMARGIN", new_y="NEXT")
        
        # Complete Date
        pdf.cell(10)
        time_str = task.updated_at.strftime('%Y年%m月%d日 %H:%M:%S') if task.updated_at else "未知"
        pdf.cell(0, 6, pdf._safe_text(f"分析时间: {time_str}"), new_x="LMARGIN", new_y="NEXT")
        
        # Spacer past card boundary
        pdf.set_y(card_y + 36)
        pdf.ln(10)
        
        # 3. Render AI Insights Markdown
        if task.ai_summary:
            html = markdown.markdown(task.ai_summary)
            soup = BeautifulSoup(html, "html.parser")
            
            for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'li']):
                # Standard page-break check to protect flow layouts
                if pdf.get_y() > 250:
                    pdf.add_page()
                    
                if element.name in ['h1', 'h2', 'h3']:
                    pdf.ln(4)
                    current_y = pdf.get_y()
                    
                    # Draw a modern Indigo vertical indicator column
                    pdf.set_fill_color(79, 70, 229)
                    pdf.rect(20, current_y + 1, 3.5, 6, "F")
                    
                    pdf.set_font(pdf.font_name, size=13)
                    pdf.set_text_color(31, 41, 55)
                    pdf.set_x(26) # Indent slightly past block
                    pdf.multi_cell(164, 8, text=pdf._safe_text(element.get_text()))
                    pdf.ln(2)
                    
                    # Smooth baseline divider line below section
                    pdf.set_draw_color(243, 244, 246)
                    pdf.set_line_width(0.2)
                    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
                    pdf.ln(4)
                    
                elif element.name == 'li':
                    pdf.set_font(pdf.font_name, size=11)
                    pdf.set_text_color(55, 65, 81)
                    
                    # Custom designed modern Indigo bullet marker block
                    pdf.set_fill_color(99, 102, 241)
                    bullet_y = pdf.get_y() + 2.5
                    pdf.rect(23, bullet_y, 2, 2, "F")
                    
                    pdf.set_x(28)
                    pdf.multi_cell(162, 7, text=pdf._safe_text(element.get_text()))
                    pdf.ln(2.5)
                    
                else:
                    # Paragraph body text
                    pdf.set_font(pdf.font_name, size=11)
                    pdf.set_text_color(55, 65, 81)
                    pdf.multi_cell(170, 7, text=pdf._safe_text(element.get_text()))
                    pdf.ln(4)
        else:
            pdf.set_font(pdf.font_name, size=12)
            pdf.set_text_color(156, 163, 175)
            pdf.cell(0, 10, pdf._safe_text("暂无智能分析内容"), align="C", new_x="LMARGIN", new_y="NEXT")
            
        return bytes(pdf.output())
