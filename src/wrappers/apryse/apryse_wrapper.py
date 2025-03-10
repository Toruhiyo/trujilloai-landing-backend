from copy import deepcopy
from difflib import SequenceMatcher
import itertools
import logging
from math import sqrt
import re
from time import perf_counter
from typing import Optional, Callable
from pathlib import Path
from dataclasses import dataclass
from data_structures_utils.list_toolbox import flatten_list
from src.app.entities.masks.dtos import Quad
from .apryse_session import ApryseSession
from .errors import InvalidOrCorruptedFile
from src.utils.metaclasses import DynamicSingleton
from src.config.vars_grabber import VariablesGrabber
from apryse_sdk.PDFNetPython import (
    PDFDoc,
    TextSearch,
    ColorPt,
    Annot,
    RedactionAnnot,
    Page,
    Rect,
    QuadPoint,
    TextExtractor,
    Point,
    BorderStyle,
    FreeText,
    Word,
)
from text_utils.regex_toolbox import make_literal

logger = logging.getLogger(__name__)

APRYSE_SDK_KEY = VariablesGrabber().get("APRYSE_SDK_KEY", type=str, default=None)
MAX_COMPUTE_AMBIENT_STRING_SECONDS = 30
MAX_QUADS_LENGTH_TO_COMPUTE_PERMUTATIONS = 6


@dataclass
class OffsetDTO:
    left: int = 0
    right: int = 0
    top: int = 0
    bottom: int = 0


NO_OFFSET = OffsetDTO()
DEFAULT_OFFSET = OffsetDTO(left=2, right=3, top=3, bottom=3)

DEFAULT_N_AMBIENT_LEADING_WORDS = 3
DEFAULT_N_AMBIENT_TRAILING_WORDS = 3


