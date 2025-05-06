import os
import csv
from pyzbar.pyzbar import decode
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import qrcode
from fpdf import FPDF
from fpdf.enums import Align, XPos, YPos
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()
print(f"Email: {os.getenv('EMAIL_USER')}")
print(f"Password: {os.getenv('EMAIL_PASS')}")


def verify_qr_code(qr_image_path):
    try:
        img = Image.open(qr_image_path).convert("RGB")
        result = decode(img)
        if result:
            data = result[0].data.decode()
            print(f"QR Code contains: {data}")
            return data
        else:
            print("Could not decode QR code")
            return None
    except Exception as e:
        print(f"Error reading QR code: {e}")
        return None


def send_email_with_pass(recipient_email, recipient_name, png_path, pdf_path):
    sender_email = os.environ.get("EMAIL_USER")
    app_password = os.environ.get("EMAIL_PASS")

    if not sender_email or not app_password:
        print("Email or Password is not set in environment variables")
        return

    msg = EmailMessage()
    msg["Subject"] = "Your Event Ticket"
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.set_content(f"Hi {recipient_name}, \n\nAttached are your digital ticket files (PDF and PNG)."
                    f"\n\n Best Regards, \nLondon Chinese Association")

    with open(pdf_path, "rb") as file:
        msg.add_attachment(file.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))

    with open(png_path, "rb") as file:
        msg.add_attachment(file.read(), maintype="image", subtype="png", filename=os.path.basename(png_path))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print(f"Email has been sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {recipient_email}: {e}")
        return False


def write_log_entry(name, email, phone, barcode, status):
    log_path = "ticket_log.csv"
    file_exists = os.path.isfile(log_path)
    with open(log_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Name", "Email", "Phone", "Barcode", "Status", "Timestamp"])
        writer.writerow([name, email, phone, barcode, status, datetime.now().isoformat()])


def generate_android_pass(name, event, ticket_type, barcode, email, phone, output_dir="android_passes"):
    os.makedirs(output_dir, exist_ok=True)

    # Basic layout config
    width, height = 600, 400
    background_color = "white"
    text_color = "black"
    filename_base = f"{name.replace(' ', '_')}_{barcode}"

    # Create QR code
    qr = qrcode.make(barcode)
    qr_path = os.path.join(output_dir, f"{filename_base}_qr.png")
    qr.save(qr_path)

    # Verifying QR content
    verify_qr_code(qr_path)

    # Create PNG Pass
    image = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(image)

    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 20)
    except:
        font = None

    draw.text((20, 20), f"Event: {event}", fill=text_color, font=font)
    draw.text((20, 60), f"Name: {name}", fill=text_color, font=font)
    draw.text((20, 100), f"Ticket Type: {ticket_type}", fill=text_color, font=font)
    draw.text((20, 140), f"Code: {barcode}", fill=text_color, font=font)

    # Paste QR code
    qr_img = Image.open(qr_path).resize((150, 150))
    image.paste(qr_img, (width - 180, 40))

    # Save PNG
    png_path = os.path.join(output_dir, f"{filename_base}.png")
    image.save(png_path)

    # Create PDF using fpdf2
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=16)
    pdf.cell(0, 10, text=f"Event: {event}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
    pdf.cell(0, 10, text=f"Name: {name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
    pdf.cell(0, 10, text=f"Ticket Type: {ticket_type}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
    pdf.cell(0, 10, text=f"Barcode: {barcode}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align=Align.L)
    pdf.image(qr_path, x=80, y=70, w=50, h=50)

    pdf_path = os.path.join(output_dir, f"{filename_base}.pdf")
    pdf.output(pdf_path)

    print("✅ PNG and PDF pass generated:")
    print(f"- PNG: {png_path}")
    print(f"- PDF: {pdf_path}")

    # Send by email
    email_status = send_email_with_pass(email, name, png_path, pdf_path)
    write_log_entry(name, email, phone, barcode, "Sent" if email_status else "Failed")


# Example usage
if __name__ == "__main__":
    generate_android_pass(
        name="Kai",
        event="Chinese New Year 2026",
        ticket_type="VIP",
        barcode="CHINESE_NEW_YEAR_1312_2026",
        email="kailashnathashok@gmail.com"
    )
