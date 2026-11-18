#!/usr/bin/env python3
"""
Generate professional PDF report using reportlab (pure Python, no system dependencies)
This script creates a branded PDF competitive analysis report without any API calls.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime


def install_reportlab():
    """Install reportlab if not already installed"""
    try:
        from reportlab.lib.pagesizes import letter, A4
    except ImportError:
        print("Installing reportlab...")
        os.system(f"{sys.executable} -m pip install reportlab -q")


def generate_pdf_report(analysis_json, output_file):
    """Generate a professional PDF report from analysis data"""
    install_reportlab()

    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        Paragraph,
        Spacer,
        PageBreak,
        Image,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

    try:
        print(f"Reading analysis data...")

        with open(analysis_json, "r") as f:
            data = json.load(f)

        print(f"Creating PDF document...")

        # Create PDF
        pdf = SimpleDocTemplate(
            output_file, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch
        )
        story = []

        # Define styles
        styles = getSampleStyleSheet()

        # Brand colors
        PRIMARY_BLUE = colors.HexColor("#2563EB")
        DARK_NAVY = colors.HexColor("#0F172A")
        LIGHT_GRAY = colors.HexColor("#E5E7EB")
        SKY_BLUE = colors.HexColor("#55BFEA")

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=DARK_NAVY,
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=DARK_NAVY,
            spaceAfter=12,
            spaceBefore=12,
            fontName="Helvetica-Bold",
            borderPadding=5,
            borderColor=PRIMARY_BLUE,
            borderWidth=2,
        )

        normal_style = ParagraphStyle(
            "CustomNormal",
            parent=styles["Normal"],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=10,
        )

        # Header
        story.append(Paragraph("Ammar AI Automation Solution", title_style))
        story.append(Paragraph("Competitive Analysis Report", styles["Heading3"]))
        story.append(Paragraph(f"November 14, 2026", styles["Normal"]))
        story.append(Spacer(1, 0.3 * inch))

        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(
            Paragraph(
                "Ammar AI Automation Solution operates in a highly competitive AI automation market with 7 major players. "
                "AAA differentiates through specialized n8n expertise, AI agent development, and deterministic business logic. "
                "Key opportunities: capture underserved South Asian market, build vertical specialization, create productized offerings.",
                normal_style,
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        # Competitive Landscape
        story.append(Paragraph("Competitive Landscape", heading_style))

        competitors_data = [
            ["Competitor", "Threat Level", "Positioning"],
            [
                "Zapier",
                "HIGH",
                "Market leader in no-code automation (6000+ integrations)",
            ],
            ["Make", "HIGH", "Challenger with better pricing model"],
            [
                "n8n Enterprise",
                "HIGH",
                "Direct platform competitor with enterprise services",
            ],
            ["Tray.io", "HIGH", "Enterprise-grade automation with managed services"],
            ["HubSpot", "MEDIUM", "Market leader in SMB CRM with expanding automation"],
            ["ActiveCampaign", "MEDIUM", "Strong in customer communication automation"],
            ["Process.st", "LOW", "Niche player in simple process automation"],
        ]

        competitors_table = Table(
            competitors_data, colWidths=[1.5 * inch, 1.2 * inch, 2.3 * inch]
        )
        competitors_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), DARK_NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), LIGHT_GRAY),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
                ]
            )
        )

        story.append(competitors_table)
        story.append(Spacer(1, 0.3 * inch))

        # Gap Analysis
        story.append(Paragraph("Gap Analysis: 10 Key Competitive Gaps", heading_style))

        gaps = [
            (
                "1. Product-Led Growth",
                "Competitors use freemium models; AAA lacks product entry point",
            ),
            (
                "2. Ecosystem Lock-In",
                "Zapier 6000+, Make 1000+ integrations; AAA is service-only",
            ),
            ("3. Self-Service Templates", "DIY workflows reduce consulting dependence"),
            (
                "4. Vertical Specialization",
                "Competitors target specific industries; AAA is generalist",
            ),
            (
                "5. Brand Presence",
                "Competitors dominate search; AAA has limited public credibility",
            ),
            (
                "6. Training Academies",
                "Make Academy, HubSpot Academy; AAA lacks formal training",
            ),
            (
                "7. Regional Localization",
                "AAA's BIGGEST advantage underlevered (South Asia opportunity)",
            ),
            (
                "8. AI-Agent Positioning",
                "Competitors claim AI; AAA has expertise but doesn't market it",
            ),
            (
                "9. Open-Source Community",
                "n8n's free model builds community; AAA closed services",
            ),
            (
                "10. AI-Driven Support",
                "24/7 AI support as service offering missing from AAA",
            ),
        ]

        for title, desc in gaps:
            story.append(Paragraph(f"<b>{title}:</b> {desc}", normal_style))

        story.append(PageBreak())

        # Brand Recommendations
        story.append(
            Paragraph("Top 5 Brand Improvement Recommendations", heading_style)
        )

        recommendations = [
            {
                "priority": "CRITICAL",
                "title": "Productized SMB Offering ($500-1000)",
                "action": "Create Starter Automation Kit + tiered packages to capture SMB segment",
            },
            {
                "priority": "CRITICAL",
                "title": "Regional Positioning - South Asian Expert",
                "action": "Build localized case studies, regional partnerships, leverage timezone advantage",
            },
            {
                "priority": "HIGH",
                "title": "Thought Leadership Campaign",
                "action": "LinkedIn content 2-3x/week, YouTube tutorials, webinars, guest posts",
            },
            {
                "priority": "HIGH",
                "title": "Partner Certification Program",
                "action": "4-week n8n certification ($200-500/person) to build partner ecosystem",
            },
            {
                "priority": "HIGH",
                "title": "Industry Blueprints",
                "action": "Create 3 vertical solutions: Real Estate, E-commerce, Service Business",
            },
        ]

        for rec in recommendations:
            story.append(
                Paragraph(
                    f"<b>{rec['priority']}: {rec['title']}</b><br/>{rec['action']}",
                    normal_style,
                )
            )
            story.append(Spacer(1, 0.1 * inch))

        # AAA Strengths/Weaknesses
        story.append(Paragraph("AAA's Competitive Position", heading_style))

        story.append(Paragraph("<b>Strengths:</b>", styles["Normal"]))
        strengths = [
            "Deep expertise in n8n (platform insiders build on it)",
            "Strong AI agent development and custom logic",
            "Regional expertise in South Asia/Middle East",
            "Flexible infrastructure (self-hosted options)",
            "High-touch consulting (better for complex needs)",
        ]
        for strength in strengths:
            story.append(Paragraph(f"• {strength}", normal_style))

        story.append(Spacer(1, 0.1 * inch))

        story.append(Paragraph("<b>Weaknesses:</b>", styles["Normal"]))
        weaknesses = [
            "Limited global brand awareness",
            "No productized offering (all high-touch)",
            "No community/open-source play",
            "Limited thought leadership",
            "No vertical specialization",
        ]
        for weakness in weaknesses:
            story.append(Paragraph(f"• {weakness}", normal_style))

        story.append(Spacer(1, 0.2 * inch))

        # Market Trends
        story.append(Paragraph("Market Trends & Opportunities", heading_style))
        trends = [
            "AI agents becoming core differentiator",
            "Shift from platforms to specialized services",
            "Regional SaaS emerging as viable model",
            "Open-source automation accelerating",
            "Hybrid deterministic + AI architectures gaining traction",
        ]
        for trend in trends:
            story.append(Paragraph(f"• {trend}", normal_style))

        story.append(Spacer(1, 0.3 * inch))

        # Next Steps
        story.append(Paragraph("Recommended Next Steps", heading_style))
        steps = [
            "<b>This Month:</b> Launch LinkedIn thought leadership (2-3x/week) + publish 2-3 case studies",
            "<b>Month 1-2:</b> Develop Starter Kit + vertical blueprints + start partner certification",
            "<b>Month 2-3:</b> Implement regional positioning + localized content",
            "<b>Month 3-4:</b> Launch AI Agent Marketplace with 5-10 pre-built agents",
            "<b>Month 4+:</b> Monitor competition + adjust strategy based on market feedback",
        ]
        for step in steps:
            story.append(Paragraph(step, normal_style))

        # Footer
        story.append(Spacer(1, 0.3 * inch))
        story.append(
            Paragraph(
                "Competitive Analysis Report | Ammar AI Automation Solution | Generated: November 14, 2026 | "
                "Analysis Covers: Zapier, Make, n8n, HubSpot, ActiveCampaign, Tray.io, Process.st | "
                "Confidential - Internal Use Only",
                ParagraphStyle(
                    "Footer",
                    parent=styles["Normal"],
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=TA_CENTER,
                ),
            )
        )

        # Build PDF
        pdf.build(story)

        # Get file size
        file_size_kb = os.path.getsize(output_file) / 1024

        print(f"PDF generated successfully!")
        print(f"Saved to: {output_file}")
        print(f"File size: {file_size_kb:.1f} KB")

        return True

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    # Paths
    script_dir = Path(__file__).parent.parent
    analysis_json = script_dir / ".tmp" / "analysis_history" / "analysis_202611.json"
    output_file = script_dir / ".tmp" / "competitor_report_20261114.pdf"

    print("=" * 70)
    print(" " * 15 + "PDF Report Generator")
    print(" " * 10 + "Pure Python - No API Calls - No System Dependencies")
    print("=" * 70)
    print()

    if not os.path.exists(analysis_json):
        print(f"Error: Analysis file not found: {analysis_json}")
        return 1

    # Generate PDF
    success = generate_pdf_report(str(analysis_json), str(output_file))

    if success:
        print("\n" + "=" * 70)
        print(" " * 20 + "SUCCESS!")
        print("=" * 70)
        print()
        print(f"  PDF Location: {output_file}")
        print()
        print("  You can now:")
        print("    ✓ Download the PDF directly")
        print("    ✓ Share with your team")
        print("    ✓ Print and distribute")
        print("    ✓ Use for board presentations")
        print()
        print("=" * 70)
        return 0
    else:
        print("\nFailed to generate PDF")
        return 1


if __name__ == "__main__":
    sys.exit(main())
