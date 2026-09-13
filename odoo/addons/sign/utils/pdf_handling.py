# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging

from io import BytesIO

from odoo.exceptions import ValidationError
from odoo.tools.pdf import DependencyError, errors, NameObject, PdfFileReader, PdfFileWriter, PdfReadError, NumberObject, DictionaryObject
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)


def get_valid_pdf_data(pdf_bytes, strict=True):
    """
    Validate and return a readable PDF file object from the given byte data.

    :param pdf_bytes: Raw byte data of the PDF file to be validated.
    :param strict: Enforce strict parsing of the PDF file.
    :return: A valid and non-encrypted PdfFileReader instance.
    :raises ValidationError: If cannot return non-encrypted PdfFileReader instance.
    """
    # If strict=True is explicitly requested, try strict first then fall back to lenient.
    # By default we favor lenient parsing to cope with malformed yet readable PDFs.
    # pypdf strict=False enables best-effort parsing for PDFs that don't follow the spec exactly.
    # See https://pypdf.readthedocs.io/en/stable/user/robustness.html
    strict_modes = (True, False) if strict else (False,)
    for strict_flag in strict_modes:
        try:
            pdf_reader = PdfFileReader(BytesIO(pdf_bytes), strict_flag)
            if pdf_reader.isEncrypted:
                continue
            if strict_flag is False and strict:
                _logger.warning("Strict PDF parsing failed; falling back to lenient mode.")
            return pdf_reader
        except (DependencyError, UnicodeDecodeError, PdfReadError, errors.PyPdfError):
            _logger.warning("Failed to read PDF data (strict=%s).", strict_flag, exc_info=True)
            continue

    raise ValidationError(_lt(
        "It seems that we're not able to process one of the uploaded pdf. It is either"
        " encrypted, or encoded in a format we do not support."
    ))


# TODO: Wait for the next Debian release to bump the pypdf dependency to >= 5.8.0.
#  Starting from pypdf 5.8.0, true annotation flattening is natively supported. Once upgraded,
#  this workaround can be replaced with real PDF flattening using the  function `update_page_form_field_values`
def flatten_pdf(base64_pdf):
    """
    Makes a PDF non-editable by locking all interactive form fields to Read-Only.

    Note: Due to limitations in the currently supported PyPDF version, true
    flattening (rendering fields as static background text and removing widgets)
    is not performed. Instead, this function locks the data and UI layers of the
    widgets so the user cannot alter the values.

    :param base64_pdf: Base64-encoded string of the original PDF.
    :return: Base64-encoded string of the flattened, non-editable PDF.
    :raises ValidationError: If the PDF cannot be decoded or parsed.
    """
    try:
        pdf_bytes = base64.b64decode(base64_pdf)
        # Use lenient parsing to better handle malformed PDFs while still refusing encrypted ones.
        # strict=False allows pypdf to apply best-effort recovery for non-spec-compliant PDFs.
        pdf_reader = get_valid_pdf_data(pdf_bytes, strict=False)
        output_pdf = PdfFileWriter()
        output_pdf.appendPagesFromReader(pdf_reader)

        for page_number in range(output_pdf.getNumPages()):
            page = output_pdf.getPage(page_number)
            if "/Annots" in page:
                for annot_ref in page["/Annots"]:
                    annot_obj = annot_ref.getObject()

                    # If the annotation is an interactive form Widget
                    if annot_obj.get("/Subtype") == "/Widget":
                        if "/FT" in annot_obj and "/T" in annot_obj:
                            parent_annot_obj = annot_obj
                        else:
                            parent_annot_obj = annot_obj.get("/Parent", DictionaryObject()).getObject()

                        # Bit 1 (Value 1) = Read-Only Data
                        current_ff = parent_annot_obj.get("/Ff", 0)
                        parent_annot_obj[NameObject("/Ff")] = NumberObject(current_ff | 1)

    except errors.PyPdfError as e:
        _logger.warning("Failed to parse PDF during locking interactive widgets: %s", e)
        return base64_pdf

    output_stream = BytesIO()
    output_pdf.write(output_stream)
    return base64.b64encode(output_stream.getvalue())


def _draw_field_value(can, annot_ref):
    """
    Auxiliary function to draw a field value (text, checkbox, radio button).
    """
    _logger.warning("The `_draw_field_value` function is deprecated, unused, and will be removed.")

    annot = annot_ref.getObject()
    rect = annot.get("/Rect")
    if not rect:
        return
    field_value = _get_field_value(annot)
    if field_value:
        x, y = float(rect[0]), float(rect[1])
        can.setFont("Helvetica", 10)
        can.drawString(x + 2, y + 2, field_value)


def _get_field_value(annot):
    """ Return the display value extracted from a PDF annotation.

    :param annot: The annotation dictionary representing the PDF form field.
    :return: The string value to draw, or a checkmark character for active buttons.
    :rtype: str
    """
    _logger.warning("The `_get_field_value` function is deprecated, unused, and will be removed.")

    field_type = annot.get("/FT")
    if field_type == "/Btn":  # checkbox or radio
        appearance_state = annot.get("/AS")
        if appearance_state and appearance_state != NameObject("/Off"):
            # Render a ✓ symbol for checked Check Box or Radio Button
            return chr(0x2713)
        else:  # if btn is not checked don't render anything
            return ""
    return str(annot.get("/V") or "")
