from __future__ import annotations

import logging
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

import requests
import unicodedata
import xml.etree.ElementTree as ET
from functools import lru_cache

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


@lru_cache(maxsize=8192)
def _strip_diacritics_cached(s: str) -> str:
    """Version mise en cache de la suppression des diacritiques."""
    normalized = unicodedata.normalize("NFD", s)
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", stripped)


class Dictionary:
    """
    Accès simplifié à Morphalou avec corrections ligatures et diacritiques.

    Usage :
        dictionary = Dictionary()
        dictionary.prepare()  # optionnel, déclenché automatiquement à la première requête
        dictionary.ligaturize("Oedipe")  # -> "Œdipe"
        dictionary.accentize("evaluation")  # -> "évaluation"
    """

    def __init__(
        self,
        workdir: Optional[Path] = None,
        session: Optional[requests.Session] = None,
        timeout: int = 60,
    ) -> None:
        self.workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="morphalou_"))
        self.session = session or requests.Session()
        self.timeout = timeout
        self.zip_path: Optional[Path] = None
        self.extract_dir: Optional[Path] = None
        self.words: Set[str] = set(FALLBACK_WORDS)
        self._clean_after = workdir is None
        self._ligature_map: Dict[str, str] = {}
        self._accent_map: Dict[str, Tuple[str, ...]] = {}
        self._prepared = False
        self._prepare_attempted = False
        self._build_indexes()

    # ------------------ Cycle de préparation ------------------

    def prepare(self) -> None:
        """Pipeline complet : télécharge, extrait, parse, construit les index."""
        self._prepare_attempted = True
        try:
            self._download_latest_zip()
            self._extract_zip()
            self._parse_all_xml()
        except Exception as exc:  # pragma: no cover - dépend du réseau/environnement
            log.warning("Impossible de préparer Morphalou (mode secours) : %s", exc)
            self.words = set(FALLBACK_WORDS)
            self._build_indexes()
            return

        # enrichit avec le fallback pour conserver quelques mots sûrs
        self.words.update(FALLBACK_WORDS)
        self._build_indexes()
        self._prepared = True

    def _download_latest_zip(self) -> Path:
        """
        Récupère la page de 'latest/', trouve le meilleur ZIP TEI et le télécharge.
        """
        self.workdir.mkdir(parents=True, exist_ok=True)
        resp = self.session.get(LISTING_URL, timeout=self.timeout)
        resp.raise_for_status()
        hrefs = re.findall(r'href="([^"]+)"', resp.text, flags=re.IGNORECASE)

        tei_candidates = [h for h in hrefs if ZIP_PATTERN.search(Path(h).name)]
        if not tei_candidates:
            raise RuntimeError("Aucun fichier 'Morphalou*formatTEI*.zip' trouvé dans 'latest/'.")

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

    def _extract_zip(self) -> Path:
        """Extrait l’archive TEI.zip dans un sous-dossier."""
        if not self.zip_path:
            raise RuntimeError("Aucun ZIP à extraire. Appelez d'abord prepare().")
        extract_dir = self.workdir / "tei_extracted"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(self.zip_path, "r") as archive:
            archive.extractall(extract_dir)
        self.extract_dir = extract_dir
        return extract_dir

    def _parse_all_xml(self) -> None:
        """Collecte les graphies Morphalou et alimente self.words."""
        if not self.extract_dir:
            raise RuntimeError("Aucun dossier extrait. Appelez prepare() d'abord.")

        xml_files = list(self.extract_dir.rglob("*.xml"))
        words: Set[str] = set()

        for xml_path in xml_files:
            try:
                for _event, elem in ET.iterparse(str(xml_path), events=("end",)):
                    tag = self._strip_ns(elem.tag)
                    if tag in {"orth", "orthography"} and elem.text and elem.text.strip():
                        words.add(elem.text.strip())

                    if tag in {"form", "orthogr"}:
                        for attr in ("orth", "lemma", "entry", "writtenForm"):
                            value = elem.attrib.get(attr)
                            if value and value.strip():
                                words.add(value.strip())
                        for child in elem:
                            ctag = self._strip_ns(child.tag)
                            if ctag in {"orth", "orthography"} and child.text and child.text.strip():
                                words.add(child.text.strip())
            except ET.ParseError:
                continue

        words = {w for w in words if self._is_potential_word(w)}

        self.words = words
        self._ligature_map.clear()
        self._accent_map.clear()

    # ------------------ Accès publics ------------------

    def ligaturize(self, word: str) -> str:
        """Corrige les ligatures 'oe/ae' en respectant la casse initiale."""
        if not word:
            return word
        self._ensure_ready()
        key = self.normaliser_ascii(word).lower()
        candidate = self._ligature_map.get(key)
        if not candidate:
            return word
        return self._apply_casing(word, candidate)

    def accentize(self, word: str) -> str:
        """
        Corrige les diacritiques lorsqu'une seule variante Morphalou est compatible.
        En cas d'ambiguïté, on renvoie le mot d'origine.
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
            variant for variant in accent_only if self._is_compatible_with_existing_diacritics(lower_word, variant)
        ]
        if len(filtered) != 1:
            return word

        return self._apply_casing(word, filtered[0])

    def contains(self, fragment: str) -> Tuple[str, ...]:
        """Renvoie les mots contenant le fragment (utilisé pour diagnostics)."""
        if not fragment:
            return ()
        self._ensure_ready()
        fragment_lower = fragment.lower()
        results = {word for word in self.words if fragment_lower in word.lower()}
        return tuple(sorted(results))

    def cleanup(self) -> None:
        """Supprime le répertoire de travail si la classe l’a créé."""
        if self._clean_after and self.workdir.exists():
            shutil.rmtree(self.workdir, ignore_errors=True)

    # ------------------ Construction des index ------------------

    def _build_indexes(self) -> None:
        """Construit les dictionnaires internes pour ligatures et diacritiques."""
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

        self._ligature_map = {key: sorted(values)[0] for key, values in ligature_candidates.items()}

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

    def _ensure_ready(self) -> None:
        if self._prepared:
            return
        if not self._prepare_attempted:
            try:
                self.prepare()
            except Exception as exc:  # pragma: no cover - sécurité supplémentaire
                log.debug("Préparation du dictionnaire échouée : %s", exc)
                self.words = set(FALLBACK_WORDS)
                self._build_indexes()

    @staticmethod
    def _strip_ns(tag: str) -> str:
        """Supprime l’éventuel namespace '{...}' des noms de balises."""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    @staticmethod
    def _is_potential_word(text: str) -> bool:
        """Filtre très permissif pour éliminer les chaînes clairement non lexicales."""
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
        """Remplace les ligatures par leurs digrammes ASCII (utile pour clés)."""
        return (
            text.replace("Œ", "OE")
            .replace("œ", "oe")
            .replace("Æ", "AE")
            .replace("æ", "ae")
        )

    @staticmethod
    def _contient_ligature(text: str) -> bool:
        """Vérifie la présence de ligatures œ/æ dans la chaîne."""
        return any(char in text for char in ("œ", "Œ", "æ", "Æ"))

    @staticmethod
    def _apply_casing(original: str, suggestion_lower: str) -> str:
        """Adapte la casse de la suggestion (attendue en minuscules) à celle de l'original."""
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
    def _is_compatible_with_existing_diacritics(original_lower: str, candidate_lower: str) -> bool:
        """Filtre les candidats qui respectent les diacritiques déjà présents."""
        if len(original_lower) != len(candidate_lower):
            return False
        for orig_char, cand_char in zip(original_lower, candidate_lower):
            if _strip_diacritics_cached(orig_char) != _strip_diacritics_cached(cand_char):
                return False
            if orig_char != _strip_diacritics_cached(orig_char) and orig_char != cand_char:
                return False
        return True

    def _get_accent_candidates(self, base: str) -> Tuple[str, ...]:
        """Récupère les candidats accentués pour une forme de base avec cache interne."""
        cached = self._accent_map.get(base)
        if cached is not None:
            return cached

        matches: Set[str] = set()
        ascii_present = False
        for word in self.words:
            lower_word = word.lower()
            if _strip_diacritics_cached(lower_word) != base:
                continue
            if lower_word == base:
                ascii_present = True
            else:
                matches.add(lower_word)

        if not matches and not ascii_present:
            self._accent_map[base] = ()
            return ()

        ordered = []
        if ascii_present:
            ordered.append(base)
        ordered.extend(sorted(matches))
        result = tuple(ordered)
        self._accent_map[base] = result
        return result


dictionary = Dictionary()
