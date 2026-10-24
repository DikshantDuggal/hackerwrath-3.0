"""
EdgeRunner Guardian Asset and Model Storage Manager.
Provides disk-efficient asset retrieval, HatchZip in-place extraction integration,
integrity checksum verification, atomic directory promotion, and fallback mechanisms.

Adheres strictly to the storage policy of keeping C: drive free by placing model
caches, vector stores, and dataset archives onto the D: drive.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("edgerunner.asset_manager")

# Default paths favoring D: drive to protect C: drive space
def get_default_models_dir() -> Path:
    env_dir = os.getenv("EDGERUNNER_MODELS_DIR")
    if env_dir:
        return Path(env_dir)
    d_drive = Path("D:/edgerunner_models")
    if d_drive.drive.upper() == "D:" and Path("D:/").exists():
        return d_drive
    # Fallback to backend/models
    return Path(__file__).resolve().parent.parent / "models"


@dataclass
class AssetManifestEntry:
    asset_id: str
    name: str
    version: str
    size_mb: float
    sha256: str
    archive_format: str  # "zip", "tar", "joblib", "raw"
    relative_target_path: str
    download_url: Optional[str] = None
    description: str = ""
    is_critical: bool = False


class AssetManager:
    """
    Manages downloading, checksum verification, HatchZip in-place archive extraction,
    and storage organization for large multilingual models and datasets.
    """

    def __init__(self, base_models_dir: Optional[Path] = None) -> None:
        self.base_dir = base_models_dir or get_default_models_dir()
        self.manifest_path = self.base_dir / "models_manifest.json"
        self._ensure_storage_environment()

    def _ensure_storage_environment(self) -> None:
        """Configures environment variables for HuggingFace, PyTorch, and cache locations on D: drive."""
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            hf_cache = self.base_dir / "huggingface"
            torch_cache = self.base_dir / "torch"
            hf_cache.mkdir(parents=True, exist_ok=True)
            torch_cache.mkdir(parents=True, exist_ok=True)

            os.environ.setdefault("HF_HOME", str(hf_cache))
            os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_cache / "hub"))
            os.environ.setdefault("TORCH_HOME", str(torch_cache))
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        except Exception as exc:
            logger.warning(f"Could not initialize model cache directories at {self.base_dir}: {exc}")

    @staticmethod
    def calculate_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
        """Computes SHA-256 hash in streaming chunks to avoid memory spikes."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    def is_hatchzip_available(self) -> bool:
        """Checks if the HatchZip binary is installed and executable on the host system."""
        hatchzip_bin = shutil.which("hatchzip")
        return hatchzip_bin is not None

    def extract_archive_inplace(self, archive_path: Path, destination_dir: Path) -> bool:
        """
        Extracts an archive in-place to avoid 2x disk bloat.
        Uses HatchZip (https://github.com/xevrion/hatchzip) when available, which extracts
        from tail-to-head and progressively truncates the archive, freeing disk space during extraction.
        Falls back to standard streaming extraction if HatchZip is not installed.
        """
        destination_dir.mkdir(parents=True, exist_ok=True)

        if self.is_hatchzip_available():
            logger.info(f"Using HatchZip in-place extraction for {archive_path.name} -> {destination_dir}")
            try:
                # HatchZip CLI syntax: hatchzip unpack <archive> <dest>
                result = subprocess.run(
                    ["hatchzip", "unpack", str(archive_path), str(destination_dir)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info(f"HatchZip extraction succeeded: {result.stdout.strip()}")
                return True
            except Exception as exc:
                logger.warning(f"HatchZip execution failed ({exc}); falling back to standard extraction.")

        # Fallback: Standard Python zipfile streaming extraction
        logger.info(f"Extracting {archive_path.name} via standard zipfile...")
        temp_dir = destination_dir.parent / f"{destination_dir.name}.extracting"
        try:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(temp_dir)

            # Atomic promotion
            if destination_dir.exists():
                shutil.rmtree(destination_dir)
            temp_dir.rename(destination_dir)

            # Delete the archive to reclaim space
            if archive_path.exists():
                archive_path.unlink()
            return True
        except Exception as exc:
            logger.error(f"Archive extraction failed for {archive_path}: {exc}")
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False

    def verify_asset(self, entry: AssetManifestEntry) -> bool:
        """Verifies if an asset exists and passes SHA-256 integrity checks."""
        target_path = self.base_dir / entry.relative_target_path
        if not target_path.exists():
            return False

        if target_path.is_file() and entry.sha256:
            actual_hash = self.calculate_sha256(target_path)
            return actual_hash.lower() == entry.sha256.lower()

        # For directories, check existence of required internal model weights
        if target_path.is_dir():
            has_files = any(target_path.iterdir())
            return has_files

        return True

    def get_asset_status(self) -> Dict[str, Any]:
        """Returns the readiness status of all registered model and dataset assets."""
        manifest = self.load_manifest()
        status_report = {}
        for asset_id, entry in manifest.items():
            ready = self.verify_asset(entry)
            status_report[asset_id] = {
                "name": entry.name,
                "version": entry.version,
                "size_mb": entry.size_mb,
                "ready": ready,
                "is_critical": entry.is_critical,
                "location": str(self.base_dir / entry.relative_target_path),
            }
        return status_report

    def load_manifest(self) -> Dict[str, AssetManifestEntry]:
        """Loads or creates the asset manifest."""
        default_manifest: Dict[str, AssetManifestEntry] = {
            "icfd_classifier_calibrated": AssetManifestEntry(
                asset_id="icfd_classifier_calibrated",
                name="ICFD-31k Calibrated Classifier Head",
                version="1.0.0",
                size_mb=4.2,
                sha256="",
                archive_format="joblib",
                relative_target_path="icfd_classifier/icfd_calibrated_model.joblib",
                description="Trained and calibrated sigmoid classifier head for multilingual scam detection",
                is_critical=True,
            ),
            "rag_tfidf_baseline": AssetManifestEntry(
                asset_id="rag_tfidf_baseline",
                name="RAG Corpus TF-IDF Baseline",
                version="1.0.0",
                size_mb=12.5,
                sha256="",
                archive_format="joblib",
                relative_target_path="vector_store/tfidf_logistic_baseline.joblib",
                description="Fast offline TF-IDF logistic baseline for Hindi/Punjabi/English scam corpus",
                is_critical=True,
            ),
            "minilm_multilingual_embedder": AssetManifestEntry(
                asset_id="minilm_multilingual_embedder",
                name="Sentence-Transformers MiniLM L6 v2",
                version="2.0",
                size_mb=120.0,
                sha256="",
                archive_format="raw",
                relative_target_path="huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2",
                description="Dense sentence embedding model for semantic scam retrieval",
                is_critical=False,
            ),
        }

        if not self.manifest_path.exists():
            try:
                manifest_dict = {k: asdict(v) for k, v in default_manifest.items()}
                with open(self.manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest_dict, f, indent=2)
            except Exception as exc:
                logger.warning(f"Could not persist default manifest to {self.manifest_path}: {exc}")
            return default_manifest

        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {k: AssetManifestEntry(**v) for k, v in data.items()}
        except Exception as exc:
            logger.error(f"Error reading manifest from {self.manifest_path}: {exc}")
            return default_manifest


_default_asset_manager: Optional[AssetManager] = None


def get_asset_manager() -> AssetManager:
    global _default_asset_manager
    if _default_asset_manager is None:
        _default_asset_manager = AssetManager()
    return _default_asset_manager
