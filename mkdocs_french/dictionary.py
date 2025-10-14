"""Morphalou-backed dictionary helpers for ligatures and diacritics."""

from __future__ import annotations

from functools import lru_cache
import gzip
import json
import logging
from pathlib import Path
import re
import shutil
import tempfile
from typing import Dict, Iterable, Optional, Set, Tuple
import unicodedata
import xml.etree.ElementTree as ET
import zipfile

import requests

from .artifacts import SCHEMA_VERSION, default_data_path


log = logging.getLogger("mkdocs.plugins.fr_typo")


LISTING_URL = "https://repository.ortolang.fr/api/content/morphalou/latest/"
ZIP_PATTERN = re.compile(r"^Morphalou.*formatTEI(?:_toutEnUn)?\.zip$", re.IGNORECASE)

FALLBACK_WORDS: Set[str] = {
    "cœur",
    "cœurs",
    "coeur",
    "coeurs",
    "œuvre",
    "œuvres",
    "oeuvre",
    "oeuvres",
    "æquo",
    "aequo",
    "fœtus",
    "foetus",
    "œil",
    "oeil",
    "œufs",
    "oeufs",
    "œuf",
    "oeuf",
    "œsophage",
    "oesophage",
    "œdipe",
    "oedipe",
    "œdème",
    "oedeme",
    "étalement",
    "ėtalement",
    "evaluer",
    "évaluation",
    "evaluation",
    "évaluations",
    "evaluations",
    "élève",
    "élèves",
    "élevé",
    "élevée",
    "élevés",
    "élevées",
    "eleve",
    "eleves",
    "noël",
    "noels",
    "noel",
    "école",
    "ecole",
    "français",
    "francais",
}


@lru_cache(maxsize=131072)
def _strip_diacritics_cached(s: str) -> str:
    """Strip diacritics from a string while caching results.

    Args:
        s: Input string whose diacritics should be removed.

    Returns:
        The normalized string free of combining marks.

    Examples:
        >>> from mkdocs_french.dictionary import _strip_diacritics_cached
        >>> _strip_diacritics_cached("Élévation")
        'Elevation'
    """
    normalized = unicodedata.normalize("NFD", s)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", stripped)


