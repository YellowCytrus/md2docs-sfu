from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, auto
from types import MappingProxyType


class BlockType(Enum):
    DOCUMENT = auto()
    PARAGRAPH = auto()
    HEADING = auto()
    TABLE = auto()
    FIGURE = auto()
    FORMULA = auto()
    LIST = auto()
    LIST_ITEM = auto()
    PAGE_BREAK = auto()
    STRUCTURAL_SECTION = auto()
    APPENDIX = auto()
    BIBLIOGRAPHY_ENTRY = auto()
    RAW_BLOCK = auto()
    TABLE_CAPTION = auto()
    FIGURE_CAPTION = auto()
    METADATA = auto()
    TABLE_OF_CONTENTS = auto()
    TITLE_PAGE = auto()
    REFERENCE = auto()
    ABBREVIATIONS_LIST = auto()
    SOURCE_RECORD = auto()
    FOOTNOTE = auto()
    SECTION_SETUP = auto()
    PROJECT_DESIGNATION = auto()
    DRAWING_SHEET = auto()
    POSTER = auto()
    SLIDE_DECK = auto()
    SLIDE = auto()


class HeadingLevel(Enum):
    H1 = 1
    H2 = 2
    H3 = 3
    H4 = 4
    H5 = 5
    H6 = 6


class StructuralSectionType(Enum):
    ABSTRACT = "РЕФЕРАТ"
    ANNOTATION = "АННОТАЦИЯ"
    CONTENTS = "СОДЕРЖАНИЕ"
    INTRODUCTION = "ВВЕДЕНИЕ"
    CONCLUSION = "ЗАКЛЮЧЕНИЕ"
    ABBREVIATIONS = "СПИСОК СОКРАЩЕНИЙ"
    SOURCES = "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"
    APPENDIX = "ПРИЛОЖЕНИЕ"


class ListType(Enum):
    BULLET = auto()
    NUMBERED = auto()
    LETTERED = auto()


class SectionOrientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class SheetFormat(str, Enum):
    A4 = "A4"
    A3 = "A3"
    A3X4 = "A3x4"
    A4X4 = "A4x4"
    A2 = "A2"
    A1 = "A1"


class FrameType(str, Enum):
    NONE = "none"
    TEXT_FIRST = "text_first"
    TEXT_FOLLOWING = "text_following"
    GRAPHIC = "graphic"


class TitleBlockForm(str, Enum):
    FORM_1 = "form_1"
    FORM_2 = "form_2"
    FORM_3 = "form_3"
    FORM_4 = "form_4"
    FORM_5 = "form_5"
    FORM_6 = "form_6"


class ContinuationLabel(Enum):
    CONTINUATION = "continuation"
    FINAL = "final"


@dataclass(frozen=True)
class SourceSpan:
    """Location in the source TXT file."""

    line_start: int
    line_end: int
    col_start: int = 0
    col_end: int = 0
    filename: str | None = None


@dataclass(frozen=True)
class TextRun:
    """A run of text with optional inline formatting."""

    text: str
    bold: bool = False
    italic: bool = False
    source: SourceSpan | None = None


@dataclass(frozen=True)
class FootnoteAnchor:
    """Inline reference to a footnote body."""

    marker: str
    source: SourceSpan | None = None


PageRange = int | tuple[int, int]


@dataclass(frozen=True)
class Citation:
    """One bibliography citation item inside an in-text source reference."""

    number: int
    volume: int | None = None
    pages: PageRange | None = None


@dataclass(frozen=True)
class CitationNode:
    """Inline structured source citation such as ``[20, с. 29]``."""

    citations: tuple[Citation, ...]
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "citations", tuple(self.citations))

    @property
    def text(self) -> str:
        return _format_citation_node(self)


InlineNode = TextRun | FootnoteAnchor | CitationNode


@dataclass(frozen=True)
class ParagraphNode:
    """A normal text paragraph."""

    runs: tuple[InlineNode, ...]
    source: SourceSpan | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "runs", tuple(self.runs))
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class HeadingNode:
    """A heading block."""

    level: HeadingLevel
    text: str
    number: str | None = None
    source: SourceSpan | None = None


