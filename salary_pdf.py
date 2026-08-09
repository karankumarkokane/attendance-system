from io import BytesIO


def create_salary_slip_pdf(slip):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    employee = slip.get("employees") or {}
    month = str(slip["payroll_month"])[:7]
    story = [
        Paragraph("SALARY SLIP", styles["Title"]),
        Spacer(1, 5*mm),
        Paragraph(f"<b>Employee:</b> {employee.get('full_name', '')}", styles["BodyText"]),
        Paragraph(f"<b>Centre:</b> {employee.get('centre', '')}", styles["BodyText"]),
        Paragraph(f"<b>Payroll month:</b> {month}", styles["BodyText"]),
        Spacer(1, 6*mm),
    ]
    rows = [
        ["Working days", slip["working_days"]], ["Present days", slip["present_days"]],
        ["CL taken", slip["cl_days"]], ["SL taken", slip["sl_days"]],
        ["Paid leave days", slip["paid_leave_days"]], ["Half-days", slip["half_days"]],
        ["Unpaid day units", slip["unpaid_days"]],
        ["Gross salary (INR)", f"{float(slip['gross_salary']):,.2f}"],
        ["Deduction (INR)", f"{float(slip['deduction']):,.2f}"],
        ["NET PAYABLE (INR)", f"{float(slip['net_salary']):,.2f}"],
    ]
    table = Table(rows, colWidths=[105*mm, 55*mm])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#dfe5ef")),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#eef4ff")),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"), ("PADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(table)
    details = slip.get("leave_details") or []
    if details:
        story += [Spacer(1, 6*mm), Paragraph("<b>Approved CL/SL dates</b>", styles["BodyText"])]
        for item in details:
            story.append(Paragraph(f"{item['date']} - {item['leave_type']}", styles["BodyText"]))
    story += [Spacer(1, 10*mm), Paragraph("This is a system-generated salary slip.", styles["Italic"])]
    doc.build(story)
    output.seek(0)
    return output