class ApryseWrapper(metaclass=DynamicSingleton):
    @property
    def doc(self) -> PDFDoc:
        return self.__doc

    def __init__(self, filepath: Path, api_key: str = APRYSE_SDK_KEY):
        ApryseSession(api_key)
        self.__filepath = filepath
        self.__doc = PDFDoc(str(filepath))

    def save_document(
        self, output_path: Optional[Path] = None, flag: Optional[int] = None
    ) -> None:
        output_path = output_path or self.__filepath
        self.__doc.Save(str(output_path), flag)

    def remove_annotations(self, output_path: Optional[Path] = None) -> Path:
        output_path = output_path or self.__filepath
        doc = self.__doc
        itr = doc.GetPageIterator()
        while itr.HasNext():
            page = itr.Current()
            i = 0
            while page.GetNumAnnots() - i > 0:
                annot = page.GetAnnot(i)
                if annot.GetType() != Annot.e_Redact:
                    i += 1
                    continue
                page.AnnotRemove(annot)
            itr.Next()
        doc.Save(str(output_path), doc.e_verified)
        return output_path

    def extract_redact_annotations(
        self,
        transform_function: Optional[Callable] = None,
        offset: OffsetDTO = DEFAULT_OFFSET,
    ) -> list[dict]:
        annotations = []

        def extract_redact_annotation(annot: Annot, page: Page, page_num: int) -> Page:
            if not annot.IsValid() or annot.GetType() != Annot.e_Redact:
                return page
            annot = RedactionAnnot(annot)
            overlay_text = annot.GetOverlayText()
            page_rotation = page.GetRotation()
            page.SetRotation(0)
            quads = self.__get_redact_annotation_quads(annot)
            if not quads:
                quads = self.__compute_redact_annotation_quads_from_rect(annot)

            covered_text = self.__extract_covered_text_from_quads(
                page, quads, offset=offset
            )
            quads = [self.__fix_displaced_quadpoints(quad, page) for quad in quads]
            quads = [self.__fix_unflipped_quadpoints(quad) for quad in quads]
            quads = [self.flip_quadpoint_vertically(quad, page) for quad in quads]
            annotation = {
                "id": len(annotations) + 1,
                "page": page_num,
                "covered_text": covered_text,
                "label": overlay_text,
                "quads": quads,
            }
            if isinstance(transform_function, Callable):
                annotation = transform_function(annotation)
            annotations.append(annotation)
            page.SetRotation(page_rotation)
            return page

        self.__iterate_annotations(extract_redact_annotation)
        return annotations

    def compute_quadpoints_for_text(
        self,
        text: str,
        page_number: Optional[int] = None,
        reference_quads: Optional[list[QuadPoint]] = None,
        reference_ambient_string: Optional[str] = None,
        string_transform_function: Optional[Callable[[str], str]] = None,
        enable_fault_tolerance: bool = False,
        enable_disambiguation: bool = True,
    ) -> list[QuadPoint] | None:
        doc = self.__doc
        page_numbers = (
            [page_number]
            if isinstance(page_number, int)
            else self.__find_match_page_numbers(doc, text)
        )
        for i in page_numbers:
            page = doc.GetPage(i)
            quads = self.__compute_quadpoints_for_text_in_page(
                text,
                page,
                reference_quads=reference_quads,
                reference_ambient_string=reference_ambient_string,
                string_transform_function=string_transform_function,
                enable_disambiguation=enable_disambiguation,
            )
            if quads:
                return quads
            elif enable_fault_tolerance:
                return self.__compute_quadpoints_for_text_in_page_fault_tolerant(
                    text,
                    page,
                    reference_quads=reference_quads,
                    reference_ambient_string=reference_ambient_string,
                    string_transform_function=string_transform_function,
                    enable_disambiguation=enable_disambiguation,
                )

    def __find_match_pages(self, doc: PDFDoc, text: str) -> list[Page]:
        page_numbers = self.__find_match_page_numbers(doc, text)
        return [doc.GetPage(i) for i in page_numbers]

    def __find_match_page_numbers(self, doc: PDFDoc, text: str) -> list[int]:
        page_numbers = []
        txt_search = TextSearch()
        mode = TextSearch.e_whole_word | TextSearch.e_page_stop
        pattern = text
        txt_search.Begin(doc, pattern, mode)
        while True:
            search_result = txt_search.Run()
            if not search_result.IsFound():
                break
            match = search_result.GetMatch()
            page_number = match.GetPageNumber()
            page_numbers.append(page_number)
        return page_numbers

    def create_redact_annotations(
        self, annotations: list[dict], output_path: Optional[Path] = None
    ) -> Path:
        output_path = output_path or self.__filepath

        def create_redact_annotations(page: Page, page_num: int, doc: PDFDoc) -> Page:
            doc_sdf = doc.GetSDFDoc()
            for annotation in annotations:
                if annotation["page"] != page_num:
                    continue
                quads = [
                    self.flip_quadpoint_vertically(
                        self.quad_to_quadpoint(Quad(**quad)),
                        page,
                    )
                    for quad in annotation["quads"]
                ]
                overlay_text = annotation["label"]
                for quad in quads:
                    rect = self.__get_rect_from_quad(quad)
                    redact = RedactionAnnot.Create(doc_sdf, rect)
                    redact.SetContentRect(rect)
                    redact.SetContents(overlay_text)
                    redact.SetBorderStyle(
                        BorderStyle(BorderStyle.e_solid, 1, 10, 20), True
                    )
                    # redact.SetTitle(overlay_text)
                    redact.SetColor(ColorPt(0, 0, 0), 3)
                    redact.SetInteriorColor(ColorPt(0, 0, 0), 3)
                    page.AnnotPushBack(redact)
            return page

        self.__iterate_pages(
            create_redact_annotations,
            output_path=output_path,
            shall_save_file=True,
        )
        return output_path

    def flatten_annotations(self, output_path: Optional[Path] = None) -> Path:
        output_path = output_path or self.__filepath
        doc = self.__doc
        doc.FlattenAnnotations()
        doc.Save(str(output_path), doc.e_verified)
        # doc.Save(str(output_path), SDFDoc.e_linearized)
        return output_path

    def flatten_redact_annotations(self, output_path: Optional[Path] = None) -> Path:
        output_path = output_path or self.__filepath

        def flatten_redact_annotation(annot: Annot, page: Page, page_num: int) -> Page:
            if not annot.IsValid() or annot.GetType() != Annot.e_Redact:
                return page
            redact = RedactionAnnot(annot)
            redact.Flatten(page)
            return page

        self.__iterate_annotations(
            flatten_redact_annotation,
            output_path=output_path,
            shall_save_file=True,
        )
        return output_path

    def flatten_free_texts(self, output_path: Optional[Path] = None) -> Path:
        output_path = output_path or self.__filepath

        def flatten_free_text(annot: Annot, page: Page, page_num: int) -> Page:
            if not annot.IsValid() or annot.GetType() != Annot.e_FreeText:
                return page
            redact = FreeText(annot)
            rect = redact.GetRect()
            page = self.__remove_elements_from_page_matching_rect(page, rect)
            redact.Flatten(page)
            return page

        self.__iterate_annotations(
            flatten_free_text,
            output_path=output_path,
            shall_save_file=True,
        )
        return output_path

    def quad_to_quadpoint(self, quad: Quad) -> QuadPoint:
        min_x = min(quad.x1, quad.x2, quad.x3, quad.x4)
        max_x = max(quad.x1, quad.x2, quad.x3, quad.x4)
        min_y = min(quad.y1, quad.y2, quad.y3, quad.y4)
        max_y = max(quad.y1, quad.y2, quad.y3, quad.y4)
        return QuadPoint(
            Point(float(min_x), float(min_y)),
            Point(float(max_x), float(min_y)),
            Point(float(min_x), float(max_y)),
            Point(float(max_x), float(max_y)),
        )

    def quadpoint_to_quad(self, quadpoint: QuadPoint) -> Quad:
        min_x = min(quadpoint.p1.x, quadpoint.p2.x, quadpoint.p3.x, quadpoint.p4.x)
        max_x = max(quadpoint.p1.x, quadpoint.p2.x, quadpoint.p3.x, quadpoint.p4.x)
        min_y = min(quadpoint.p1.y, quadpoint.p2.y, quadpoint.p3.y, quadpoint.p4.y)
        max_y = max(quadpoint.p1.y, quadpoint.p2.y, quadpoint.p3.y, quadpoint.p4.y)
        return Quad(
            x1=min_x,
            y1=max_y,
            x2=max_x,
            y2=max_y,
            x3=max_x,
            y3=min_y,
            x4=min_x,
            y4=min_y,
        )

    def get_page_text(self, page_number: int) -> str:
        doc = self.__doc
        page = doc.GetPage(page_number)
        txt = TextExtractor()
        txt.Begin(page)
        return txt.GetAsText()

    def find_matches(
        self,
        pattern: str,
        start_page: Optional[int] = None,
        end_page: Optional[int] = None,
        ignore_case: bool = False,
        whole_word: bool = False,
    ) -> list[tuple[str, int]]:
        start_page = start_page or -1
        end_page = end_page or -1
        doc = self.__doc
        txt_search = TextSearch()
        mode = TextSearch.e_raw_text_search
        if not ignore_case:
            mode |= TextSearch.e_case_sensitive
        if whole_word:
            mode |= TextSearch.e_whole_word
        txt_search.Begin(doc, pattern, mode, start_page=start_page, end_page=end_page)
        matches = []
        while True:
            search_result = txt_search.Run()
            if not search_result.IsFound():
                break
            match = search_result.GetMatch()
            page_number = search_result.GetPageNumber()
            matches.append((match, page_number))
        return matches

    def compute_ambient_string(
        self,
        page_number: int,
        quads: list[QuadPoint],
        n_leading_words: int = DEFAULT_N_AMBIENT_LEADING_WORDS,
        n_trailing_words: int = DEFAULT_N_AMBIENT_TRAILING_WORDS,
        offset: OffsetDTO = DEFAULT_OFFSET,
    ) -> str | None:
        doc = self.__doc
        permutations = (
            itertools.permutations(quads)
            if len(quads) < MAX_QUADS_LENGTH_TO_COMPUTE_PERMUTATIONS
            else [quads]
        )
        t0 = perf_counter()
        for permutation in permutations:
            permutation = list(permutation)
            ambient_string = self.__compute_ambient_string_for_quads(
                doc,
                page_number,
                permutation,
                n_leading_words,
                n_trailing_words,
                offset=offset,
            )
            if ambient_string:
                return ambient_string
            if perf_counter() - t0 > MAX_COMPUTE_AMBIENT_STRING_SECONDS:
                break
        logger.warning(
            f"No matches found for quads in page {page_number}. Cannot compute ambient string."
        )
        return None

    # Private:
    def __compute_ambient_string_for_quads(
        self,
        doc: PDFDoc,
        page_number: int,
        quads: list[QuadPoint],
        n_leading_words: int,
        n_trailing_words: int,
        apply_vertically_flip_correction: bool = True,
        offset: OffsetDTO = DEFAULT_OFFSET,
    ) -> str | None:
        page = doc.GetPage(page_number)
        quads = [self.flip_quadpoint_vertically(quad, page) for quad in quads]
        covered_text = self.__extract_covered_text_from_quads(
            page, quads, offset=offset
        )
        quads = [self.flip_quadpoint_vertically(quad, page) for quad in quads]
        txt_search = TextSearch()
        # txt_search.SetAmbientWordsBefore(n_leading_words)
        # txt_search.SetAmbientWordsAfter(n_trailing_words)
        pattern = covered_text
        pattern = make_literal(pattern)
        pattern = re.sub(r"-", ".?", pattern)
        pattern = re.sub(r"\s+", "\\\\s*", pattern)
        mode = (
            TextSearch.e_ambient_string
            | TextSearch.e_reg_expression
            # | TextSearch.e_case_sensitive
            # | TextSearch.e_whole_word
            # | TextSearch.e_raw_text_search
            | TextSearch.e_page_stop
            | TextSearch.e_highlight
        )
        try:
            txt_search.Begin(
                doc, pattern, mode, start_page=page_number, end_page=page_number
            )
            results = []
            while True:
                search_result = txt_search.Run()
                if not search_result.IsFound():
                    break
                highlights = search_result.GetHighlights()
                highlights.Begin(doc)
                if not highlights.HasNext():
                    continue
                match_quads = [quad for quad in highlights.GetCurrentQuads()]
                match_ambient_string = search_result.GetAmbientString()
                results.append((match_ambient_string, match_quads))
            if not results:
                return None
            matches_quads = [match_quads for _, match_quads in results]
            matches_quads = [
                [self.flip_quadpoint_vertically(quad, page) for quad in match_quads]
                for match_quads in matches_quads
            ]
            i = (
                self.__get_quads_index_closer_to_reference_quads(matches_quads, quads)
                if len(matches_quads) > 1
                else 0
            )
            ambient_string = results[i][0]
            return ambient_string
        except Exception as e:
            logger.warning(
                f"Failed computing ambient string for quads in page {page_number}: {e}"
            )
            return None

    def __compute_quadpoints_for_text_in_page(
        self,
        text: str,
        page: Page,
        reference_quads: Optional[list[QuadPoint]] = None,
        reference_ambient_string: Optional[str] = None,
        string_transform_function: Optional[Callable[[str], str]] = None,
        enable_disambiguation: bool = True,
        i0_line: int | None = 0,
        i0_word: int | None = 0,
    ) -> list[QuadPoint] | None:
        i0_line = i0_line or 0
        i0_word = i0_word or 0
        txt = TextExtractor()
        txt.Begin(page)
        separator = ""
        string_transform_function = string_transform_function or (lambda x: x)
        processed_text_parts = [string_transform_function(s) for s in text.split()]
        processed_text = string_transform_function(separator.join(processed_text_parts))
        quad = None
        all_matches_quads = []
        prev_lines_quads = []
        accum_words = ""
        i_line = 0
        line = txt.GetFirstLine()
        while line.IsValid():
            i_line += 1
            if i_line < i0_line:
                line = line.GetNextLine()
                continue
            line_quads = []
            if line.GetNumWords() == 0:
                line = line.GetNextLine()
                continue
            line_bbox = line.GetBBox()
            i_word = 0
            word = line.GetFirstWord()
            while word.IsValid():
                i_word += 1
                if i_line == i0_line:
                    i_word = i0_word
                    i0_word = 0
                if i_word < i0_word:
                    word = word.GetNextWord()
                    continue
                word_length = word.GetStringLen()
                if word_length == 0:
                    word = word.GetNextWord()
                    continue

                word_string = word.GetString()
                provisional_new_accum_words = string_transform_function(
                    f"{accum_words}{separator}{word_string}"
                )
                if (
                    provisional_new_accum_words
                    and len(provisional_new_accum_words) <= len(processed_text)
                    and provisional_new_accum_words
                    == processed_text[: len(provisional_new_accum_words)]
                ):
                    word_bbox = word.GetBBox()
                    if not quad:
                        quad = QuadPoint()
                        quad.p1 = Point(word_bbox.x1, line_bbox.y2)
                        quad.p2 = Point(word_bbox.x2, line_bbox.y2)
                        quad.p3 = Point(word_bbox.x1, line_bbox.y1)
                        quad.p4 = Point(word_bbox.x2, line_bbox.y1)
                    else:
                        quad.p2 = Point(word_bbox.x2, line_bbox.y2)
                        quad.p4 = Point(word_bbox.x2, line_bbox.y1)
                    accum_words += f"{separator}{word_string}"
                else:
                    if accum_words:
                        if string_transform_function(accum_words) == processed_text:
                            if quad:
                                quad = self.flip_quadpoint_vertically(quad, page)
                                line_quads.append(quad)
                            quads = prev_lines_quads + [line_quads]
                            quads = flatten_list(quads)
                            all_matches_quads.append(quads)
                            line_quads = []
                            accum_words = ""
                        quad = None
                    line_quads = []
                    prev_lines_quads = []
                    accum_words = ""
                    provisional_new_accum_words = string_transform_function(
                        f"{accum_words}{separator}{word_string}"
                    )
                    if (
                        provisional_new_accum_words
                        and len(provisional_new_accum_words) <= len(processed_text)
                        and provisional_new_accum_words
                        == processed_text[: len(provisional_new_accum_words)]
                    ):
                        word_bbox = word.GetBBox()
                        if not quad:
                            quad = QuadPoint()
                            quad.p1 = Point(word_bbox.x1, line_bbox.y2)
                            quad.p2 = Point(word_bbox.x2, line_bbox.y2)
                            quad.p3 = Point(word_bbox.x1, line_bbox.y1)
                            quad.p4 = Point(word_bbox.x2, line_bbox.y1)
                        else:
                            quad.p2 = Point(word_bbox.x2, line_bbox.y2)
                            quad.p4 = Point(word_bbox.x2, line_bbox.y1)
                        accum_words += f"{separator}{word_string}"
                word = word.GetNextWord()
            line = line.GetNextLine()
            # if line_quads:
            #     prev_lines_quads.append(line_quads)
            if accum_words and quad:
                quad = self.flip_quadpoint_vertically(quad, page)
                line_quads.append(quad)
                prev_lines_quads.append(line_quads)
                quad = None
                # accum_words = ""

        if len(all_matches_quads) == 1:
            return all_matches_quads[0]
        elif len(all_matches_quads) > 1:
            if not enable_disambiguation:
                logger.debug(
                    f"Multiple matches found for text '{text}' in page {page.GetIndex()}. Returning None since disambiguation is disabled."
                )
                return None
            if not reference_quads and not reference_ambient_string:
                logger.warning(
                    f"Cannot disambiguate multiple matches found for text '{text}' in page {page.GetIndex()} without reference quads or ambient string. Taking the first match."
                )
                return all_matches_quads[0]
            logger.info(
                f"Multiple matches found for text '{text}' in page {page.GetIndex()}. Disambiguating with reference quads and/or ambient string."
            )
            return self.__disambiguate_multiple_quads_match(
                all_matches_quads,
                page_number=page.GetIndex(),
                reference_quads=reference_quads,
                reference_ambient_string=reference_ambient_string,
            )
        logger.debug(f"No matches found for text '{text}' in page {page.GetIndex()}")
        return None

    def __compute_quadpoints_for_text_in_page_fault_tolerant(
        self,
        text: str,
        page: Page,
        reference_quads: Optional[list[QuadPoint]] = None,
        reference_ambient_string: Optional[str] = None,
        string_transform_function: Optional[Callable[[str], str]] = None,
        enable_disambiguation: bool = True,
    ) -> list[QuadPoint] | None:
        all_quads = []
        string_transform_function = string_transform_function or (lambda x: x)
        remaining_text = string_transform_function(text)
        while remaining_text:
            longest_match, i_line, i_word = self.__find_longest_match(
                remaining_text,
                page,
                string_transform_function=string_transform_function,
            )
            if not longest_match:
                break
            quads = self.__compute_quadpoints_for_text_in_page(
                longest_match,
                page,
                reference_quads=reference_quads,
                reference_ambient_string=reference_ambient_string,
                string_transform_function=string_transform_function,
                enable_disambiguation=enable_disambiguation,
                i0_line=i_line,
                i0_word=i_word,
            )
            if quads:
                pre_remaining_text = deepcopy(remaining_text)
                remaining_text = remaining_text.replace(
                    string_transform_function(longest_match), ""
                )
                if pre_remaining_text == remaining_text:
                    remaining_text = remaining_text[len(longest_match) :]
                all_quads += quads
            else:
                break
        return all_quads if all_quads else None

    def __find_longest_match(
        self,
        text: str,
        page: Page,
        string_transform_function: Optional[Callable[[str], str]] = None,
        i0_line=0,
        i0_word=0,
    ) -> tuple[str, int | None, int | None]:
        txt = TextExtractor()
        txt.Begin(page)
        separator = ""
        string_transform_function = string_transform_function or (lambda x: x)
        processed_text_parts = [string_transform_function(s) for s in text.split()]
        processed_text = string_transform_function(separator.join(processed_text_parts))
        accum_words = ""
        longest_match = ""
        accum_i0_line = None
        accum_i0_word = None
        longest_i_line = None
        longest_i_word = None
        i_line = 0
        line = txt.GetFirstLine()
        while line.IsValid():
            i_line += 1
            if i_line < i0_line:
                line = line.GetNextLine()
                continue
            if line.GetNumWords() == 0:
                line = line.GetNextLine()
                continue
            i_word = 0
            word = line.GetFirstWord()
            while word.IsValid():
                i_word += 1
                if i_line == i0_line:
                    i_word = i0_word
                    i0_word = 0
                if i_word < i0_word:
                    word = word.GetNextWord()
                    continue
                word_length = word.GetStringLen()
                if word_length == 0:
                    word = word.GetNextWord()
                    continue
                if not accum_i0_line and not accum_i0_word:
                    accum_i0_line = i_line
                    accum_i0_word = i_word
                word_string = word.GetString()
                provisional_new_accum_words = string_transform_function(
                    f"{accum_words}{separator}{word_string}"
                )
                if (
                    provisional_new_accum_words
                    and len(provisional_new_accum_words) <= len(processed_text)
                    and provisional_new_accum_words
                    == processed_text[: len(provisional_new_accum_words)]
                ):
                    accum_words += f"{separator}{word_string}"
                    if len(accum_words) > len(longest_match):
                        longest_match = accum_words
                        longest_i_line = accum_i0_line
                        longest_i_word = accum_i0_word
                else:
                    accum_i0_line = None
                    accum_i0_word = None
                    accum_words = ""
                word = word.GetNextWord()
            line = line.GetNextLine()
        return longest_match, longest_i_line, longest_i_word

    def __disambiguate_multiple_quads_match(
        self,
        all_matches_quads: list[list[QuadPoint]],
        page_number: Optional[int] = None,
        reference_quads: Optional[list[QuadPoint]] = None,
        reference_ambient_string: Optional[str] = None,
    ) -> list[QuadPoint] | None:
        i = None
        if reference_ambient_string and (not self.__filepath or not page_number):
            raise ValueError(
                "Cannot disambiguate multiple matches by ambient string without a filepath and page number."
            )

        i_ambient = (
            self.__get_quads_index_best_matching_ambient_string(
                page_number, all_matches_quads, reference_ambient_string
            )
            if reference_ambient_string and self.__filepath and page_number is not None
            else None
        )
        i_quads = (
            self.__get_quads_index_closer_to_reference_quads(
                all_matches_quads, reference_quads
            )
            if reference_quads
            else None
        )
        if i_ambient is not None and i_quads is not None and i_ambient != i_quads:
            logger.warning(
                f"Multiple quads disambiguation results do not match (i_ambient={i_ambient}, i_quads={i_quads}). Taking ambient string match."
            )
        if i_ambient is None and i_quads is None:
            logger.warning(
                "In multiple quads disambiguation both i_ambient and i_quads are None. Taking the first match."
            )
            return all_matches_quads[0]
        i = i_ambient if i_ambient is not None else i_quads
        return all_matches_quads[i] if i is not None else None

    def __get_quads_index_best_matching_ambient_string(
        self,
        page_number: int,
        quads_list: list[list[QuadPoint]],
        reference_ambient_string: str,
        n_leading_words: int = DEFAULT_N_AMBIENT_LEADING_WORDS,
        n_trailing_words: int = DEFAULT_N_AMBIENT_TRAILING_WORDS,
        match_threshold: float = 0.5,
    ) -> int | None:
        if len(quads_list) == 0:
            raise ValueError("Quads list to disambiguate cannot be empty.")
        if len(quads_list) == 1:
            return 0
        results = []
        for quads in quads_list:
            ambient_string = self.compute_ambient_string(
                page_number,
                quads,
                n_leading_words=n_leading_words,
                n_trailing_words=n_trailing_words,
            )
            if not ambient_string:
                results.append(0)
                continue
            match_score = SequenceMatcher(
                None, ambient_string, reference_ambient_string
            ).ratio()
            results.append((match_score, ambient_string))
        sorted_results = sorted(results, reverse=True, key=lambda x: x[0])
        if sorted_results[0][0] < match_threshold:
            logger.warning(
                f"No ambient string match score is above {match_threshold}. Results: {results}"
            )
        elif len(sorted_results) > 1 and sorted_results[0][0] == sorted_results[1][0]:
            logger.warning(
                f"Multiple ambient string match scores are exactly the same. Returning None. Results: {results}"
            )
            return None
        elif (
            len(sorted_results) > 1
            and abs(sorted_results[0][0] - sorted_results[1][0]) < 0.01
        ):
            logger.warning(
                f"Multiple ambient string match scores are close to each other. Results: {results}"
            )
        scores = [score for score, _ in results]
        return scores.index(max(scores))

    def __get_redact_annotation_quads(self, annot: RedactionAnnot) -> list[QuadPoint]:
        n_quads = annot.GetQuadPointCount()
        quads = [annot.GetQuadPoint(i) for i in range(n_quads)]
        return quads

    def __compute_redact_annotation_quads_from_rect(
        self, annot: RedactionAnnot
    ) -> list[QuadPoint]:
        rect = annot.GetRect()
        quad = QuadPoint()
        quad.p1.x = rect.x1
        quad.p1.y = rect.y2
        quad.p2.x = rect.x2
        quad.p2.y = rect.y2
        quad.p3.x = rect.x1
        quad.p3.y = rect.y1
        quad.p4.x = rect.x2
        quad.p4.y = rect.y1
        return [quad]

    def __fix_unflipped_quadpoints(self, quad: QuadPoint) -> QuadPoint:
        quad_x = [quad.p1.x, quad.p2.x, quad.p3.x, quad.p4.x]
        quad_y = [quad.p1.y, quad.p2.y, quad.p3.y, quad.p4.y]
        min_x = min(quad_x)
        max_x = max(quad_x)
        min_y = min(quad_y)
        max_y = max(quad_y)
        quad.p1.x = min_x
        quad.p1.y = max_y
        quad.p2.x = max_x
        quad.p2.y = max_y
        quad.p3.x = min_x
        quad.p3.y = min_y
        quad.p4.x = max_x
        quad.p4.y = min_y
        return quad

    def __fix_displaced_quadpoints(self, quad: QuadPoint, page: Page) -> QuadPoint:
        crop_box = page.GetCropBox()
        quad.p1.x -= crop_box.x1
        quad.p1.y -= crop_box.y1
        quad.p2.x -= crop_box.x1
        quad.p2.y -= crop_box.y1
        quad.p3.x -= crop_box.x1
        quad.p3.y -= crop_box.y1
        quad.p4.x -= crop_box.x1
        quad.p4.y -= crop_box.y1
        return quad

    def flip_quadpoint_vertically(self, quad: QuadPoint, page: Page) -> QuadPoint:
        page_height = page.GetPageHeight()
        quad.p1.y = page_height - quad.p1.y
        quad.p2.y = page_height - quad.p2.y
        quad.p3.y = page_height - quad.p3.y
        quad.p4.y = page_height - quad.p4.y
        return quad

    def get_page_height(self, page_number: int) -> float:
        page = self.__doc.GetPage(page_number)
        return page.GetPageHeight()

    def get_page_width(self, page_number: int) -> float:
        page = self.__doc.GetPage(page_number)
        return page.GetPageWidth()

    def __extract_covered_text_from_quads(
        self, page: Page, quads: list[QuadPoint], offset: OffsetDTO = DEFAULT_OFFSET
    ) -> str:

        covered_text_parts = [
            self.__extract_covered_text_from_rect(
                page, self.__get_rect_from_quad(quad), offset=offset
            )
            for quad in quads
        ]
        return " ".join(covered_text_parts)

    def __extract_covered_words_from_quads(
        self, page: Page, quads: list[QuadPoint], offset: OffsetDTO = DEFAULT_OFFSET
    ) -> list[Word]:
        covered_words_per_quad = [
            self.__extract_covered_words_from_rect(
                page, self.__get_rect_from_quad(quad), offset=offset
            )
            for quad in quads
        ]
        covered_words = flatten_list(covered_words_per_quad)
        return covered_words

    def __extract_covered_text_from_rect(
        self,
        page: Page,
        rect: Rect,
        offset: OffsetDTO = DEFAULT_OFFSET,
    ) -> str:
        rect = self.__apply_offset_to_rect(rect, offset)
        text_extractor = TextExtractor()
        text_extractor.Begin(page, rect)
        text = text_extractor.GetAsText(dehyphen=False).strip("\n")
        return text

    def __extract_covered_words_from_rect(
        self,
        page: Page,
        rect: Rect,
        offset: OffsetDTO = DEFAULT_OFFSET,
    ) -> list[Word]:
        words = []
        rect = self.__apply_offset_to_rect(rect, offset)
        text_extractor = TextExtractor()
        text_extractor.Begin(page, rect)
        line = text_extractor.GetFirstLine()
        while line.IsValid():
            if line.GetNumWords() == 0:
                line = line.GetNextLine()
                continue
            word = line.GetFirstWord()
            while word.IsValid():
                word_length = word.GetStringLen()
                if word_length > 0:
                    words.append(word)
                word = word.GetNextWord()
            line = line.GetNextLine()
        return words

    def __apply_offset_to_rect(self, rect: Rect, offset: OffsetDTO) -> Rect:
        return Rect(
            rect.x1 + offset.left,
            rect.y1 + offset.top,
            rect.x2 - offset.right,
            rect.y2 - offset.bottom,
        )

    def __remove_elements_from_page_matching_rect(self, page: Page, rect: Rect) -> Page:
        # Implementar aqui la eliminación de elementos de la página que coincidan con el rectángulo.
        return page

    def __get_quads_index_closer_to_reference_quads(
        self, quads_list: list[list[QuadPoint]], reference_quads: list[QuadPoint]
    ) -> int:
        min_distance = float("inf")
        min_index = 0
        for i, quads in enumerate(quads_list):
            distance = min(
                [
                    self.__compute_quadpoints_distance(quad_point, reference_quad_point)
                    for quad_point, reference_quad_point in zip(quads, reference_quads)
                ]
            )
            if distance < min_distance:
                min_distance = distance
                min_index = i
        return min_index

    def __compute_quadpoints_distance(
        self, quad_point: QuadPoint, reference_quad_point: QuadPoint
    ) -> float:
        return sqrt(
            self.__compute_quadpoints_vertical_distance(
                quad_point, reference_quad_point
            )
            ** 2
            + self.__compute_quadpoints_horizontal_distance(
                quad_point, reference_quad_point
            )
            ** 2
        )

    def __compute_quadpoints_vertical_distance(
        self, quad_point: QuadPoint, reference_quad_point: QuadPoint
    ) -> float:
        return min(
            [
                abs(quad_point.p1.y - reference_quad_point.p3.y),
                abs(quad_point.p3.y - reference_quad_point.p1.y),
            ]
        )

    def __compute_quadpoints_horizontal_distance(
        self, quad_point: QuadPoint, reference_quad_point: QuadPoint
    ) -> float:
        return min(
            [
                abs(quad_point.p1.x - reference_quad_point.p3.x),
                abs(quad_point.p3.x - reference_quad_point.p1.x),
            ]
        )

    def __iterate_pages(
        self,
        function: Callable[[Page, int, PDFDoc], Page],
        output_path: Optional[Path] = None,
        shall_save_file: bool = False,
    ) -> None:
        doc = self.__doc
        page_num = 0
        itr = doc.GetPageIterator()
        while itr.HasNext():
            page_num += 1
            page = itr.Current()
            page = function(page, page_num, doc)
            itr.Next()
        if shall_save_file:
            output_path = output_path or self.__filepath
            doc.Save(str(output_path), doc.e_verified)

    def __iterate_annotations(
        self,
        function: Callable[[Annot, Page, int], Page],
        output_path: Optional[Path] = None,
        shall_save_file: bool = False,
    ) -> None:
        try:
            doc = self.__doc
        except Exception as e:
            raise InvalidOrCorruptedFile(
                f"Could not open the file '{self.__filepath.name}' as PDF. Details: {e}"
            )
        page_num = 0
        itr = doc.GetPageIterator()
        while itr.HasNext():
            page_num += 1
            page = itr.Current()
            num_annots = page.GetNumAnnots()
            i = 0
            while i < num_annots:
                annot = page.GetAnnot(i)
                page = function(annot, page, page_num)
                i += 1
            itr.Next()
        if shall_save_file:
            output_path = output_path or self.__filepath
            doc.Save(str(output_path), doc.e_verified)

    def __get_rect_from_quad(self, quad: QuadPoint) -> Rect:
        x0 = min(quad.p1.x, quad.p2.x, quad.p3.x, quad.p4.x)
        y0 = min(quad.p1.y, quad.p2.y, quad.p3.y, quad.p4.y)
        x1 = max(quad.p1.x, quad.p2.x, quad.p3.x, quad.p4.x)
        y1 = max(quad.p1.y, quad.p2.y, quad.p3.y, quad.p4.y)
        return Rect(x0, y0, x1, y1)