@dataclass(frozen=True)
class StructuralSectionNode:
    """A standard structural section heading such as introduction or sources."""

    section_type: StructuralSectionType
    title: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class AbbreviationEntryNode:
    short: str
    long: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class AbbreviationsListNode:
    entries: tuple[AbbreviationEntryNode, ...]
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))


@dataclass(frozen=True)
class TableCell:
    text: str


@dataclass(frozen=True)
class TableRow:
    cells: tuple[TableCell, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cells", tuple(self.cells))


@dataclass(frozen=True)
class TableNote:
    marker: str
    text: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class TableNode:
    """A table block."""

    rows: tuple[TableRow, ...]
    caption: str | None = None
    id: str | None = None
    number: str | None = None
    unit_label: str | None = None
    continuation: ContinuationLabel | None = None
    notes: tuple[TableNote, ...] = ()
    column_units: tuple[str | None, ...] = ()
    header_row_count: int = 1
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))
        object.__setattr__(self, "notes", tuple(self.notes))
        object.__setattr__(self, "column_units", tuple(self.column_units))

    @property
    def header_levels(self) -> int:
        return self.header_row_count


@dataclass(frozen=True)
class TableCaptionNode:
    """A standalone table caption block."""

    text: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class FigureNode:
    """An image/figure block."""

    src: str | None = None
    caption: str | None = None
    id: str | None = None
    explanatory_data: tuple[str, ...] | None = None
    sheet: int | None = None
    total_sheets: int | None = None
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        if self.explanatory_data is not None:
            object.__setattr__(self, "explanatory_data", tuple(self.explanatory_data))


@dataclass(frozen=True)
class FormulaSymbol:
    """A symbol explanation line belonging to a formula."""

    name: str
    description: str
    repeats: bool = False


@dataclass(frozen=True)
class FormulaNode:
    """A formula block.

    ``format="latex"`` marks ``content`` as a LaTeX expression that is rendered
    as a native Word OMML equation; the default ``None`` keeps the historical
    plain-text rendering.
    """

    content: str
    id: str | None = None
    number: str | None = None
    format: str | None = None
    explanation: str | None = None
    explanations: tuple[FormulaSymbol, ...] = ()
    continuation_lines: tuple[str, ...] = ()
    consecutive_with: str | None = None
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "explanations", tuple(self.explanations))
        object.__setattr__(self, "continuation_lines", tuple(self.continuation_lines))


@dataclass(frozen=True)
class ListItemNode:
    text: str
    children: tuple["ListNode", ...] = ()
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "children", tuple(self.children))


@dataclass(frozen=True)
class ListNode:
    list_type: ListType
    items: tuple[ListItemNode | "ListNode", ...]
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True)
class SectionSetupNode:
    orientation: SectionOrientation = SectionOrientation.PORTRAIT
    sheet_format: SheetFormat = SheetFormat.A4
    frame: FrameType = FrameType.NONE
    title_block_form: TitleBlockForm | None = None
    blocks: tuple["BlockNode", ...] = ()
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(self.blocks))


@dataclass(frozen=True)
class ProjectDesignationNode:
    prefix: str
    specialty_code: str
    group_code: str | None = None
    document_code: str = ""
    year: str | None = None
    schema_code: str | None = None
    schema_type: str | None = None
    source: SourceSpan | None = None


@dataclass(frozen=True)
class DrawingSheetNode:
    sheet_format: SheetFormat = SheetFormat.A1
    frame: FrameType = FrameType.GRAPHIC
    title_block_form: TitleBlockForm | None = TitleBlockForm.FORM_5
    scale: str | None = None
    src: str | None = None
    designation: str | None = None
    font_type: str | None = None
    source: SourceSpan | None = None


@dataclass(frozen=True)
class PosterNode:
    sheet_format: SheetFormat = SheetFormat.A1
    title: str = ""
    blocks: tuple["BlockNode", ...] = ()
    fill_percent: float | None = None
    reverse_title_block: bool = True
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(self.blocks))


