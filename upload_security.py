"""The checks the /upload endpoint runs before it keeps a file.

Kept apart from api.py so the limits, and the order they are applied in, read as one list
rather than as scattered conditions inside the endpoint.
"""

import re
import socket
import struct
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile
from starlette.concurrency import run_in_threadpool


# Only the two cooler containers, because nothing else can be read back out of the data folder.
# A broader list would only ever mean storing something that is later parsed by mistake.
ALLOWED_SUFFIXES = (".cool", ".mcool")

# A cooler file is an HDF5 file, whose first eight bytes are fixed. Checking them says what the
# bytes actually are, which the Content-Type the caller put in the request does not: a file
# labelled `application/octet-stream` can hold anything, and the label costs nothing to forge.
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"

# The name ends up in a file path, in a URL, and in the group listings on disk, so it stays
# inside the set that survives all three without quoting. No slashes, no spaces, no unicode,
# and the first character has to be a letter or a digit, which rules out a hidden `.file`.
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

# Windows hands these names to devices instead of files, extension or none.
RESERVED_WINDOWS_STEMS = {
    "con", "prn", "aux", "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}

# Stored under a name like `dataset.exe.mcool` the file is still a cooler file and still gets
# rejected or accepted on its own bytes, but the name is then what a browser offers to run or
# render once someone downloads it back out of the data folder.
DANGEROUS_STEM_SUFFIXES = (
    ".exe", ".dll", ".com", ".msi", ".pif", ".scr", ".bat", ".cmd", ".ps1", ".vbs", ".jar",
    ".lnk", ".js", ".html", ".htm", ".svg", ".xml", ".php", ".cgi", ".wsf",
)

# Sent by the app's own client, which a cross-site form cannot do. Requiring it is what turns
# "nobody can forge this request" from a hope into a rule the browser enforces.
CSRF_HEADER = "x-requested-with"
CSRF_HEADER_VALUE = "chromograph"

CHUNK_SIZE = 1024 * 1024
CLAMD_CHUNK_SIZE = 32 * 1024

# An upload is written here first and only moved into place once it passed every check. The name
# doubles as the marker the startup sweep looks for, so a transfer interrupted by a crash or a
# restart does not leave a file the size of the upload limit sitting in the data folder.
STAGING_PREFIX = ".upload-"
STAGING_SUFFIX = ".part"


def staging_path(directory: str | Path) -> Path:
    """A not-yet-used staging path inside `directory`."""
    return Path(directory) / f"{STAGING_PREFIX}{uuid4().hex}{STAGING_SUFFIX}"


def discard_stale_uploads(directories: Iterable[str | Path]) -> None:
    """Delete staging files left behind by uploads that never finished.

    Called at startup, while no upload can be in flight, so there is nothing here that belongs
    to a transfer still arriving.
    """
    for entry in directories:
        directory = Path(entry)
        if not directory.is_dir():
            continue
        for leftover in directory.glob(f"{STAGING_PREFIX}*{STAGING_SUFFIX}"):
            try:
                leftover.unlink(missing_ok=True)
            except OSError as error:
                print(f"Could not remove interrupted upload {leftover}: {error}")


def check_upload_request(request: Request, allowed_origins: list[str]) -> None:
    """Refuse an upload that did not arrive from the app's own client.

    The passcode travels as an Authorization header rather than a cookie, so a foreign page
    cannot ride out somebody's session — but it can still submit an ordinary form here and
    store a file anonymously, so the request itself has to be recognised instead. A browser
    always describes how a request was made: a form submission or a `no-cors` fetch arrives
    with a `Sec-Fetch-Mode` that is not `cors`, and neither can carry a custom header.

    Stopping a forged request is what this buys, which is the whole of the threat here: the
    passcode is a header rather than a cookie, so there is no session for a foreign page to
    ride, and what it can do is build a request of its own. That last case is the CORS
    middleware's to refuse, and the origin list below refuses it again from inside the endpoint,
    so an upload from a site the operator never listed fails even if CORS was set broadly.
    """
    headers = request.headers
    sec_fetch_mode = headers.get("sec-fetch-mode")
    if sec_fetch_mode is not None and sec_fetch_mode.lower() != "cors":
        raise HTTPException(
            status_code=403,
            detail="The upload did not come from the application, so it was not accepted.",
        )

    origin = headers.get("origin")
    if origin is None:
        # No origin is a script rather than a page — curl, a notebook, a deployment's own
        # tooling — which is how this endpoint is used outside a browser.
        return
    if _is_same_origin(origin, headers.get("host")):
        # A request aimed at this very service, which is what the docs page at /docs sends and
        # what a front end served from the same host sends. Cross-site is the case to guard.
        return
    if (headers.get(CSRF_HEADER) or "").lower() != CSRF_HEADER_VALUE:
        raise HTTPException(
            status_code=403,
            detail="The upload request is missing the header the application sends with it.",
        )

    # Empty means the operator has not listed any origins, which leaves the header above as the
    # only origin rule; a single `*` is the explicit way to accept every site.
    patterns = [pattern.lower() for pattern in allowed_origins]
    if not patterns or "*" in patterns:
        return
    if not _matches_any(origin.lower(), patterns):
        raise HTTPException(
            status_code=403,
            detail=f"Uploads are not accepted from {origin}.",
        )


def _is_same_origin(origin: str, host: str | None) -> bool:
    """Whether an Origin header names this very service, comparing only the address."""
    if not host:
        return False
    address = origin.split("://", 1)[-1].rstrip("/")
    return address.lower() == host.lower()


def _matches_any(value: str, patterns: list[str]) -> bool:
    """Match an origin against `*` wildcards, so `http://localhost:*` covers every dev port.

    A `*` covers part of an address but never a `/`, which keeps a host from being smuggled in
    behind a path — `https://*.example.com` must not admit `https://evil.com/!.example.com`.
    """
    for pattern in patterns:
        if pattern == value:
            return True
        if "*" not in pattern:
            continue
        expression = "[^/]*".join(re.escape(segment) for segment in pattern.split("*"))
        if re.fullmatch(expression, value):
            return True
    return False


def safe_upload_name(raw_name: str | None, max_length: int) -> tuple[str, str]:
    """Reduce whatever the caller called the file to a (stem, suffix) that is safe to store.

    Runs before the extension is looked at on purpose: the name is first proven to be an ordinary
    filename, and only then read for its extension, so a name that only turns into `x.mcool` once
    slashes or NUL bytes are stripped never reaches the check that would have approved it.
    """
    name = (raw_name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="The upload did not say what file it is.")

    # Safari and some non-browser clients send a whole path, with either separator.
    name = name.replace("\\", "/").rsplit("/", 1)[-1]

    if len(name) > max_length:
        raise HTTPException(status_code=400, detail=f"The file name may be at most {max_length} characters.")
    if not SAFE_NAME.fullmatch(name):
        raise HTTPException(
            status_code=400,
            detail="The file name may only contain letters, numbers, dots, dashes and underscores, and has to start with a letter or a number.",
        )

    stem, suffix = Path(name).stem, Path(name).suffix.lower()
    if not stem or suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .cool and .mcool files can be uploaded.")
    # The charset above already leaves `..` and a leading dot unreachable; checked again so a
    # future widening of the charset cannot silently reopen the path traversal.
    if ".." in name or stem.lower() in RESERVED_WINDOWS_STEMS or stem.endswith((".", "-")):
        raise HTTPException(status_code=400, detail=f"The file name {name} cannot be stored.")
    if stem.lower().endswith(DANGEROUS_STEM_SUFFIXES):
        raise HTTPException(status_code=400, detail=f"A cooler file cannot be named {name}.")

    return stem, suffix


def check_declared_size(raw_content_length: str | None, max_bytes: int) -> None:
    """Turn a caller away before a single byte of an obviously oversized file arrives.

    The header is the caller's own claim about the body and may be wrong, absent on a chunked
    transfer, or lower than what follows, so store_upload counts the bytes as they land and
    treats this only as an early exit.
    """
    try:
        declared = int(raw_content_length)
    except (TypeError, ValueError):
        return
    if declared > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"The file is said to be {declared} bytes, over this server's limit of {max_bytes} bytes.",
        )