class Dictionary:
    """Provide ligature and diacritic helpers backed by Morphalou data.

    The dictionary downloads, extracts, and parses Morphalou lexicon data (or
    reuses a pre-generated artifact) to offer helpers that fix common French
    typography issues. Heavy preparation work is performed lazily at first use.

    Examples:
        >>> from mkdocs_french.dictionary import Dictionary
        >>> d = Dictionary(use_static_data=True)
        >>> d.ligaturize("Oedipe")  # doctest: +ELLIPSIS
        'Œdipe'
        >>> d.accentize("NOEL")  # doctest: +ELLIPSIS
        'NOËL'
    """

    def __init__(
        self,
        workdir: Optional[Path] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 60,
        use_static_data: bool = True,
        data_path: Optional[Path] = None,
    ) -> None:
        """Initialize the dictionary helpers.

        Args:
            workdir: Optional working directory used for downloads and caching.
                When omitted, a temporary directory is created automatically.
            session: Optional ``requests.Session`` to reuse HTTP connections.
            timeout: Timeout in seconds for Morphalou HTTP requests.
            use_static_data: Whether to load the bundled pre-processed artifact
                when available.
            data_path: Optional path pointing to the static artifact to load.
        """
        self.workdir = (
            Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="morphalou_"))
        )
        self.session = session or requests.Session()
        self.timeout = timeout
        self.use_static_data = use_static_data
        self._data_path = Path(data_path) if data_path else default_data_path()
        self.zip_path: Optional[Path] = None
        self.extract_dir: Optional[Path] = None
        self.words: Set[str] = set(FALLBACK_WORDS)
        self._clean_after = workdir is None
        self._ligature_map: Dict[str, str] = {}
        self._accent_map: Dict[str, Tuple[str, ...]] = {}
        self._prepared = False
        self._prepare_attempted = False

        if self.use_static_data and self._load_static_data():
            self._prepared = True
            self._prepare_attempted = True
        else:
            self._build_indexes()

    # ------------------ Preparation lifecycle ------------------

    def prepare(self) -> None:  # pragma: no cover - network dependent
        """Run the full Morphalou pipeline and build lookup indexes.

        The method tolerates network and parsing failures by logging the
        exception and falling back to the bundled minimal dataset.
        """
        self._prepare_attempted = True
        try:
            self._download_latest_zip()
            self._extract_zip()
            self._parse_all_xml()
        except Exception as exc:  # pragma: no cover - network/environment dependent
            log.warning("Impossible de préparer Morphalou (mode secours) : %s", exc)
            self.words = set(FALLBACK_WORDS)
            self._build_indexes()
            return

        # Merge fallback words to keep a safe baseline vocabulary
        self.words.update(FALLBACK_WORDS)
        self._build_indexes()
        self._prepared = True

    def _download_latest_zip(self) -> Path:  # pragma: no cover - network dependent
        """Download the most relevant TEI ZIP archive from ORTOLANG.

        Returns:
            Path to the downloaded ZIP file stored inside the working directory.
        """
        self.workdir.mkdir(parents=True, exist_ok=True)
        resp = self.session.get(LISTING_URL, timeout=self.timeout)
        resp.raise_for_status()
        hrefs = re.findall(r'href="([^"]+)"', resp.text, flags=re.IGNORECASE)

        tei_candidates = [h for h in hrefs if ZIP_PATTERN.search(Path(h).name)]
        if not tei_candidates:
            raise RuntimeError(
                "Aucun fichier 'Morphalou*formatTEI*.zip' trouvé dans 'latest/'."
            )

        def score(name: str) -> tuple[int, int, str]:
            lower = name.lower()
            return (
                0 if "_toutenun" in lower else 1,
                0 if "formattei" in lower else 1,
                name,
            )

        zip_name = sorted((Path(h).name for h in tei_candidates), key=score)[0]
        zip_url = LISTING_URL + zip_name

        out_path = self.workdir / zip_name
        with self.session.get(zip_url, stream=True, timeout=self.timeout) as response:
            response.raise_for_status()
            with open(out_path, "wb") as target:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        target.write(chunk)

        self.zip_path = out_path
        return out_path

    def _extract_zip(self) -> Path:  # pragma: no cover - network dependent
        """Extract the TEI archive into a dedicated folder.

        Returns:
            Path to the directory containing the extracted XML files.

        Raises:
            RuntimeError: If called before a ZIP archive has been downloaded.
        """
        if not self.zip_path:
            raise RuntimeError("Aucun ZIP à extraire. Appelez d'abord prepare().")
        extract_dir = self.workdir / "tei_extracted"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(self.zip_path, "r") as archive:
            archive.extractall(extract_dir)
        self.extract_dir = extract_dir
        return extract_dir

    def _parse_all_xml(self) -> None:  # pragma: no cover - heavy parsing
        """Parse every extracted XML file to populate the word list.

        This step extracts various orthography fields and adds them to
        :attr:`words`. Parsing errors are ignored to ensure resilience.
        """
        if not self.extract_dir:
            raise RuntimeError("Aucun dossier extrait. Appelez prepare() d'abord.")

        xml_files = list(self.extract_dir.rglob("*.xml"))
        words: Set[str] = set()

        for xml_path in xml_files:
            try:
                for _event, elem in ET.iterparse(str(xml_path), events=("end",)):
                    tag = self._strip_ns(elem.tag)
                    if (
                        tag in {"orth", "orthography"}
                        and elem.text
                        and elem.text.strip()
                    ):
                        words.add(elem.text.strip())

                    if tag in {"form", "orthogr"}:
                        for attr in ("orth", "lemma", "entry", "writtenForm"):
                            value = elem.attrib.get(attr)
                            if value and value.strip():
                                words.add(value.strip())
                        for child in elem:
                            ctag = self._strip_ns(child.tag)
                            if (
                                ctag in {"orth", "orthography"}
                                and child.text
                                and child.text.strip()
                            ):
                                words.add(child.text.strip())
            except ET.ParseError:
                continue

        words = {w for w in words if self._is_potential_word(w)}

        self.words = words
        self._ligature_map.clear()
        self._accent_map.clear()

    # ------------------ Public API ------------------

    def ligaturize(self, word: str) -> str:
        """Replace ``oe``/``ae`` digraphs by ligatures when possible.

        Args:
            word: Word to transform.

        Returns:
            The ligaturized word when a single candidate exists, otherwise the
            original input.
        """
        if not word:
            return word
        self._ensure_ready()
        key = self.normaliser_ascii(word).lower()
        candidate = self._ligature_map.get(key)
        if not candidate:
            return word
        return self._apply_casing(word, candidate)

    def accentize(self, word: str) -> str:
        """Add missing diacritics when Morphalou provides an unambiguous match.

        Args:
            word: Word to transform.

        Returns:
            The accentized word when exactly one compatible candidate exists;
            otherwise the original word.
        """
        if not word:
            return word
        self._ensure_ready()

        lower_word = word.lower()
        base = _strip_diacritics_cached(lower_word)
        candidates = self._get_accent_candidates(base)
        if not candidates:
            return word

        accent_only = [variant for variant in candidates if variant != base]
        if not accent_only:
            return word

        filtered = [
            variant
            for variant in accent_only
            if self._is_compatible_with_existing_diacritics(lower_word, variant)
        ]
        if len(filtered) != 1:
            return word

        return self._apply_casing(word, filtered[0])

    def contains(self, fragment: str) -> Tuple[str, ...]:
        """Return words containing the provided fragment (diagnostic helper).

        Args:
            fragment: Substring to search for within the dictionary.

        Returns:
            Sorted tuple of matching words.
        """
        if not fragment:
            return ()
        self._ensure_ready()
        fragment_lower = fragment.lower()
        results = {word for word in self.words if fragment_lower in word.lower()}
        return tuple(sorted(results))

    def cleanup(self) -> None:
        """Remove the working directory if it was created internally."""
        if self._clean_after and self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)

    # ------------------ Index construction ------------------

    def _build_indexes(self) -> None:
        """Populate internal indexes for ligature and accent handling.

        The method reads :attr:`words`, computes lookup maps, and stores the
        results in :attr:`_ligature_map` and :attr:`_accent_map`.
        """
        ligature_candidates: Dict[str, Set[str]] = {}
        accent_variants: Dict[str, Set[str]] = {}
        accent_ascii_present: Set[str] = set()

        for word in self.words:
            lower_word = word.lower()
            ascii_word = self.normaliser_ascii(lower_word)
            if self._contient_ligature(word):
                ligature_candidates.setdefault(ascii_word, set()).add(lower_word)

            base_no_diac = _strip_diacritics_cached(lower_word)
            if not base_no_diac:
                continue
            if lower_word != base_no_diac:
                accent_variants.setdefault(base_no_diac, set()).add(lower_word)
            else:
                accent_ascii_present.add(base_no_diac)
                accent_variants.setdefault(base_no_diac, set())

        self._ligature_map = {
            key: sorted(values)[0] for key, values in ligature_candidates.items()
        }

        accent_map: Dict[str, Tuple[str, ...]] = {}
        for base, variants in accent_variants.items():
            if not variants:
                continue
            ordered = []
            if base in accent_ascii_present:
                ordered.append(base)
            ordered.extend(sorted(variants))
            accent_map[base] = tuple(ordered)
        self._accent_map = accent_map

    # ------------------ Helpers ------------------

    def _load_static_data(self) -> bool:
        """Attempt to load the pre-generated indexes from disk.

        Returns:
            ``True`` when the static artifact was loaded successfully, ``False``
            otherwise.
        """
        log.info("Loading static dictionary data from '%s' ...", self._data_path)
        path = self._data_path
        if not path.exists():
            return False

        try:
            with gzip.open(path, "rb") as handle:
                payload = json.load(handle)
        except FileNotFoundError:
            return False
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Artéfact Morphalou illisible (%s) : %s", path, exc)
            return False

        if not isinstance(payload, dict):
            log.warning("Artéfact Morphalou invalide : structure inattendue.")
            return False

        version = payload.get("schema_version")
        if version == SCHEMA_VERSION:
            fast_path = payload.get("normalized", False)
        elif version == 1:
            log.info(
                "Artéfact Morphalou ancien (schema=1) détecté : chargement en mode compatibilité."
            )
            fast_path = False
        else:
            log.info(
                "Artéfact Morphalou incompatible (schema=%s, attendu=%s).",
                version,
                SCHEMA_VERSION,
            )
            return False

        words_field = payload.get("words")
        lig_field = payload.get("ligature_map", {})
        accent_field = payload.get("accent_map", {})

        if not isinstance(words_field, list):  # pragma: no cover - validation guard
            log.warning("Artéfact Morphalou invalide : 'words' doit être une liste.")
            return False
        if not isinstance(lig_field, dict):  # pragma: no cover - validation guard
            log.warning(
                "Artéfact Morphalou invalide : 'ligature_map' doit être un dict."
            )
            return False
        if not isinstance(accent_field, dict):  # pragma: no cover - validation guard
            log.warning("Artéfact Morphalou invalide : 'accent_map' doit être un dict.")
            return False

        if fast_path:
            log.info(
                "Static dictionary data flagged as normalized; using fast loading path."
            )
            words = {entry for entry in words_field if isinstance(entry, str)}
            ligature_map = {
                key: value
                for key, value in lig_field.items()
                if isinstance(key, str) and isinstance(value, str)
            }
            accent_map = {
                key: tuple(variants)
                for key, variants in accent_field.items()
                if isinstance(key, str) and isinstance(variants, list)
            }
        else:
            log.info("Processing %d french words from static data...", len(words_field))
            words = {
                item
                for entry in words_field
                if isinstance(entry, str)
                for item in (entry.strip(),)
                if item and self._is_potential_word(item)
            }

            ligature_map = {
                key: value
                for key, value in lig_field.items()
                if isinstance(key, str) and isinstance(value, str)
            }

            accent_map = {}
            for key, variants in accent_field.items():
                if not isinstance(key, str) or not isinstance(variants, list):
                    continue
                normalized = self._normalize_accent_entry(key, variants)
                if normalized:
                    accent_map[key] = normalized

        if not words:  # pragma: no cover - validation guard
            log.warning("Artéfact Morphalou invalide : aucune entrée exploitable.")
            return False

        log.info("Static dictionary data loaded successfully.")
        self.words = words.union(FALLBACK_WORDS)
        self._ligature_map = ligature_map
        self._accent_map = accent_map
        self._augment_indexes_with_fallbacks()

        log.info("Dictionary is ready for use.")
        return True

    def _ensure_ready(self) -> None:
        """Trigger preparation lazily when the indexes are not ready."""
        if self._prepared:
            return
        if not self._prepare_attempted:
            try:
                self.prepare()
            except Exception as exc:  # pragma: no cover - additional safety
                log.debug("Préparation du dictionnaire échouée : %s", exc)
                self.words = set(FALLBACK_WORDS)
                self._build_indexes()

    @staticmethod
    def _strip_ns(tag: str) -> str:
        """Strip an optional ``{namespace}`` prefix from XML tag names.

        Args:
            tag: Tag name possibly prefixed with a namespace.

        Returns:
            The tag name without the namespace portion.
        """
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    @staticmethod
    def _is_potential_word(text: str) -> bool:
        """Return whether a string looks like a valid lexical entry.

        Args:
            text: Raw text candidate to evaluate.

        Returns:
            ``True`` if the string could represent a word, ``False`` otherwise.
        """
        stripped = text.strip()
        if not stripped:
            return False
        if "\n" in stripped or "\r" in stripped:
            return False
        if len(stripped) > 64:
            return False
        return True

    @staticmethod
    def normaliser_ascii(text: str) -> str:
        """Replace ligatures with ASCII digraphs (useful for keys).

        Args:
            text: Input string possibly containing ligatures.

        Returns:
            The string where ``œ``/``æ`` are replaced with ``oe``/``ae``.
        """
        return (
            text.replace("Œ", "OE")
            .replace("œ", "oe")
            .replace("Æ", "AE")
            .replace("æ", "ae")
        )

    @staticmethod
    def _contient_ligature(text: str) -> bool:
        """Return whether the string contains œ/æ ligatures."""
        return any(char in text for char in ("œ", "Œ", "æ", "Æ"))

    @staticmethod
    def _apply_casing(original: str, suggestion_lower: str) -> str:
        """Adapt the lowercase suggestion casing to match the original string.

        Args:
            original: Original token whose casing should be mimicked.
            suggestion_lower: Suggested replacement in lowercase.

        Returns:
            The suggestion adjusted to match the casing of ``original``.
        """
        if not suggestion_lower:
            return suggestion_lower
        if original.isupper():
            return suggestion_lower.upper()
        if original.islower():
            return suggestion_lower
        if original[0].isupper() and original[1:].islower():
            return suggestion_lower[0].upper() + suggestion_lower[1:]
        if original[0].isupper():
            return suggestion_lower[0].upper() + suggestion_lower[1:]
        return suggestion_lower

    @staticmethod
    def _is_compatible_with_existing_diacritics(
        original_lower: str, candidate_lower: str
    ) -> bool:
        """Return whether a candidate respects existing diacritics.

        Args:
            original_lower: Lowercased source token.
            candidate_lower: Lowercased candidate token from Morphalou.

        Returns:
            ``True`` when the candidate matches the already present diacritics,
            ``False`` otherwise.
        """
        if len(original_lower) != len(candidate_lower):
            return False
        for orig_char, cand_char in zip(original_lower, candidate_lower):
            if _strip_diacritics_cached(orig_char) != _strip_diacritics_cached(
                cand_char
            ):
                return False
            if (
                orig_char != _strip_diacritics_cached(orig_char)
                and orig_char != cand_char
            ):
                return False
        return True

    def _get_accent_candidates(self, base: str) -> Tuple[str, ...]:
        """Retrieve accent candidates for a base form using the internal cache.

        Args:
            base: Normalized base form (without diacritics).

        Returns:
            Tuple of candidate strings; empty tuple when no candidates exist.
        """
        cached = self._accent_map.get(base)
        if cached is not None:
            return cached

        # Bases absent from the precomputed map have no accent variants.
        self._accent_map[base] = ()
        return ()

    def _augment_indexes_with_fallbacks(self) -> None:
        """Inject fallback words into ligature and diacritic indexes."""
        for word in FALLBACK_WORDS:
            lower_word = word.lower()
            ascii_word = self.normaliser_ascii(lower_word)
            if self._contient_ligature(word):
                self._ligature_map.setdefault(ascii_word, lower_word)

            base = _strip_diacritics_cached(lower_word)
            current = list(self._accent_map.get(base, ()))
            current.append(lower_word)
            self._accent_map[base] = self._normalize_accent_entry(base, current)

    @staticmethod
    def _normalize_accent_entry(base: str, variants: Iterable[str]) -> Tuple[str, ...]:
        """Sort accent variants (ASCII first) and remove duplicates.

        Args:
            base: Diacritic-free base form serving as the canonical reference.
            variants: Iterable of candidate variants including ASCII versions.

        Returns:
            Tuple of unique variants ordered with ASCII first and then alphabetically.
        """
        ascii_variants = []
        other_variants = []
        seen = set()

        for item in variants:
            if not isinstance(item, str):
                continue
            candidate = item.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if candidate == base:
                ascii_variants.append(candidate)
            else:
                other_variants.append(candidate)

        return tuple(ascii_variants + sorted(other_variants))


@lru_cache(maxsize=1)
def get_dictionary() -> "Dictionary":
    """Return a cached :class:`Dictionary` instance.

    Returns:
        Singleton dictionary created on first call.
    """

    return Dictionary()


__all__ = ["Dictionary", "get_dictionary"]
