
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.colors import white
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.units import inch
from datetime import datetime
import io
import pickle


def create_pdf_report(session_data):
    data = session_data["content"]
    user_data = session_data["user_data"]
    pdf_buffer = io.BytesIO()


    #-----------------------------------------Create Document-----------------------------------------
    # Create a SimpleDocTemplate object
    left_margin = right_margin = inch
    page_width, page_height = A4
    text_width = page_width - (left_margin + right_margin)
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,leftMargin=left_margin, rightMargin=right_margin)
    text_flow_width = A4[0] - left_margin - right_margin

    # -----------------------------------------GENERAL STYLES-------------------------------------------
    # Get standard styles
    styles = getSampleStyleSheet()

    style_table_body = styles['BodyText']
    style_table_body.fontSize = 7

    style_table_captions = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8,textColor=white)

    style_table_frame_default = TableStyle([
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            # Gray background for the first row
        ('BACKGROUND', (0, 0), (-1, 0), colors.gray),
        # Gray background for the first column
        ('BACKGROUND', (0, 1), (0, -1), colors.gray),
        # Add other style commands as needed...
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ])

    style_table_frame_company = TableStyle([
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BOX', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, 0), colors.gray),
        # Gray background for the first column
        ('BACKGROUND', (0, 1), (0, -1), colors.gray),
        # Add other style commands as needed...
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ])


    # -----------------------------------------TITLE--------------------------------------------------
    title = "GenAI IdeaWorks"
    subtitle="Session " + str(datetime.now().strftime("%m.%d.%Y"))

    para_title = Paragraph(title, styles['Title'])
    centered_style = ParagraphStyle('centered', parent=styles['Heading2'], alignment=TA_CENTER)
    para_subtitle = Paragraph(subtitle, centered_style)

    # -----------------------------------------COMPANY INFORMATION-------------------------------------
    heading_company_information = Paragraph("<b>Company Information</b>", styles['Heading3'])


    table_company_data=[
        [Paragraph('Company Name:', style_table_captions), Paragraph(data["company_name"], style_table_body)],
        [Paragraph('Company Description:', style_table_captions), Paragraph(data["company_description"], style_table_body)]]

    text_width-=12
    table_company = Table(table_company_data, colWidths=[text_width * 2 / 5, text_width * 3 / 5])
    table_company.setStyle(style_table_frame_company)


    # -----------------------------------------Value Chain INFORMATION-------------------------------------
    heading_value_chain = Paragraph("<b>Value Chain</b>", styles['Heading3'])


    #Generate value chain table data
    N=len(data["value_chain"])
    table_value_chain_data=[["" for _ in range(N + 1)] for _ in range(2)]
    table_value_chain_data[0][0]=Paragraph("Component", style_table_captions)
    table_value_chain_data[1][0]=Paragraph("Description", style_table_captions)

    for i,elem_comp in enumerate(data["value_chain"]):
      table_value_chain_data[0][i + 1]=Paragraph(elem_comp["name"], style_table_captions)
      table_value_chain_data[1][i + 1]=Paragraph(elem_comp["description"], style_table_body)
      use_cases=[]


    table_value_chain = Table(table_value_chain_data)
    table_value_chain.setStyle(style_table_frame_default)


    if len(data["use_cases"])>0:
        # -----------------------------------------Use Cases INFORMATION-------------------------------------
        heading_use_cases = Paragraph("<b>Use Cases</b>", styles['Heading3'])

        #add user information
        use_case=data["use_cases"]
        for case in use_case:
            dict_key= case["component"]+"_"+case["name"]
            case["comment"]=user_data[dict_key]["comment"]
            case["prio"] = user_data[dict_key]["prio"]

        df_use_cases=pd.DataFrame(data["use_cases"])
        table_data_use_cases_no_para = [df_use_cases.columns.tolist()] + df_use_cases.values.tolist()
        table_data_use_cases = []
        for i, row in enumerate(table_data_use_cases_no_para):
            new_row = []
            for j, cell in enumerate(row):
                # Apply bold_white_style for the first row and the first column
                if i == 0 or j == 0:
                    new_row.append(Paragraph(str(cell), style_table_captions))
                else:
                    new_row.append(Paragraph(str(cell), style_table_body))
            table_data_use_cases.append(new_row)



        table_use_cases = Table(table_data_use_cases)
        table_use_cases.setStyle(style_table_frame_default)


    # -----------------------------------------# Assemble the document-------------------------------------

    story = []
    story.append(para_title)
    story.append(para_subtitle)
    story.append(Spacer(1, 0.2*inch))
    story.append(heading_company_information)
    story.append(table_company)
    story.append(Spacer(1, 0.2*inch))
    story.append(heading_value_chain)
    story.append(table_value_chain)
    story.append(Spacer(1, 0.2*inch))
    if len(data["use_cases"]) > 0:
        story.append(heading_use_cases)
        story.append(table_use_cases)



    # -----------------------------------------Build The Document-------------------------------------
    doc.build(story)
    return pdf_buffer



# #-----------------------------------------Variables -----------------------------------------
# # Define the PDF file name
# file_name_a4 = "report.pdf"
#
# #-----------------------------------------LOAD DATA-----------------------------------------

#file_name="session.pkl"
#with open(file_name, 'rb') as file:
#     session=pickle.load(file)



#pdf_bytes= create_pdf_report(session)
#with open("report.pdf", "wb") as file:
#    # Seek to the start of the io.BytesIO object if it's not already at the beginning
#    file.write(pdf_bytes.getbuffer())

