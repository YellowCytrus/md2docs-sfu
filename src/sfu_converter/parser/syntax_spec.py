from __future__ import annotations

from copy import deepcopy

_SYNTAX_SPECS = {
    1: {
        "syntaxVersion": 1,
        "blocks": [
            {
                "name": "heading",
                "marker": "[H1] Title",
                "node": "HeadingNode",
                "description": "Create a numbered heading. [H2], [H3], and [H4] create lower levels.",
                "example": "[H1] Introduction",
            },
            {
                "name": "paragraph",
                "marker": "Plain text",
                "node": "ParagraphNode",
                "description": "Any non-marker text line becomes a body paragraph.",
                "example": "This is a paragraph.",
            },
            {
                "name": "figure",
                "marker": "[IMAGE=diagram.png]",
                "node": "FigureNode",
                "description": "Insert an image and optionally use the following caption line.",
                "example": "[IMAGE=diagram.png]",
            },
            {
                "name": "table",
                "marker": "[TABLE_START]",
                "node": "TableNode",
                "description": "Parse pipe-delimited rows until [TABLE_END].",
                "example": "[TABLE_START]\n| A | B |\n[TABLE_END]",
            },
            {
                "name": "list",
                "marker": "[LIST type=bullet]",
                "node": "ListNode",
                "description": "Parse explicit list items until [LIST_END].",
                "example": "[LIST type=bullet]\n[-] item\n[LIST_END]",
            },
            {
                "name": "formula",
                "marker": "[FORMULA]",
                "node": "FormulaNode",
                "description": "Parse formula content until [FORMULA_END].",
                "example": "[FORMULA]\nE = mc^2\n[FORMULA_END]",
            },
            {
                "name": "metadata",
                "marker": "[META key=value]",
                "node": "MetadataNode",
                "description": "Attach document metadata for renderers and templates.",
                "example": "[META title=Report]",
            },
            {
                "name": "table_of_contents",
                "marker": "[TOC]",
                "node": "TableOfContentsNode",
                "description": "Insert a generated table-of-contents placeholder.",
                "example": "[TOC]",
            },
            {
                "name": "title_page",
                "marker": "[TITLE_PAGE]",
                "node": "TitlePageNode",
                "description": "Insert a generated title-page placeholder.",
                "example": "[TITLE_PAGE]",
            },
        ],
    },
    2: {
        "syntaxVersion": 2,
        "blocks": [
            {
                "name": "document",
                "marker": "[DOC syntax=2 profile=common language=ru]",
                "node": "Document",
                "description": "Declare syntax version and document-level metadata.",
                "example": "[DOC syntax=2 profile=lab_practical_project_reports language=ru]",
            },
            {
                "name": "metadata",
                "marker": '[META key=title value="..."]',
                "node": "MetadataNode",
                "description": "Attach a key/value metadata field to the document.",
                "example": '[META key=title value="Report title"]',
            },
            {
                "name": "heading",
                "marker": '[H level=1 title="..." number=auto]',
                "node": "HeadingNode",
                "description": "Create a heading with explicit level (1-6), title, and numbering mode.",
                "example": '[H level=1 title="Introduction" number=auto]',
            },
            {
                "name": "structural_section",
                "marker": '[STRUCTURAL title="..."]',
                "node": "StructuralSectionNode",
                "description": "Create a special structural section heading such as ВВЕДЕНИЕ or СПИСОК ИСТОЧНИКОВ.",
                "example": '[STRUCTURAL title="ВВЕДЕНИЕ"]',
            },
            {
                "name": "paragraph",
                "marker": "[P]",
                "node": "ParagraphNode",
                "description": "Create a normal paragraph from explicit text.",
                "example": "[P] Body text.",
            },
            {
                "name": "figure",
                "marker": (
                    '[FIGURE src="..." caption="..." id=fig:id '
                    'explanatory="1 — item\\n2 — item" sheet=1 total_sheets=2]'
                ),
                "node": "FigureNode",
                "description": "Insert a figure with optional caption, reference id, explanatory data, and sheet labels.",
                "example": (
                    '[FIGURE src="diagram.png" caption="Overview" id=fig:overview '
                    'explanatory="1 — input\\n2 — processor" sheet=1 total_sheets=2]'
                ),
            },
            {
                "name": "drawing",
                "marker": '[DRAWING sheet=A1 frame=graphic form=form_5 scale="1:50"]',
                "node": "DrawingSheetNode",
                "description": "Create a framed drawing/scheme sheet with form 5/6 title block.",
                "example": (
                    '[DRAWING sheet=A1 frame=graphic form=form_5 scale="1:50"]\n'
                    'src="diagram.svg"\n'
                    "[/DRAWING]"
                ),
            },
            {
                "name": "poster",
                "marker": '[POSTER format=A1 title="..."] ... [/POSTER]',
                "node": "PosterNode",
                "description": "Create an A1 poster sheet with reverse-side title block.",
                "example": '[POSTER format=A1 title="Architecture"]\n[P] Content\n[/POSTER]',
            },
            {
                "name": "slide_deck",
                "marker": "[SLIDE_DECK format=A4] ... [/SLIDE_DECK]",
                "node": "SlideDeckNode",
                "description": "Create an A4-printable slide deck for optional PPTX output.",
                "example": (
                    "[SLIDE_DECK format=A4]\n"
                    '[SLIDE first_slide=true title="Topic" student="Name" supervisor="Name"][/SLIDE]\n'
                    "[/SLIDE_DECK]"
                ),
            },
            {
                "name": "table",
                "marker": '[TABLE caption="..." id=tbl:id number=auto]',
                "node": "TableNode",
                "description": "Parse pipe-delimited rows until [TABLE_END].",
                "example": '[TABLE caption="Data"]\n| A | B |\n[TABLE_END]',
            },
            {
                "name": "list",
                "marker": "[LIST type=bullet]",
                "node": "ListNode",
                "description": "Parse explicit list items until [LIST_END].",
                "example": "[LIST type=bullet]\n[-] item\n[LIST_END]",
            },
            {
                "name": "formula",
                "marker": "[FORMULA id=eq:id number=auto format=latex consecutive_with=eq:previous]",
                "node": "FormulaNode",
                "description": (
                    "Parse formula content and optional FORMULA_SYMBOL lines until [FORMULA_END]. "
                    "With format=latex the content is rendered as a native Word equation (OMML); "
                    "inline $...$ elsewhere in text is rendered inline as an equation too."
                ),
                "example": (
                    "[FORMULA id=eq:main number=auto format=latex]\n"
                    r"E = mc^2" + "\n"
                    '[FORMULA_SYMBOL name=E text="energy, J"]\n'
                    "[FORMULA_END]"
                ),
            },
            {
                "name": "reference",
                "marker": "[REF target=id]",
                "node": "ReferenceNode",
                "description": "Insert a reference to a figure, table, formula, or appendix id.",
                "example": "[REF target=fig:overview]",
            },
            {
                "name": "source",
                "marker": '[SOURCE number=1 type=book_two_authors lang=ru] ... [/SOURCE]',
                "node": "BibliographyEntryNode | SourceRecordNode",
                "description": "Add a numbered free-text or structured GOST bibliography/source entry.",
                "example": (
                    "[SOURCE number=1 type=book_two_authors lang=ru]\n"
                    'authors="Иванов И. И., Петров П. П."\n'
                    'title="Анализ данных" city="Красноярск" publisher="СФУ" year=2023 pages=320\n'
                    "[/SOURCE]"
                ),
            },
            {
                "name": "footnote",
                "marker": '[FN id=1 text="..."]',
                "node": "FootnoteAnchor | FootnoteNode",
                "description": "Insert an inline footnote anchor and body; FN_ANCHOR/FN_BODY split placement is also supported.",
                "example": '[P] Text [FN id=1 text="Source note"].',
            },
            {
                "name": "page_break",
                "marker": "[PAGE_BREAK]",
                "node": "PageBreakNode",
                "description": "Force a page break in the rendered document.",
                "example": "[PAGE_BREAK]",
            },
            {
                "name": "appendix",
                "marker": '[APPENDIX id=app:a title="..."]',
                "node": "AppendixNode",
                "description": "Start an appendix section with optional id and title.",
                "example": '[APPENDIX id=app:a title="Data"]',
            },
            {
                "name": "raw",
                "marker": "[RAW]",
                "node": "RawBlockNode",
                "description": "Escape marker-like text until [RAW_END].",
                "example": "[RAW]\n[This is literal]\n[RAW_END]",
            },
        ],
    },
}


def get_syntax_spec(syntax_version: int) -> dict:
    """Return parser-owned syntax metadata for CLI help and docs."""

    try:
        return deepcopy(_SYNTAX_SPECS[syntax_version])
    except KeyError as exc:
        raise ValueError(f"Unsupported syntax version: {syntax_version}") from exc
