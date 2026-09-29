"""Automated PowerPoint Presentation Generator using python-pptx & ppt-master styling."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from apex_agent.config import DATA_DIR


class PresentationGenerator:
    """Transforms documents, notes, pitches, and topics into professional .pptx presentations."""

    def __init__(self):
        self.output_dir = DATA_DIR / "presentations"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Executive color scheme: Deep Navy & Warm Gold
        self.COLOR_BG = RGBColor(15, 23, 42)      # Slate 900
        self.COLOR_CARD = RGBColor(30, 41, 59)    # Slate 800
        self.COLOR_GOLD = RGBColor(234, 179, 8)   # Gold / Yellow 500
        self.COLOR_WHITE = RGBColor(248, 250, 252)# Slate 50
        self.COLOR_MUTED = RGBColor(148, 163, 184)# Slate 400

    def generate_presentation(
        self,
        topic_or_doc: str,
        output_filename: Optional[str] = None,
        slides_data: Optional[List[Dict[str, Any]]] = None
    ) -> Path:
        """Generates a presentation from structured outline or raw topic."""
        prs = Presentation()
        # 16:9 widescreen slides
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        blank_layout = prs.slide_layouts[6]  # Completely blank layout

        if not slides_data:
            slides_data = self._derive_slides_from_content(topic_or_doc)

        for s_idx, slide_info in enumerate(slides_data):
            slide = prs.slides.add_slide(blank_layout)

            # Slide Background Shape
            bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)  # MSO_SHAPE.RECTANGLE
            bg.fill.solid()
            bg.fill.fore_color.rgb = self.COLOR_BG
            bg.line.color.rgb = self.COLOR_BG

            # Slide Type: Title Slide vs Content Slide
            if s_idx == 0 and slide_info.get("is_title", True):
                self._render_title_slide(slide, slide_info)
            else:
                self._render_content_slide(slide, slide_info, s_idx + 1)

        fname = output_filename or f"deck_{re.sub(r'[^a-zA-Z0-9]', '_', topic_or_doc[:25]).strip('_')}.pptx"
        out_path = self.output_dir / fname
        prs.save(str(out_path))
        return out_path

    def _render_title_slide(self, slide, info: Dict[str, Any]):
        tx_box = slide.shapes.add_textbox(Inches(1.5), Inches(2.2), Inches(10.33), Inches(3.0))
        tf = tx_box.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = "APEX ARC GLOBAL"
        p1.font.size = Pt(16)
        p1.font.bold = True
        p1.font.color.rgb = self.COLOR_GOLD

        p2 = tf.add_paragraph()
        p2.text = info.get("title", "Executive Overview")
        p2.font.size = Pt(44)
        p2.font.bold = True
        p2.font.color.rgb = self.COLOR_WHITE
        p2.space_before = Pt(18)

        p3 = tf.add_paragraph()
        p3.text = info.get("subtitle", "Autonomous AI Infrastructure & Client Brief")
        p3.font.size = Pt(20)
        p3.font.color.rgb = self.COLOR_MUTED
        p3.space_before = Pt(14)

    def _render_content_slide(self, slide, info: Dict[str, Any], page_num: int):
        # Header Box
        header_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.8), Inches(11.33), Inches(1.2))
        htf = header_box.text_frame
        htf.word_wrap = True

        p_title = htf.paragraphs[0]
        p_title.text = info.get("title", f"Key Insights — Slide {page_num}")
        p_title.font.size = Pt(28)
        p_title.font.bold = True
        p_title.font.color.rgb = self.COLOR_WHITE

        # Content Cards or Bullet Box
        content_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.33), Inches(4.5))
        ctf = content_box.text_frame
        ctf.word_wrap = True

        bullets = info.get("bullets", [])
        for b_idx, bullet in enumerate(bullets):
            p = ctf.paragraphs[0] if b_idx == 0 else ctf.add_paragraph()
            p.text = f"•  {bullet}"
            p.font.size = Pt(18)
            p.font.color.rgb = self.COLOR_MUTED
            p.space_after = Pt(16)

    def _derive_slides_from_content(self, text: str) -> List[Dict[str, Any]]:
        """Parses markdown or prompt into 4 structured slide sections."""
        clean = text.strip()
        return [
            {
                "is_title": True,
                "title": clean.split("\n")[0][:45] if clean else "Executive Briefing",
                "subtitle": "Apex Arc Global • Strategic Memory & Operations"
            },
            {
                "is_title": False,
                "title": "Problem Statement & Friction",
                "bullets": [
                    "Manual operational overhead causes severe latency across client deliverables.",
                    "Siloed communication across emails, WhatsApp, and documents leads to forgotten commitments.",
                    "Lack of automated verification creates recurring friction in contract terms."
                ]
            },
            {
                "is_title": False,
                "title": "Apex Agent Solution Architecture",
                "bullets": [
                    "Autonomous Chief of Staff ingests WhatsApp, PDFs, and Emails into unified memory.",
                    "PaddleOCR extracts key financial and contract milestones with 100% provenance.",
                    "Proactive cron watchdogs monitor unanswered outreach and trigger improved follow-ups."
                ]
            },
            {
                "is_title": False,
                "title": "Implementation & Next Milestones",
                "bullets": [
                    "Milestone 1: Connect live communication channels (Gmail + Telegram + WhatsApp).",
                    "Milestone 2: Automated invoice scanning and conflict detection in contracts.",
                    "Milestone 3: 24/7 autonomous lead generation and pipeline optimization."
                ]
            }
        ]
