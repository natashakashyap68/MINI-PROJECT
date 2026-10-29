import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf_report(user, sessions, analytics, study_plan) -> io.BytesIO:
    """Generate a high-quality PDF performance report for a user's viva sessions."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'ReportSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )

    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=14,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    bold_body_style = ParagraphStyle(
        'BoldBody',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    story = []

    # Title & Header
    story.append(Paragraph("AI Viva Preparation Bot - Performance Report", title_style))
    story.append(Paragraph(f"Student: <b>{user.username}</b> ({user.email}) &nbsp;|&nbsp; Generated on: {datetime.now().strftime('%B %d, %Y %I:%M %p')}", subtitle_style))
    story.append(Spacer(1, 10))

    # Overall Metrics Summary Table
    total_sessions = len(sessions)
    if total_sessions > 0:
        total_earned = sum(s.score for s in sessions)
        total_possible = sum(s.total for s in sessions)
        overall_percentage = round((total_earned / total_possible) * 100, 1) if total_possible > 0 else 0
        avg_score = round(total_earned / total_sessions, 1)
    else:
        overall_percentage = 0
        avg_score = 0

    metrics_data = [
        [
            Paragraph(f"<b>Total Sessions</b><br/>{total_sessions}", body_style),
            Paragraph(f"<b>Average Score</b><br/>{avg_score} / 10", body_style),
            Paragraph(f"<b>Overall Mastery</b><br/>{overall_percentage}%", body_style),
            Paragraph(f"<b>Weakest Subject</b><br/>{study_plan.get('weak_subject', 'None') if study_plan else 'N/A'}", body_style)
        ]
    ]
    metrics_table = Table(metrics_data, colWidths=[130, 130, 130, 140])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 15))

    # Subject Breakdown Section
    story.append(Paragraph("Subject Performance Breakdown", section_style))
    if analytics:
        subj_table_data = [["Subject / Domain", "Mastery %", "Status"]]
        for subj, pct in analytics.items():
            status = "Strong" if pct >= 80 else ("Moderate" if pct >= 60 else "Needs Improvement")
            subj_table_data.append([subj, f"{pct}%", status])

        subj_table = Table(subj_table_data, colWidths=[240, 140, 150])
        subj_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(subj_table)
    else:
        story.append(Paragraph("No subject data available yet.", body_style))

    story.append(Spacer(1, 15))

    # Weak Topic & Targeted Study Plan Section
    if study_plan:
        story.append(Paragraph("Weak Topic Detector & Targeted Study Plan", section_style))
        plan_box_data = [
            [Paragraph(f"<b>Focus Area:</b> {study_plan.get('weak_subject', 'General')}", bold_body_style)],
            [Paragraph(f"<b>Recommended Sub-Topics to Practice:</b> {', '.join(study_plan.get('recommended_topics', []))}", body_style)],
            [Paragraph(f"<b>Actionable Advice:</b> {study_plan.get('actionable_advice', '')}", body_style)]
        ]
        plan_table = Table(plan_box_data, colWidths=[530])
        plan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF3C7')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F59E0B')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        story.append(plan_table)
        story.append(Spacer(1, 15))

    # Recent Viva History
    story.append(Paragraph("Recent Viva Examination Sessions", section_style))
    if sessions:
        recent = sessions[:8]  # Last 8 sessions for clean formatting
        history_data = [["Date", "Subject", "Topic", "Score", "Feedback Summary"]]
        for s in recent:
            date_str = s.created_at.strftime('%Y-%m-%d') if s.created_at else "N/A"
            feedback_snippet = (s.feedback[:75] + "...") if len(s.feedback) > 75 else s.feedback
            history_data.append([
                date_str,
                s.subject,
                s.topic[:20],
                f"{s.score}/{s.total}",
                feedback_snippet
            ])

        history_table = Table(history_data, colWidths=[70, 110, 100, 50, 200])
        history_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#334155')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ]))
        story.append(history_table)
    else:
        story.append(Paragraph("No viva sessions recorded yet.", body_style))

    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

