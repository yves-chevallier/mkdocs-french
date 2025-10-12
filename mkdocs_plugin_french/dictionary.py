from __future__ import annotations

import csv
import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.error import URLError, HTTPError
from urllib.request import urlretrieve

from .utils.text import strip_accents

log = logging.getLogger("mkdocs.plugins.fr_typo")

LEXIQUE_URL = "http://www.lexique.org/databases/Lexique383/Lexique383.zip"
CACHE_DIR = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache")) / "mkdocs_french"
MAP_FILENAME = "lexique_map.json"
ZIP_FILENAME = "Lexique383.zip"

FALLBACK_WORDS = {
    "ÇA",
    "ÉCOLE",
    "ÉTÉ",
    "ÉLÈVE",
    "FRANÇAIS",
    "GARÇON",
    "LEÇON",
    "MAÇON",
    "SOUPÇON",
    "CITÉ",
    "PIQÛRE",
    "COÛT",
    "NOËL",
    "AÎNÉ",
    "DÉJÀ",
    "PÂQUES",
    "PÂTÉ",
    "RÔLE",
}


def _build_fallback_map() -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for word in FALLBACK_WORDS:
        key = strip_accents(word).upper()
        mapping.setdefault(key, []).append(word)
    return mapping


class Dictionary:
    def __init__(self) -> None:
        self._map: Optional[Dict[str, List[str]]] = None
        self._ready: bool = False
        self._fallback_map = _build_fallback_map()

    def accentize(self, word: str) -> Optional[str]:
        mapping = self._load()
        if not mapping:
            return None
        key = strip_accents(word).upper()
        fallback_candidates = self._fallback_map.get(key)
        if fallback_candidates:
            return self._choose_candidate(fallback_candidates, word)
        if key in AMBIGUOUS_KEYS:
            return None
        candidates = mapping.get(key)
        if not candidates:
            return None
        unique_candidates: List[str] = []
        seen_lower = set()
        for cand in candidates:
            lower = cand.lower()
            if lower in seen_lower:
                continue
            seen_lower.add(lower)
            unique_candidates.append(cand)
        if len(unique_candidates) != 1:
            return None
        return self._choose_candidate(unique_candidates, word)

    # -- internals -----------------------------------------------------

    def _load(self) -> Dict[str, List[str]]:
        if self._map is not None:
            return self._map

        cache_file = CACHE_DIR / MAP_FILENAME
        if cache_file.exists():
            try:
                with cache_file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    self._map = {k: list(v) for k, v in data.items()}
                    return self._map
            except json.JSONDecodeError:
                log.warning("Lexique cache corrompu, reconstruction…")

        self._map = self._build_from_source(cache_file)
        return self._map

    def _build_from_source(self, cache_file: Path) -> Dict[str, List[str]]:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except PermissionError as exc:
            log.warning("Impossible de créer le cache Lexique (mode secours) : %s", exc)
            return _build_fallback_map()
        zip_path = CACHE_DIR / ZIP_FILENAME

        mapping: Dict[str, List[str]] = {}
        try:
            if not zip_path.exists():
                log.info("Téléchargement du dictionnaire Lexique383…")
                urlretrieve(LEXIQUE_URL, zip_path)
            with zipfile.ZipFile(zip_path, "r") as archive:
                tsv_name = next(
                    (name for name in archive.namelist() if name.lower().endswith(".tsv")),
                    None,
                )
                if not tsv_name:
                    raise FileNotFoundError("Fichier TSV introuvable dans Lexique383.zip")
                with archive.open(tsv_name) as raw:
                    text = raw.read().decode("utf-8")
        except (URLError, HTTPError, FileNotFoundError, zipfile.BadZipFile) as exc:
            log.warning("Impossible de préparer le dictionnaire Lexique (mode secours) : %s", exc)
            mapping = _build_fallback_map()
            self._save_cache(cache_file, mapping)
            return mapping

        reader = csv.DictReader(text.splitlines(), delimiter="\t")
        for row in reader:
            ortho = row.get("ortho")
            if not ortho:
                continue
            if strip_accents(ortho) == ortho:
                continue  # pas de diacritique à apprendre
            key = strip_accents(ortho).upper()
            mapping.setdefault(key, [])
            if ortho not in mapping[key]:
                mapping[key].append(ortho)

        if not mapping:
            mapping = _build_fallback_map()

        self._save_cache(cache_file, mapping)
        return mapping

    @staticmethod
    def _save_cache(cache_file: Path, mapping: Dict[str, List[str]]) -> None:
        try:
            with cache_file.open("w", encoding="utf-8") as fh:
                json.dump(mapping, fh, ensure_ascii=False)
        except (OSError, PermissionError) as exc:
            log.debug("Impossible d'écrire le cache Lexique : %s", exc)

    @staticmethod
    def _choose_candidate(candidates: List[str], original: str) -> str:
        if original.isupper():
            for cand in candidates:
                if cand.isupper():
                    return cand
            return candidates[0].upper()

        if original[0].isupper() and original[1:].islower():
            for cand in candidates:
                if cand[0].isupper():
                    return cand
            return candidates[0].capitalize()

        for cand in candidates:
            if cand.islower():
                return cand
        return candidates[0]


dictionary = Dictionary()
AMBIGUOUS_KEYS = {
    "LE",
    "LA",
    "LES",
    "DES",
    "DE",
    "DU",
    "A",
    "AU",
    "AUX",
    "ET",
    "OU",
    "SUR",
    "EST",
    "SON",
    "SES",
    "NOS",
    "VOS",
    "PLUS",
}
