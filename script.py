import os
import logging
import tempfile
import asyncio
from telethon import TelegramClient, events
from telethon.network.connection import ConnectionTcpFull
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Path to the predetermined image (stored locally)
PREDETERMINED_IMAGE_PATH = '/home/sudoham/Desktop/Copy.jpg'

# Telethon API credentials (from environment variables)
API_ID = int(os.getenv('API_ID'))  # Ensure API_ID is an integer
API_HASH = os.getenv('API_HASH')

# Target dimensions for deletion (width, height)
TARGET_DIMENSIONS = [(1280, 1009), (922, 922)]


# Function to check if a page matches specific dimensions
def matches_dimensions(page, target_dimensions):
    width = float(page.mediabox[2])
    height = float(page.mediabox[3])
    return (width, height) in target_dimensions


# Function to convert JPG to PDF while preserving dimensions
def convert_image_to_pdf(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    can.drawImage(image_path, 0, 0, width=width, height=height)
    can.save()
    packet.seek(0)
    return packet


# Initialize Telethon client with a faster data center
client = TelegramClient(
    'session_name',
    API_ID,
    API_HASH,
    connection=ConnectionTcpFull  # Use the class, not an instance
)


# Event handler for incoming messages
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply('Welcome! Send me a PDF file to edit.')


async def process_pdf(file, event):
    try:
        # Create a temporary directory for file storage
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download the PDF file sent by the user
            input_pdf_path = os.path.join(temp_dir, 'input.pdf')
            await client.download_media(file, file=input_pdf_path)  # Use download_media

            # Notify the user that the file is being processed
            await event.reply("Processing your PDF file...")

            # Edit the PDF
            reader = PdfReader(input_pdf_path)
            writer = PdfWriter()

            # Check and skip first or last page if they match target dimensions
            for i, page in enumerate(reader.pages):
                if (i == 0 and matches_dimensions(page, TARGET_DIMENSIONS)) or \
                   (i == len(reader.pages) - 1 and matches_dimensions(page, TARGET_DIMENSIONS)):
                    await event.reply(f"Skipping page {i + 1} (matches target dimensions)...")
                    continue
                writer.add_page(page)

            # Add the predetermined image as the first page
            if os.path.exists(PREDETERMINED_IMAGE_PATH):
                await event.reply("Adding predetermined image as the first page...")
                image_pdf = convert_image_to_pdf(PREDETERMINED_IMAGE_PATH)
                image_reader = PdfReader(BytesIO(image_pdf))
                writer.add_page(image_reader.pages[0])
            else:
                await event.reply("Error: Predetermined image not found.")
                return

            # Add the remaining pages from the original PDF
            for page in reader.pages:
                writer.add_page(page)

            # Save the edited PDF
            output_pdf_path = os.path.join(temp_dir, 'output.pdf')
            with open(output_pdf_path, 'wb') as output_pdf:
                writer.write(output_pdf)

            # Rename the file
            original_filename = file.attributes[0].file_name
            new_filename = original_filename.replace("Manga_BS_ManhuaAR", "MangaMaster33")

            # Notify the user that the file is ready
            await event.reply("Sending the edited PDF back to you...")

            # Send the edited PDF back to the user
            await client.send_file(
                event.sender_id,
                output_pdf_path,
                caption=new_filename,
                thumb=PREDETERMINED_IMAGE_PATH
            )

    except Exception as e:
        # Notify the user if an error occurs
        await event.reply(f"Error processing your file: {e}")


@client.on(events.NewMessage)
async def handle_pdf(event):
    print("New message received!")  # Debugging line

    # Check if the message contains a document and is a PDF
    if not event.document or not event.document.mime_type == 'application/pdf':
        await event.reply("Please send a PDF file.")
        return

    # Notify the user that the file is being downloaded
    await event.reply("Downloading your PDF file...")

    # Process the file
    await process_pdf(event.document, event)


# Start the Telethon client
def main():
    logging.basicConfig(level=logging.ERROR)  # Reduce logging level
    with client:
        print("Client is running. Press Ctrl+C to stop.")  # Debugging line
        client.run_until_disconnected()


if __name__ == '__main__':
    main()