async def store_upload(file: UploadFile, staging: Path, max_bytes: int) -> None:
    """Write the upload to `staging`, refusing it as soon as it stops being a plausible cooler.

    Both the size cap and the format check cut the transfer short rather than finishing it
    first: a file that is twice the limit, or is not HDF5 at all, is known within the first
    megabyte. The caller removes `staging` whatever happens.
    """
    written = 0
    pending = b""
    checked_magic = False
    with staging.open("wb") as out:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"The file passed this server's upload limit of {max_bytes} bytes, so it was discarded.",
                )
            if not checked_magic:
                # Held back rather than written, and read again if it came back shorter than the
                # signature, so nothing reaches the data folder before it is known to be HDF5.
                pending += chunk
                if len(pending) < len(HDF5_MAGIC):
                    continue
                if not pending.startswith(HDF5_MAGIC):
                    raise HTTPException(
                        status_code=400,
                        detail="The file is not a cooler file, whatever its name and stated type said.",
                    )
                checked_magic = True
                out.write(pending)
                pending = b""
                continue
            out.write(chunk)
    if not checked_magic:
        raise HTTPException(status_code=400, detail="The uploaded file is too small to be a cooler file.")
    return written


async def scan(path: Path, host: str | None, port: int | None, unix_socket: str | None, timeout_seconds: int) -> None:
    """Ask a clamd daemon about a stored file, refusing the upload if it cannot be scanned.

    clamd speaks a line of text followed by length-prefixed chunks over a plain socket, so an
    INSTREAM scan needs nothing beyond the standard library. An operator who configured a
    scanner and then cannot reach it is not in a position to say the file is clean, so every
    failure short of an `OK` answer ends with the file discarded.

    Runs on a worker thread: a scan of a large file takes seconds, and sitting on the socket
    from the endpoint itself would stall every other request the service is handling.
    """
    try:
        answer = await run_in_threadpool(_ask_clamd, path, host, port, unix_socket, timeout_seconds)
    except (OSError, RuntimeError) as error:
        raise HTTPException(
            status_code=503,
            detail=f"The file could not be scanned ({error}), so it was not accepted.",
        )

    # A clean scan answers `OK`, a hit answers `<threat> FOUND`, anything else is clamd
    # reporting a problem of its own.
    reply = answer.decode(errors="ignore").strip().strip("\x00 ")
    if reply == "OK":
        return
    if reply.endswith(" FOUND"):
        raise HTTPException(
            status_code=422,
            detail=f"The file was rejected by the virus scanner as {reply[: -len(' FOUND')]}.",
        )
    raise HTTPException(status_code=503, detail=f"The virus scanner answered {reply!r}, so the upload was not accepted.")


