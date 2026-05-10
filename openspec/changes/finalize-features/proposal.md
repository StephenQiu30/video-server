# Proposal: Finalize Video Processing & AI Intelligence Suite

## Goal
Complete the implementation and integration of core features: video downloading, AI-generated reports (summary & mindmap), SSE real-time streaming, and PDF export.

## User Requirements
1. **Video Download**: Users can download processed videos directly from the workbench.
2. **AI Reports**: Every task should generate a professional summary and a Mermaid mindmap.
3. **SSE Streaming**: Use Server-Sent Events for real-time task status updates instead of polling.
4. **PDF Export**: Export the AI intelligence report (summary) to a professional PDF file.
5. **Standard Compliance**: Follow `AGENTS.md` rules, update documentation, and submit to GitHub in Chinese.

## Proposed Changes
### Backend (API & Worker)
- **PDF Service**: Add `app/services/pdf.py` using `fpdf2` to generate reports.
- **PDF Endpoint**: Add a download route in `app/routers/tasks.py`.
- **Dependencies**: Add `fpdf2` and `markdown` to `requirements.txt`.
- **Worker**: Ensure AI processing is robust and covers all succeeded tasks.

### Frontend (Web)
- **SSE Integration**: Replace `react-query` polling with `EventSource` for the task list.
- **Download Actions**: Add a download button to each successful task item.
- **PDF Export Button**: Implement the PDF download logic in the AI Insight modal.
- **UI Polish**: Use Shadcn UI for all new buttons and interactions.

### Documentation
- Update `docs/prd/` and `docs/design/` to reflect these features.
- Update `README.md`.
