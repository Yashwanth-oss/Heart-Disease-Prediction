"""
Advanced PDF Report Generator for Heart Disease Clinical Assessment
Uses ReportLab to generate comprehensive, multi-section clinical documentation
including local feature attributions, counterfactual recourse, guidelines, and SOAP note.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf_report(
    patient_data, prediction, probability, risk_level, biomarkers, framingham, recommendations,
    attributions=None, recourse=None, citations=None, soap_note=None, conformal=None
):
    """
    Generates a multi-page, comprehensive clinical consultation report in PDF format.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    
    soap_style = ParagraphStyle(
        'SoapText',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1E293B')
    )
    
    disclaimer_style = ParagraphStyle(
        'DisclaimerText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#94A3B8'),
        alignment=1
    )
    
    story = []
    
    # Header
    story.append(Paragraph("CardioAI &bull; Comprehensive Clinical Cardiology Consultation Report", title_style))
    story.append(Paragraph("AI-Assisted Machine Learning Risk Assessment &amp; Clinical Decision Support (CDSS)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#E2E8F0'), spaceAfter=10))
    
    # Metadata Table
    timestamp_str = patient_data.get('timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    patient_id = patient_data.get('id', 'N/A')
    patient_name = patient_data.get('patient_name', 'Patient Screening')
    mrn = patient_data.get('mrn', f"MRN-{patient_id}")
    
    meta_data = [
        [
            Paragraph(f"<b>Patient Name:</b> {patient_name}", body_style),
            Paragraph(f"<b>MRN / ID:</b> #{mrn}", body_style)
        ],
        [
            Paragraph(f"<b>Age / Sex:</b> {patient_data.get('age', 0)} years, {'Male' if int(patient_data.get('sex', 1)) == 1 else 'Female'}", body_style),
            Paragraph(f"<b>Evaluation Date:</b> {timestamp_str}", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))
    
    # Primary Assessment Outcome Banner
    risk_color = colors.HexColor('#DC2626') if prediction == 1 else colors.HexColor('#16A34A')
    risk_bg = colors.HexColor('#FEF2F2') if prediction == 1 else colors.HexColor('#F0FDF4')
    risk_border = colors.HexColor('#FCA5A5') if prediction == 1 else colors.HexColor('#86EFAC')
    
    conf_str = f" &bull; 95% Confidence Interval: {conformal.get('coverage_interval')}" if conformal else ""
    headline = f"<b>Prediction: {risk_level.upper()} ({probability*100:.1f}% Estimated Probability){conf_str}</b>"
    fram_str = f"<b>Framingham 10-Yr CVD Statistical Risk:</b> {framingham.get('estimated_10yr_risk_pct')}% ({framingham.get('category')})"
    
    summary_data = [
        [Paragraph(f"<font color='{risk_color.hexval()}'>{headline}</font>", body_style)],
        [Paragraph(fram_str, body_style)]
    ]
    summary_table = Table(summary_data, colWidths=[540])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), risk_bg),
        ('BOX', (0,0), (-1,-1), 1.5, risk_border),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    
    # 1. Biomarkers Table
    story.append(Paragraph("1. Clinical Biomarker Breakdown", heading_style))
    bio_headers = [Paragraph("<b>Parameter</b>", body_style),
                   Paragraph("<b>Value</b>", body_style),
                   Paragraph("<b>Status</b>", body_style),
                   Paragraph("<b>Interpretation</b>", body_style)]
    bio_rows = [bio_headers]
    for key, item in biomarkers.items():
        name_map = {
            'trestbps': 'Resting Blood Pressure',
            'chol': 'Total Serum Cholesterol',
            'fbs': 'Fasting Blood Sugar',
            'thalach': 'Peak Exercise Heart Rate',
            'oldpeak': 'ST Depression (Oldpeak)',
            'exang': 'Exercise Angina'
        }
        bio_rows.append([
            Paragraph(name_map.get(key, key), body_style),
            Paragraph(str(item.get('value', '')), body_style),
            Paragraph(f"<b>{item.get('status', '')}</b>", body_style),
            Paragraph(str(item.get('detail', '')), body_style)
        ])
    bio_table = Table(bio_rows, colWidths=[140, 80, 110, 210])
    bio_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(bio_table)
    story.append(Spacer(1, 10))
    
    # 2. Local Patient-Specific Feature Attributions
    if attributions:
        story.append(Paragraph("2. Local Explainability: Patient-Specific Risk Drivers", heading_style))
        attr_headers = [Paragraph("<b>Biomarker</b>", body_style),
                        Paragraph("<b>Direction</b>", body_style),
                        Paragraph("<b>Relative Weight</b>", body_style)]
        attr_rows = [attr_headers]
        for a in attributions[:5]:
            dir_text = "<font color='#DC2626'>Increases Risk (+)</font>" if a['direction'] == 'increases_risk' else "<font color='#16A34A'>Decreases Risk (-)</font>"
            attr_rows.append([
                Paragraph(a['feature'], body_style),
                Paragraph(dir_text, body_style),
                Paragraph(f"{a['impact_pct']}", body_style)
            ])
        attr_table = Table(attr_rows, colWidths=[240, 180, 120])
        attr_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(attr_table)
        story.append(Spacer(1, 10))
        
    # 3. Actionable Counterfactual Recourse
    if recourse and recourse.get('needed'):
        story.append(Paragraph(f"3. Actionable Recourse: Projected Risk Reduction (-{recourse.get('risk_reduction_pct')}%)", heading_style))
        rec_headers = [Paragraph("<b>Biomarker</b>", body_style),
                       Paragraph("<b>Current</b>", body_style),
                       Paragraph("<b>Target</b>", body_style),
                       Paragraph("<b>Recommended Clinical Pathway</b>", body_style)]
        rec_rows = [rec_headers]
        for r in recourse.get('recourse_actions', []):
            rec_rows.append([
                Paragraph(r['biomarker'], body_style),
                Paragraph(r['current'], body_style),
                Paragraph(f"<b>{r['target']}</b>", body_style),
                Paragraph(r['clinical_path'], body_style)
            ])
        rec_table = Table(rec_rows, colWidths=[130, 70, 70, 270])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ECFDF5')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#A7F3D0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 10))

    # Page Break for SOAP note and citations
    story.append(PageBreak())
    
    # 4. Evidence-Based Clinical Guidelines
    if citations:
        story.append(Paragraph("4. Evidence-Based Cardiology Clinical Guidelines (ACC / AHA)", heading_style))
        for c in citations:
            c_data = [
                [Paragraph(f"<b>{c['source']} &bull; {c['recommendation_class']} &bull; {c['level_of_evidence']}</b>", body_style)],
                [Paragraph(c['guideline_text'], body_style)]
            ]
            c_table = Table(c_data, colWidths=[540])
            c_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('PADDING', (0,0), (-1,-1), 5),
            ]))
            story.append(c_table)
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))
        
    # 5. Standard Clinical SOAP Note
    if soap_note:
        story.append(Paragraph("5. Physician Electronic Medical Record (EMR) SOAP Consultation Note", heading_style))
        soap_clean = soap_note.replace('\n', '<br/>')
        soap_table = Table([[Paragraph(soap_clean, soap_style)]], colWidths=[540])
        soap_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(soap_table)
        story.append(Spacer(1, 12))
        
    # Disclaimer
    disclaimer = (
        "CONFIDENTIAL MEDICAL REPORT - Generated by CardioAI Clinical Decision Support Engine. "
        "Intended exclusively for physician decision support and screening. Not a definitive medical diagnosis."
    )
    story.append(Paragraph(disclaimer, disclaimer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
