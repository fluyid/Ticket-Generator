import os
import json
import hashlib
import zipfile
from datetime import datetime, timedelta, UTC
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from PIL import Image, ImageDraw
import smtplib
from email.message import EmailMessage


def send_email_with_pass(recipient_email, pass_file_path, recipient_name):
    sender_email = os.getenv("EMAIL_USER")
    app_password = os.getenv("EMAIL_PASS")

    msg = EmailMessage()
    msg["Subject"] = "Your Event Ticket"
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.set_content(f"Hi {recipient_name},\n\nAttached is your digital ticket for the event.\n\nRegards,\nKai Events")

    with open(pass_file_path, "rb") as f:
        pkpass_data = f.read()
        msg.add_attachment(pkpass_data, maintype="application", subtype="vnd.apple.pkpass", filename="ticket.pkpass")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, app_password)
        smtp.send_message(msg)
        print(f"📧 Pass emailed to {recipient_email}")


def generate_signed_pass(name, event, ticket_type, barcode, email, output_path="pass/final_signed_pass.pkpass"):
    # Configuration
    PASS_DIR = "pass_output"
    PASS_DATA = {
        "formatVersion": 1,
        "passTypeIdentifier": "pass.com.example.event",
        "serialNumber": barcode,
        "teamIdentifier": "ABCDE12345",
        "organizationName": "Kai Events",
        "description": "Event Ticket",
        "barcode": {
            "message": barcode,
            "format": "PKBarcodeFormatQR",
            "messageEncoding": "iso-8859-1"
        },
        "eventTicket": {
            "primaryFields": [{"key": "event", "label": "Event", "value": event}],
            "secondaryFields": [
                {"key": "name", "label": "Name", "value": name},
                {"key": "type", "label": "Ticket Type", "value": ticket_type}
            ]
        }
    }

    # Create directories
    os.makedirs(PASS_DIR, exist_ok=True)
    os.makedirs("pass", exist_ok=True)

    # Save pass.json
    with open(f"{PASS_DIR}/pass.json", "w") as f:
        json.dump(PASS_DATA, f)

    # Create dummy images
    def create_image(path, text):
        img = Image.new("RGB", (100, 100), color="blue")
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), text, fill="white")
        img.save(path)

    create_image(f"{PASS_DIR}/icon.png", "Icon")
    create_image(f"{PASS_DIR}/logo.png", "Logo")

    # Create manifest.json
    def sha1_file(filepath):
        with open(filepath, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()

    manifest = {
        "pass.json": sha1_file(f"{PASS_DIR}/pass.json"),
        "icon.png": sha1_file(f"{PASS_DIR}/icon.png"),
        "logo.png": sha1_file(f"{PASS_DIR}/logo.png")
    }
    with open(f"{PASS_DIR}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=4)

    # Generate a self-signed cert and private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"Test Certificate")
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now(UTC)
    ).not_valid_after(
        datetime.now(UTC) + timedelta(days=3650)
    ).sign(private_key, hashes.SHA256(), default_backend())

    # Sign manifest.json
    with open(f"{PASS_DIR}/manifest.json", "rb") as f:
        manifest_data = f.read()

    signature = private_key.sign(
        manifest_data,
        padding.PKCS1v15(),
        hashes.SHA1()
    )
    with open(f"{PASS_DIR}/signature", "wb") as f:
        f.write(signature)

    # Create .pkpass
    with zipfile.ZipFile(output_path, "w") as z:
        z.write(f"{PASS_DIR}/pass.json", "pass.json")
        z.write(f"{PASS_DIR}/icon.png", "icon.png")
        z.write(f"{PASS_DIR}/logo.png", "logo.png")
        z.write(f"{PASS_DIR}/manifest.json", "manifest.json")
        z.write(f"{PASS_DIR}/signature", "signature")

    print(f"✅ Signed .pkpass created for {name} at:", output_path)

    # Send email
    send_email_with_pass(email, output_path, name)


# Example usage
if __name__ == "__main__":
    generate_signed_pass(
        name="Kai",
        event="Comic Con 2025",
        ticket_type="VIP",
        barcode="KAI2025-CCON",
        email="kai@example.com"
    )