def _ask_clamd(path: Path, host: str | None, port: int | None, unix_socket: str | None, timeout_seconds: int) -> bytes:
    connection = _connect_clamd(host, port, unix_socket, timeout_seconds)
    try:
        connection.sendall(b"INSTREAM\0")
        with path.open("rb") as source:
            while chunk := source.read(CLAMD_CHUNK_SIZE):
                connection.sendall(struct.pack(">I", len(chunk)) + chunk)
        connection.sendall(struct.pack(">I", 0))
        return _read_clamd_answer(connection)
    finally:
        connection.close()


def _connect_clamd(host: str | None, port: int | None, unix_socket: str | None, timeout_seconds: int) -> socket.socket:
    if unix_socket and hasattr(socket, "AF_UNIX"):
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(timeout_seconds)
        connection.connect(unix_socket)
        return connection
    if not host or port is None:
        raise RuntimeError("no clamd daemon is configured to scan uploads with")
    return socket.create_connection((host, port), timeout=timeout_seconds)


def _read_clamd_answer(connection: socket.socket) -> bytes:
    """Read one newline-terminated reply, clamd's whole protocol being line based."""
    received = bytearray()
    while not received.endswith(b"\n"):
        piece = connection.recv(4096)
        if not piece:
            break
        received.extend(piece)
        # A reply is one short line; anything longer is not an answer but a stream being echoed.
        if len(received) > 4096:
            break
    return bytes(received).strip()


def static_mount_directories(app) -> list[Path]:
    """Every directory the app itself serves back to a browser, file for file."""
    directories = []
    for route in getattr(app, "routes", []):
        directory = getattr(getattr(route, "app", None), "directory", None)
        if directory:
            directories.append(Path(directory).resolve())
    return directories


def assert_stored_outside_webroot(app, directories: Iterable[str | Path]) -> None:
    """Refuse to start if uploaded files would sit inside a folder the app serves verbatim.

    The service itself has no way of returning an uploaded file — it opens a cooler and hands
    out numbers — so the files are outside the webroot today. This says so in a way that survives
    someone adding a static mount over the data folder later.
    """
    mounted = static_mount_directories(app)
    if not mounted:
        return
    for entry in directories:
        resolved = Path(entry).resolve()
        for directory in mounted:
            if resolved == directory or directory in resolved.parents:
                raise RuntimeError(
                    f"Uploaded files in {resolved} would be served straight to browsers by the "
                    f"static mount at {directory}. Point the data folders outside it."
                )