@dataclass(frozen=True)
class SlideNode:
    first_slide: bool = False
    fields: Mapping[str, str] = field(default_factory=dict)
    body: tuple[str, ...] = ()
    fill_percent: float | None = None
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fields, MappingProxyType):
            object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))
        object.__setattr__(self, "body", tuple(self.body))


@dataclass(frozen=True)
class SlideDeckNode:
    sheet_format: SheetFormat = SheetFormat.A4
    slides: tuple[SlideNode, ...] = ()
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "slides", tuple(self.slides))


@dataclass(frozen=True)
class PageBreakNode:
    source: SourceSpan | None = None


@dataclass(frozen=True)
class AppendixNode:
    title: str
    id: str | None = None
    letter: str | None = None
    appendix_type: str | None = None
    subtitle: str | None = None
    sheet_format: SheetFormat = SheetFormat.A4
    independent: bool = False
    blocks: tuple = ()
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(self.blocks))


@dataclass(frozen=True)
class TableOfContentsNode:
    """Insertion point for an automatically generated table of contents."""

    title: str = "СОДЕРЖАНИЕ"
    levels: int = 3
    source: SourceSpan | None = None


@dataclass(frozen=True)
class BibliographyEntryNode:
    number: int
    text: str
    source: SourceSpan | None = None


class SourceRecordType(str, Enum):
    NORMATIVE = "normative"
    PATENT = "patent"
    BOOK_ONE_AUTHOR = "book_one_author"
    BOOK_TWO_AUTHORS = "book_two_authors"
    BOOK_THREE_AUTHORS = "book_three_authors"
    BOOK_FOUR_PLUS_AUTHORS = "book_four_plus_authors"
    VOLUME = "volume"
    DISSERTATION = "dissertation"
    ELECTRONIC = "electronic"
    ARTICLE = "article"


@dataclass(frozen=True)
class SourceRecordNode:
    number: int
    record_type: SourceRecordType
    fields: Mapping[str, str]
    language: str
    source: SourceSpan | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fields, MappingProxyType):
            object.__setattr__(self, "fields", MappingProxyType(dict(self.fields)))


@dataclass(frozen=True)
class FootnoteNode:
    marker: str
    text: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class ReferenceNode:
    target: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class RawBlockNode:
    """Literal/escaped text that should not be parsed."""

    text: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class MetadataNode:
    key: str
    value: str
    source: SourceSpan | None = None


@dataclass(frozen=True)
class TitlePageNode:
    """Insertion point for a generated title page based on document metadata."""

    profile: str | None = None
    source: SourceSpan | None = None


BlockNode = (
    ParagraphNode
    | HeadingNode
    | TableNode
    | TableCaptionNode
    | FigureNode
    | FormulaNode
    | ListNode
    | PageBreakNode
    | StructuralSectionNode
    | AppendixNode
    | BibliographyEntryNode
    | SourceRecordNode
    | FootnoteNode
    | ReferenceNode
    | RawBlockNode
    | MetadataNode
    | TableOfContentsNode
    | TitlePageNode
    | AbbreviationsListNode
    | SectionSetupNode
    | ProjectDesignationNode
    | DrawingSheetNode
    | PosterNode
    | SlideDeckNode
    | SlideNode
)


@dataclass(frozen=True)
class Document:
    """Root AST node representing a complete document."""

    blocks: tuple[BlockNode, ...]
    syntax_version: int = 1
    metadata: Mapping[str, str] = field(default_factory=dict)
    source_file: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "blocks", tuple(self.blocks))
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


def _format_citation_node(node: CitationNode) -> str:
    return "[" + "; ".join(_format_citation(citation) for citation in node.citations) + "]"


def _format_citation(citation: Citation) -> str:
    parts = [str(citation.number)]
    if citation.volume is not None:
        parts.append(f"т. {citation.volume}")
    if citation.pages is not None:
        pages = citation.pages
        if isinstance(pages, tuple):
            page_text = f"{pages[0]}–{pages[1]}"
        else:
            page_text = str(pages)
        parts.append(f"с. {page_text}")
    return ", ".join(parts)
