import os
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
import logging

logger = logging.getLogger(__name__)

POS_EXPORTS_DIR = "pos_exports"

def export_pos_xml_receipt(member_name: str, membership_id: str, access_granted: bool, confidence: float) -> str:
    """
    Generates an XML payload simulating a Point of Sale (POS) or Check-in event.
    Demonstrates XML generation for legacy retail/enterprise integrations.
    """
    if not os.path.exists(POS_EXPORTS_DIR):
        os.makedirs(POS_EXPORTS_DIR)

    # Create the root element
    transaction = ET.Element("Transaction")
    transaction.set("type", "BiometricCheckIn")
    transaction.set("timestamp", datetime.utcnow().isoformat() + "Z")

    # Add terminal information
    terminal = ET.SubElement(transaction, "TerminalID")
    terminal.text = "POS-GATEWAY-01"

    # Add customer information
    customer = ET.SubElement(transaction, "Customer")
    customer_id = ET.SubElement(customer, "MembershipID")
    customer_id.text = membership_id
    name = ET.SubElement(customer, "Name")
    name.text = member_name

    # Add authentication information
    auth = ET.SubElement(transaction, "Authentication")
    method = ET.SubElement(auth, "Method")
    method.text = "FacialRecognition"
    status = ET.SubElement(auth, "Status")
    status.text = "SUCCESS" if access_granted else "DENIED"
    score = ET.SubElement(auth, "ConfidenceScore")
    score.text = str(round(confidence, 2))

    # Convert to a formatted XML string
    rough_string = ET.tostring(transaction, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    # Save to file
    filename = f"pos_event_{membership_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
    filepath = os.path.join(POS_EXPORTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
        
    logger.info("Generated POS XML Receipt: %s", filepath)
    return filepath
