"""KannadaLens AI: Smart Kannada Document Digitizer (Day 7 version)."""

import hashlib
import html
import io
import os

import streamlit as st
from PIL import Image, UnidentifiedImageError

from core.crop import crop_box, crop_image, dim_outside
from core.ocr import OCRError, prepare_image, run_ocr_detailed
from core.pdf import PDFError, count_pages, render_page
from core.preprocess import THRESHOLD_CHOICES, preprocess
from core.summary import key_sentences, preview, stats, top_words
from core.textutils import find_matches, fix_anusvara_zero, highlight_html

PRESET_OFF = "Off (original image)"
PRESET_ENHANCE = "Enhance (resize + denoise + contrast)"
MAX_PAGES_PER_RUN = 10

st.set_page_config(page_title="KannadaLens AI", page_icon="🔍", layout="wide")

st.markdown(
    """
    <style>
    textarea { font-size: 1.1rem !important; line-height: 1.7 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False, max_entries=20)
def cached_render_page(file_id, index, _file_bytes):
    """Render a PDF page (the file bytes are not hashed; file_id identifies them)."""
    return render_page(_file_bytes, index)


@st.cache_data(show_spinner=False, max_entries=20)
def cached_enhance(file_id, index, threshold, crop, _image):
    """Apply the Enhance preset to one (cropped) page (cached per crop setting)."""
    return preprocess(_image, resize=True, denoise=True, contrast=True, threshold=threshold)


def html_list(items):
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


MARK_STYLE = "background:#ffd54f; color:#000; border-radius:3px; padding:0 2px;"


def confidence_html(tokens, limit):
    """Original OCR text with every word below `limit` highlighted."""
    parts = []
    for separator, word, confidence in tokens:
        parts.append(separator.replace("\n", "<br>"))
        escaped = html.escape(word)
        if confidence is not None and confidence < limit:
            parts.append(f'<mark style="{MARK_STYLE}">{escaped}</mark>')
        else:
            parts.append(escaped)
    return "".join(parts)


st.title("🔍 KannadaLens AI")
st.caption(
    "Smart Kannada Document Digitizer. Free and open source. Documents are processed "
    "in memory and not stored by this app. Run it on your own computer to keep "
    "documents fully private."
)

with st.sidebar:
    st.header("About")
    st.write(
        "Upload a printed Kannada document (image or scanned PDF) and extract "
        "editable text with Tesseract OCR."
    )
    st.warning(
        "OCR can make mistakes, especially on low-resolution, faded or unusual-font "
        "documents. Always review and correct the text. Handwritten Kannada is "
        "not supported."
    )

    st.header("Image enhancement")
    preset = st.radio(
        "Before reading the text",
        [PRESET_OFF, PRESET_ENHANCE],
        index=1,
        help=(
            "Enhance enlarges small text and improves contrast. On our small test "
            "set it was as good as or better than Off on every image. Try both on "
            "your own document."
        ),
    )
    threshold = "None"
    if preset == PRESET_ENHANCE:
        with st.expander("Advanced"):
            threshold = st.selectbox(
                "Black-and-white thresholding",
                THRESHOLD_CHOICES,
                index=0,
                help="Made results worse in our tests. Leave on None unless you are experimenting.",
            )

    st.header("Text clean-up")
    auto_fix = st.checkbox(
        "Fix digit ೦ inside words (anusvara ಂ)",
        value=True,
        help=(
            "Tesseract often reads the anusvara ಂ as the digit zero ೦. This changes a ೦ "
            "to ಂ only when it follows a Kannada letter or vowel sign and is not part of "
            "a number. Applied when you click Extract."
        ),
    )

uploaded = st.file_uploader(
    "Upload a Kannada document (JPG, PNG or scanned PDF)",
    type=["jpg", "jpeg", "png", "pdf"],
)

if uploaded is None:
    st.info("Upload a JPG, JPEG, PNG or PDF file to begin.")
    st.stop()

file_bytes = uploaded.getvalue()
file_id = hashlib.sha1(file_bytes).hexdigest()
is_pdf = uploaded.name.lower().endswith(".pdf")

# Reset results when a different file is uploaded.
if st.session_state.get("file_id") != file_id:
    st.session_state["file_id"] = file_id
    for key in ("ocr_ready", "editor", "ocr_used", "ocr_fixes", "ocr_pages", "ocr_note", "ocr_words"):
        st.session_state.pop(key, None)

# ---- Load the document: a list of pages, each loaded on demand ----
single_image = None
if is_pdf:
    try:
        page_count = count_pages(file_bytes)
    except PDFError as err:
        st.error(str(err))
        st.stop()
else:
    try:
        raw_image = Image.open(io.BytesIO(file_bytes))
        raw_image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        st.error("This file could not be read as an image. Please upload a valid JPG or PNG.")
        st.stop()
    single_image = prepare_image(raw_image)
    page_count = 1
    if single_image.size[0] < 200 or single_image.size[1] < 50:
        st.warning("This image is very small. OCR will likely be poor. Try a larger image.")


def load_page(index):
    """Return page `index` (0-based) as an RGB image."""
    if is_pdf:
        return cached_render_page(file_id, index, file_bytes)
    return single_image


crop = (0, 0, 0, 0)  # percent cut from left, right, top, bottom (set in the Crop box)


def cropped_page(index):
    """Page `index` with the crop applied (the page itself when nothing is cut)."""
    return crop_image(load_page(index), *crop)


def get_ocr_input(index):
    """The image that OCR will read for this page (cropped, then enhanced or not)."""
    page = cropped_page(index)
    if preset == PRESET_ENHANCE:
        return cached_enhance(file_id, index, threshold, crop, page)
    return page


if preset == PRESET_ENHANCE:
    used_label = "enhanced (resize, denoise, contrast"
    if threshold != "None":
        used_label += f", {threshold} threshold"
    used_label += ")"
else:
    used_label = "original image"

left, right = st.columns(2)

# ---- Left column: page choice and image preview ----
with left:
    st.subheader("Document")

    first_page, last_page = 1, 1
    if is_pdf:
        st.caption(f"PDF with {page_count} page(s).")
        if page_count > 1:
            first_page, last_page = st.slider(
                "Pages to read",
                min_value=1,
                max_value=page_count,
                value=(1, min(page_count, MAX_PAGES_PER_RUN)),
                key=f"pages_{file_id}",
            )
            if last_page - first_page + 1 > MAX_PAGES_PER_RUN:
                last_page = first_page + MAX_PAGES_PER_RUN - 1
                st.warning(
                    f"At most {MAX_PAGES_PER_RUN} pages are read at a time to keep it fast. "
                    f"Reading pages {first_page} to {last_page}."
                )
        preview_choice = st.selectbox(
            "Preview page", list(range(first_page, last_page + 1)), key=f"preview_{file_id}"
        )
        preview_index = preview_choice - 1
    else:
        preview_index = 0

    # ---- Optional crop: cut margins, side columns or pictures before OCR ----
    with st.expander("✂ Crop (optional)"):
        st.caption(
            "Cut away parts you do not want read, such as a picture, a side column or a "
            "boxed heading. Each slider removes that percent from one side. The same cut "
            "is used on every page you read. Cropping to one block of text at a time can "
            "also fix a wrong reading order."
        )
        col_l, col_r = st.columns(2)
        cut_left = col_l.slider("Cut from left (%)", 0, 60, 0, key=f"crop_l_{file_id}")
        cut_right = col_r.slider("Cut from right (%)", 0, 60, 0, key=f"crop_r_{file_id}")
        cut_top = col_l.slider("Cut from top (%)", 0, 60, 0, key=f"crop_t_{file_id}")
        cut_bottom = col_r.slider("Cut from bottom (%)", 0, 60, 0, key=f"crop_b_{file_id}")
        crop = (cut_left, cut_right, cut_top, cut_bottom)
        try:
            crop_box((100, 100), *crop)
        except ValueError as err:
            st.warning(f"{err} The crop is ignored for now.")
            crop = (0, 0, 0, 0)

    try:
        full_preview = load_page(preview_index)
        crop_rect = crop_box(full_preview.size, *crop)
        cropped_preview = cropped_page(preview_index)
        enhanced_preview = (
            cached_enhance(file_id, preview_index, threshold, crop, cropped_preview)
            if preset == PRESET_ENHANCE
            else None
        )
    except PDFError as err:
        st.error(str(err))
        st.stop()
    except Exception as err:  # noqa: BLE001
        st.error(f"Could not prepare this page: {err}")
        st.stop()

    # One tab per view. The first tab shows the whole page; when a crop is set, the
    # parts that will be cut away are darkened.
    views = [("Original", dim_outside(full_preview, crop_rect), full_preview.size)]
    if crop_rect is not None:
        views.append(("Cropped", cropped_preview, cropped_preview.size))
    if enhanced_preview is not None:
        views.append(("Enhanced", enhanced_preview, enhanced_preview.size))

    if len(views) == 1:
        st.image(views[0][1])
        st.caption(f"{views[0][2][0]} x {views[0][2][1]} pixels")
    else:
        for tab, (name, picture, size) in zip(st.tabs([v[0] for v in views]), views):
            with tab:
                st.image(picture)
                caption = f"{size[0]} x {size[1]} pixels"
                if name == "Original" and crop_rect is not None:
                    caption += ". Dark areas will be cut away."
                st.caption(caption)

if any(crop):
    used_label += ", after crop"

# ---- Right column: OCR, editing, export, search, summary ----
with right:
    st.subheader("Extracted text")
    pages_total = last_page - first_page + 1
    st.caption(
        f"OCR will use: {used_label}"
        + (f" on {pages_total} page(s)" if is_pdf else "")
        + ". Extracting again replaces any edits you made."
    )

    if st.button("Extract Kannada text", type="primary"):
        tokens = []  # (separator, word, confidence) for every word, used by the review panel
        pages_read = 0
        total_fixes = 0
        note = None
        progress = st.progress(0.0, text="Starting...")
        for step, index in enumerate(range(first_page - 1, last_page)):
            progress.progress(
                step / pages_total, text=f"Reading page {index + 1} ({step + 1} of {pages_total})..."
            )
            try:
                page_words = run_ocr_detailed(get_ocr_input(index))
            except (OCRError, PDFError) as err:
                note = f"Stopped at page {index + 1}: {err}"
                break

            cleaned = []
            for separator, word, confidence in page_words:
                if auto_fix:
                    word, fixes = fix_anusvara_zero(word)
                    total_fixes += fixes
                cleaned.append((separator, word, confidence))

            if pages_total > 1:
                tokens.append(("\n\n" if tokens else "", f"--- Page {index + 1} ---", None))
                if cleaned:
                    cleaned[0] = ("\n", cleaned[0][1], cleaned[0][2])
            tokens.extend(cleaned)
            pages_read += 1
        progress.empty()

        if pages_read:
            st.session_state["editor"] = "".join(sep + word for sep, word, _ in tokens).strip()
            st.session_state["ocr_words"] = tokens
            st.session_state["ocr_ready"] = True
            st.session_state["ocr_used"] = used_label
            st.session_state["ocr_fixes"] = total_fixes
            st.session_state["ocr_pages"] = f"{pages_read} page(s)" if is_pdf else "1 image"
            st.session_state["ocr_note"] = note
        else:
            st.session_state.pop("ocr_ready", None)
        if note:
            st.error(note)

    if st.session_state.get("ocr_ready"):
        st.caption(
            f"Last OCR run: {st.session_state.get('ocr_pages')}, "
            f"{st.session_state.get('ocr_used')}. "
            f"Clean-up changed {st.session_state.get('ocr_fixes', 0)} character(s)."
        )
        if st.session_state.get("ocr_note"):
            st.warning(st.session_state["ocr_note"] + " Text from earlier pages is kept.")
        if not st.session_state["editor"].strip():
            st.warning(
                "No text was found. Try a sharper, higher-resolution image with "
                "printed Kannada text."
            )

        edited = st.text_area(
            "Review and correct the text below",
            height=380,
            key="editor",
        )

        # --- Export ---
        base_name = os.path.splitext(uploaded.name)[0] or "kannadalens"
        st.download_button(
            "⬇ Download as TXT",
            # utf-8-sig adds a small marker at the start so Windows Notepad
            # always opens the Kannada text correctly. It is still UTF-8.
            data=edited.encode("utf-8-sig"),
            file_name=f"{base_name}.txt",
            mime="text/plain",
        )

        tab_review, tab_search, tab_summary = st.tabs(
            ["👁 Review", "🔎 Search", "📝 Summary"]
        )

        # --- Review: highlight words Tesseract is unsure about ---
        with tab_review:
            tokens = st.session_state.get("ocr_words") or []
            scored = [t for t in tokens if t[2] is not None]
            if not scored:
                st.info("No word confidence scores are available for this text.")
            else:
                st.caption(
                    "Words that Tesseract is less sure about are highlighted, so you can "
                    "check them first. This panel shows the original OCR text, so your edits "
                    "above do not appear here. On our small 7-image test, at a limit of 80 "
                    "roughly half of the highlighted words were wrong and roughly half of "
                    "all wrong words were highlighted. A word that is not highlighted can "
                    "still be wrong."
                )
                limit = st.slider(
                    "Highlight words with confidence below",
                    min_value=40,
                    max_value=95,
                    value=80,
                    step=5,
                    key="review_limit",
                )
                flagged = sum(1 for _, _, conf in scored if conf < limit)
                st.write(
                    f"**{flagged}** of {len(scored)} words highlighted "
                    f"({flagged / len(scored):.0%})"
                )
                st.html(
                    '<div style="max-height:360px; overflow:auto; padding:12px; '
                    "border:1px solid rgba(128,128,128,0.4); border-radius:8px; "
                    'font-size:1.1rem; line-height:1.9;">'
                    + confidence_html(tokens, limit)
                    + "</div>"
                )

        # --- Search ---
        with tab_search:
            query = st.text_input(
                "Find a word or phrase in the text above",
                key="query",
                placeholder="Type a Kannada or English word",
            )
            if query.strip():
                spans = find_matches(edited, query)
                if spans:
                    st.success(f"{len(spans)} match(es) found")
                    st.html(
                        '<div style="max-height:320px; overflow:auto; padding:12px; '
                        "border:1px solid rgba(128,128,128,0.4); border-radius:8px; "
                        'font-size:1.1rem; line-height:1.8;">'
                        + highlight_html(edited, spans)
                        + "</div>"
                    )
                else:
                    st.info(
                        "No matches. The OCR may have misread this word. "
                        "Try a shorter part of it."
                    )

        # --- Summary ---
        with tab_summary:
            st.caption(
                "This is an extractive summary, not AI-generated text. The app copies "
                "the sentences whose words are repeated most often in your document. It "
                "does not understand, rewrite or translate anything, and it may include "
                "OCR mistakes. Sentence splitting is simple, so an abbreviation such as "
                "'ಡಾ.' can split a sentence in two. On short documents it mostly picks "
                "the first sentences."
            )
            if not edited.strip():
                st.info("There is no text to summarize yet.")
            else:
                numbers = stats(edited)
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Words", numbers["words"])
                col_b.metric("Sentences", numbers["sentences"])
                col_c.metric("Kannada characters", f"{numbers['kannada_share']:.0%}")

                st.markdown("**Preview (start of the document)**")
                st.html(f"<p>{html.escape(preview(edited))}</p>")

                how_many = st.slider("Sentences to show", 1, 5, 3, key="summary_count")
                chosen = key_sentences(edited, how_many)
                st.markdown("**Key sentences (copied from your text)**")
                if chosen:
                    st.html(html_list(chosen))
                else:
                    st.info("No sentences long enough to pick from yet.")

                repeated = top_words(edited)
                if repeated:
                    st.markdown("**Most repeated words** (exact spelling, no stop-word filter)")
                    st.html(html_list([f"{word} ×{count}" for word, count in repeated]))