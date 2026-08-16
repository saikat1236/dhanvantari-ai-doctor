import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Adds running headers and page numbers to each page."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(40, 810, "DHANVANTARI: Real-Time AI Doctor & Clinical Triage System")
            self.drawRightString(555, 810, "College Internship Technical Project Report")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(40, 804, 555, 804)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(40, 45, 555, 45)
        self.drawString(40, 32, "Confidential • Academic Internship Project Report • Telemedicine Practice Guidelines 2020 Compliant")
        self.drawRightString(555, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def generate_report(output_filename="dhanvantari_execution_flow.pdf"):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=50,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=19,
        leading=23,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#0D9488'),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12.5,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=5
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0D9488'),
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=5
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold'
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # =========================================================================
    # PAGE 1: COVER & EXECUTIVE ABSTRACT
    # =========================================================================

    meta_data = [
        [
            Paragraph("<b>INTERNSHIP PROJECT TECHNICAL REPORT</b><br/><font color='#0D9488'>Department of Computer Science & Engineering / Artificial Intelligence</font>", body_style),
            Paragraph("<b>Academic Year:</b> 2025 – 2026<br/><b>Domain:</b> Medical AI, Rural Telehealth, Jan Aushadhi & Multimodal Systems", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[280, 235])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 7),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Main Project Title
    story.append(Paragraph("DHANVANTARI: Autonomous Real-Time Multimodal AI Doctor & Rural Telehealth System", title_style))
    story.append(Paragraph("A Statutory Telemedicine Practice Guidelines (2020) & DPDP Act (2023) Compliant Clinical Triage Platform with Interactive Visual Body Map, Jan Aushadhi PMBJP Generic Savings Engine, and 108 Emergency PHC Dispatcher", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0D9488'), spaceBefore=2, spaceAfter=8))

    # Executive Abstract
    story.append(Paragraph("1. Executive Summary & Problem Statement", h1_style))
    abstract_text = (
        "In India, over 65% of the population resides in rural villages where the doctor-to-patient ratio drops below 1:2500, "
        "resulting in severe diagnostic delays, catastrophic out-of-pocket medication expenses, and critical preventable mortality. "
        "<b>Dhanvantari</b> is an autonomous clinical AI doctor platform engineered specifically to bridge this gap. "
        "The system incorporates three frontline grassroots innovations: "
        "<br/>1. <b>Zero-Literacy Interactive Visual Body Map (Point-where-it-hurts):</b> Enables illiterate or dialect-speaking rural patients to indicate pain loci by tapping an anatomical human body map. "
        "<br/>2. <b>Jan Aushadhi Generic Medicine Engine (PMBJP):</b> Automatically computes generic chemical formulations and displays 80-90% subsidized government pharmacy price benchmarks on prescriptions. "
        "<br/>3. <b>1-Tap 108 Ambulance & Nearest PHC/CHC Emergency Dispatcher:</b> Provides GPS proximity calculations and spoken rural first-aid guidelines for acute life-threatening red flags (snakebite, stroke, myocardial infarction)."
    )
    story.append(Paragraph(abstract_text, body_style))
    story.append(Spacer(1, 6))

    # Key Performance Matrix
    story.append(Paragraph("Core System Architecture & Rural Healthcare Matrix", h2_style))
    spec_data = [
        [
            Paragraph("<b>Subsystem / Feature</b>", table_header),
            Paragraph("<b>Technical Implementation</b>", table_header),
            Paragraph("<b>Rural Healthcare Impact & Benchmark</b>", table_header)
        ],
        [
            Paragraph("<b>Visual Body Pain Map</b>", table_cell_bold),
            Paragraph("Interactive SVG Anatomigram + Haptics", table_cell),
            Paragraph("Zero-literacy symptom extraction across 7 anatomical regions with instant Hindi/English quick-chips", table_cell)
        ],
        [
            Paragraph("<b>Jan Aushadhi PMBJP Engine</b>", table_cell_bold),
            Paragraph("NLEM 2022 + Generic Salt Database", table_cell),
            Paragraph("Substitutes expensive branded drugs with generic salts, reducing prescription costs from ~₹350 to ~₹25 (85%+ savings)", table_cell)
        ],
        [
            Paragraph("<b>108 Emergency / PHC Locator</b>", table_cell_bold),
            Paragraph("HTML5 Geolocation + Rural Clinic Grid", table_cell),
            Paragraph("Calculates route to nearest 24/7 PHC/CHC with 1-tap direct dial to 108 Govt Ambulance & anti-snake venom status", table_cell)
        ],
        [
            Paragraph("<b>Doctor Voice Synthesis</b>", table_cell_bold),
            Paragraph("tarun7r/vibevoice-hindi-1.5B Neural TTS", table_cell),
            Paragraph("Empathetic Hindi/Hinglish spoken consultations matching 100% of rich clinical text advice", table_cell)
        ],
        [
            Paragraph("<b>3D Holographic Visualizer</b>", table_cell_bold),
            Paragraph("Three.js WebGL + Web Audio Analyser", table_cell),
            Paragraph("Real-time frequency-reactive neural core providing visual engagement and live subtitles", table_cell)
        ],
        [
            Paragraph("<b>Multimodal AI Radiologist</b>", table_cell_bold),
            Paragraph("SigLIP VisionExtractor + Vision LLM", table_cell),
            Paragraph("Parses Chest X-Rays, CT scans, and pathology lab reports into structured diagnostic impressions", table_cell)
        ]
    ]
    spec_table = Table(spec_data, colWidths=[120, 160, 235])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0D9488')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(spec_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: 7-PHASE END-TO-END EXECUTION FLOW
    # =========================================================================

    story.append(Paragraph("2. End-to-End System Execution Flow & State Machine", h1_style))
    story.append(Paragraph(
        "Dhanvantari executes an asynchronous, event-driven directed acyclic graph (DAG) via LangGraph:", body_style
    ))
    story.append(Spacer(1, 4))

    flow_data = [
        [
            Paragraph("<b>Stage</b>", table_header),
            Paragraph("<b>Execution Node</b>", table_header),
            Paragraph("<b>Technical Protocol & Rural Clinical Safeguards</b>", table_header)
        ],
        [
            Paragraph("<b>Phase 1</b>", table_cell_bold),
            Paragraph("<b>Patient Intake & DPDP 2023 Consent</b>", table_cell_bold),
            Paragraph("Captures patient ID and explicit DPDP Act 2023 consent. Initializes local patient audit log.", table_cell)
        ],
        [
            Paragraph("<b>Phase 2</b>", table_cell_bold),
            Paragraph("<b>Symptom Collector & Visual Body Map</b>", table_cell_bold),
            Paragraph("Ingests voice audio, text, or touch coordinates from the Interactive Body Map (Head, ENT, Chest, Abdomen, Pelvis, Limbs).", table_cell)
        ],
        [
            Paragraph("<b>Phase 3</b>", table_cell_bold),
            Paragraph("<b>Multimodal Vision Scan Extractor</b>", table_cell_bold),
            Paragraph("Analyzes uploaded CXR or lab reports, outputting quantitative metrics (e.g. Cardiothoracic ratio, opacity indices).", table_cell)
        ],
        [
            Paragraph("<b>Phase 4</b>", table_cell_bold),
            Paragraph("<b>Deterministic Red-Flag Gate & 108 Emergency</b>", table_cell_bold),
            Paragraph("Hardcoded regex filter checks for 8 red-flag emergencies (snakebite, crushing chest pain, anaphylaxis). Triggers instant 108 dispatch.", table_cell)
        ],
        [
            Paragraph("<b>Phase 5</b>", table_cell_bold),
            Paragraph("<b>RAG Retrieval & Jan Aushadhi Grounding</b>", table_cell_bold),
            Paragraph("Retrieves ICD-10 codification, NLEM 2022 guidelines, and generic chemical salt prices from the Jan Aushadhi repository.", table_cell)
        ],
        [
            Paragraph("<b>Phase 6</b>", table_cell_bold),
            Paragraph("<b>Gated Hybrid Intelligence (LLaMA + DeepSeek-R1)</b>", table_cell_bold),
            Paragraph("Groq Cloud generates real-time triage guidance. If complex pathology is detected, gates execution to DeepSeek-R1 for Chain-of-Thought reasoning.", table_cell)
        ],
        [
            Paragraph("<b>Phase 7</b>", table_cell_bold),
            Paragraph("<b>VibeVoice 1.5B TTS & RMP PDF Generator</b>", table_cell_bold),
            Paragraph("Synthesizes warm spoken Hindi audio. ReportLab outputs official downloadable PDF prescriptions with Jan Aushadhi generic price benchmarks.", table_cell)
        ]
    ]
    flow_table = Table(flow_data, colWidths=[55, 145, 315])
    flow_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(flow_table)
    story.append(Spacer(1, 8))

    # Callout Box
    arch_box_data = [[
        Paragraph(
            "<b>Statutory Invariant (India Telemedicine 2020):</b> "
            "All generated prescriptions are marked as 'DRAFT PENDING RMP APPROVAL'. "
            "Under no circumstances are Schedule X narcotics permitted. "
            "Generic salt substitutions are enforced under Pradhan Mantri Bhartiya Janaushadhi Pariyojana rules.",
            callout_style
        )
    ]]
    arch_box = Table(arch_box_data, colWidths=[515])
    arch_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDFA')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#0D9488')),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(arch_box)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: TECHNICAL STACK & FRONTLINE MODULE SPECIFICATIONS
    # =========================================================================

    story.append(Paragraph("3. Technical Implementation of Frontline Innovations", h1_style))
    
    # 3.1 Body Map
    story.append(Paragraph("3.1 Interactive Visual Body Map (Point-Where-It-Hurts)", h2_style))
    story.append(Paragraph(
        "Engineered with vector SVG path geometry, the body map decomposes the human physique into discrete tactile touch zones: "
        "<i>Head/Brain (🧠)</i>, <i>ENT & Throat (👁️)</i>, <i>Chest & Lungs (🫁)</i>, <i>Stomach/Abdomen (🫄)</i>, "
        "<i>Pelvis & Urinary</i>, <i>Shoulders & Arms (💪)</i>, and <i>Knees & Legs (🦵)</i>. "
        "Tapping a zone dynamically surfaces high-yield clinical symptom chips in both English and Hindi, "
        "allowing illiterate patients to report complex presentations with zero typing required.",
        body_style
    ))

    # 3.2 Jan Aushadhi
    story.append(Paragraph("3.2 Jan Aushadhi Generic Medicine & Cost Optimization Engine", h2_style))
    story.append(Paragraph(
        "To alleviate financial toxicity in rural care, the formulary engine translates proprietary brand names into "
        "<b>Generic Chemical Salt Formulations IP</b> (e.g. <i>Amoxicillin 500mg + Potassium Clavulanate 125mg IP</i>) and calculates "
        "subsidized price comparisons against standard commercial market prices. The digital prescription and PDF display: "
        "<br/>• <b>Generic Chemical Salt Name & Strength</b> "
        "<br/>• <b>Dosage, Timing & Food Advice</b> (e.g. <i>Take strictly after meals</i>) "
        "<br/>• <b>Jan Aushadhi Kendra Subsidized Cost</b> (e.g. <i>₹10 vs ₹80 - 88% Savings</i>).",
        body_style
    ))

    # 3.3 Emergency 108 & PHC
    story.append(Paragraph("3.3 1-Tap 108 Emergency & Nearest PHC/CHC GPS Locator", h2_style))
    story.append(Paragraph(
        "The emergency dispatcher couples browser geolocation coordinates with a rural healthcare facility index. "
        "When red flags are identified, the system renders: "
        "<br/>• <b>1-Tap Direct Call to 108 Govt Ambulance Service</b> "
        "<br/>• <b>Distance to Nearest 24/7 Primary Health Centre (PHC) & Community Health Centre (CHC)</b> "
        "<br/>• <b>Anti-Snake Venom (ASV) & Emergency Oxygen Availability</b> "
        "<br/>• <b>Spoken First-Aid Protocols</b> (e.g. <i>Do NOT cut snakebite wound; immobilize limb immediately</i>).",
        body_style
    ))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: DEPLOYMENT, VALIDATION & CONCLUSION
    # =========================================================================

    story.append(Paragraph("4. Production Cloud Deployment & Test Validation", h1_style))
    story.append(Paragraph(
        "The Dhanvantari platform is packaged as a Docker container and deployed to permanent cloud infrastructure: "
        "<br/>• <b>Permanent Cloud URL:</b> <code>https://dhanvantari-ai-doctor.onrender.com/</code> "
        "<br/>• <b>RMP Doctor Review Portal:</b> <code>https://dhanvantari-ai-doctor.onrender.com/admin</code> "
        "<br/>• <b>Mobile App Experience:</b> 100% responsive bottom navigation bar, safe-area insets, and touch scaling. "
        "<br/>• <b>Automated Test Suite:</b> 6/6 test suites passed across red-flag interception, RAG grounding, multimodal parsing, and CoT reasoning.",
        body_style
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("5. Project Conclusion & Internship Learning Outcomes", h1_style))
    conclusion_text = (
        "This internship project successfully designed, engineered, and deployed an end-to-end medical AI triage suite "
        "tailored to the socio-economic realities of rural India. By synthesizing <b>LangGraph deterministic orchestration</b>, "
        "<b>multimodal radiological extraction</b>, <b>Three.js WebGL visual interfaces</b>, <b>neural VibeVoice Hindi speech synthesis</b>, "
        "and <b>Jan Aushadhi generic pricing grounding</b>, Dhanvantari demonstrates how cutting-edge AI can deliver free, "
        "equitable, and life-saving healthcare to the most vulnerable communities."
    )
    story.append(Paragraph(conclusion_text, body_style))
    story.append(Spacer(1, 10))

    # Sign-off Table
    sign_data = [
        [
            Paragraph("<b>Student Intern:</b> Saikat Biswas<br/><b>Role:</b> Full-Stack AI Engineering Intern", body_style),
            Paragraph("<b>Project Status:</b> Completed & Live in Production<br/><b>Deployment:</b> Render.com / Docker Cloud", body_style)
        ]
    ]
    sign_table = Table(sign_data, colWidths=[260, 255])
    sign_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(sign_table)

    # Build PDF with running headers and page numbers
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ Successfully compiled project report: {output_filename}")

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "/Users/saikatbiswas/Desktop/projects/Dhanvantari/dhanvantari_execution_flow.pdf"
    generate_report(out_file)
