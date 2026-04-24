from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DownloadResult:
    model_key: str
    output_dir: Path
    model_xml: Path | None
    commands: tuple[str, ...]


@dataclass(frozen=True)
class OmzModelSpec:
    name: str
    needs_conversion: bool


OMZ_MODELS: dict[str, OmzModelSpec] = {
    "image-classification": OmzModelSpec(
        name="mobilenet-v3-small-1.0-224-tf",
        needs_conversion=True,
    ),
    "object-detection": OmzModelSpec(
        name="person-detection-retail-0013",
        needs_conversion=False,
    ),
}


def download_model(key: str, output_dir: Path, convert: bool = True) -> DownloadResult:
    normalized = key.strip().lower()
    spec = OMZ_MODELS.get(normalized)
    if spec is None:
        available = ", ".join(sorted(OMZ_MODELS))
        raise ValueError(f"No downloader is configured for '{key}'. Available: {available}")
    model_name = spec.name

    downloader = shutil.which("omz_downloader")
    if downloader is None and not _can_import_omz_downloader():
        raise RuntimeError(
            "omz_downloader is not available. Install OpenVINO model tools or use an environment "
            "that provides Open Model Zoo tools, then try again."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    commands: list[str] = []

    download_args = [
        "--name",
        model_name,
        "--output_dir",
        str(output_dir),
    ]
    commands.append(_format_command(["omz_downloader", *download_args]))
    if downloader:
        _run([downloader, *download_args])
    else:
        _run_omz_downloader(download_args)

    model_xml: Path | None = None
    if convert and spec.needs_conversion:
        converter = shutil.which("omz_converter")
        if converter is None and not _can_import_omz_converter():
            raise RuntimeError(
                "Downloaded the model, but omz_converter is not available. Install OpenVINO model "
                "tools to convert public models to OpenVINO IR."
            )

        convert_args = [
            "--name",
            model_name,
            "--download_dir",
            str(output_dir),
            "--output_dir",
            str(output_dir),
        ]
        commands.append(_format_command(["omz_converter", *convert_args]))
        if converter:
            _run([converter, *convert_args])
        else:
            _run_omz_converter(convert_args)
        model_xml = _find_model_xml(output_dir, model_name)

    if model_xml is None:
        model_xml = _find_model_xml(output_dir, model_name)

    return DownloadResult(
        model_key=normalized,
        output_dir=output_dir,
        model_xml=model_xml,
        commands=tuple(commands),
    )


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, check=False, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {completed.returncode}: {_format_command(command)}")


def _run_omz_downloader(args: list[str]) -> None:
    from omz_tools.omz_downloader import download

    _run_omz_function("omz_downloader", download, args)


def _run_omz_converter(args: list[str]) -> None:
    from omz_tools.omz_converter import converter

    _run_omz_function("omz_converter", converter, args)


def _run_omz_function(name: str, function: object, args: list[str]) -> None:
    try:
        function(args)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code != 0:
            raise RuntimeError(f"{name} failed with exit code {code}") from exc


def _can_import_omz_downloader() -> bool:
    try:
        import omz_tools.omz_downloader  # noqa: F401

        return True
    except Exception:
        return False


def _can_import_omz_converter() -> bool:
    try:
        import omz_tools.omz_converter  # noqa: F401

        return True
    except Exception:
        return False


def _find_model_xml(output_dir: Path, model_name: str) -> Path | None:
    matches = sorted(output_dir.rglob(f"{model_name}.xml"))
    return matches[0] if matches else None


def _format_command(command: list[str]) -> str:
    return " ".join(command)
