"""Check GitHub releases against the version recorded in version.txt."""

import json
import os
import re
import sys

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest


GITHUB_REPOSITORY = "kayzexiv-droid/GradeIPSI"
RELEASE_API_URL = (
    f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
)
_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$", re.IGNORECASE)


def load_current_version():
    app_directory = getattr(
        sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
    )
    version_path = os.path.join(app_directory, "version.txt")
    try:
        with open(version_path, "r", encoding="utf-8") as version_file:
            version = version_file.read().strip()
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Impossible de lire {version_path} : {error}") from error

    if _parse_version(version) is None:
        raise ValueError(
            f"Version invalide dans {version_path} : utilisez le format X.Y.Z."
        )
    return version


def _parse_version(tag):
    if not isinstance(tag, str):
        return None
    match = _VERSION_PATTERN.fullmatch(tag)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


class ReleaseChecker(QObject):
    release_available = Signal(str, str, str)
    up_to_date = Signal(str)
    check_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)
        self._reply = None
        self._current_version = None
        self._timed_out = False
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.setInterval(8000)
        self._timeout.timeout.connect(self._abort_timed_out_request)

    def check(self):
        if self._reply is not None:
            return

        try:
            self._current_version = load_current_version()
        except ValueError as error:
            self.check_failed.emit(str(error))
            return

        request = QNetworkRequest(QUrl(RELEASE_API_URL))
        request.setRawHeader(b"Accept", b"application/vnd.github+json")
        request.setRawHeader(b"User-Agent", b"GradeIPSI-update-checker")
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            request.setRawHeader(b"Authorization", f"Bearer {token}".encode("utf-8"))

        self._timed_out = False
        self._reply = self._manager.get(request)
        self._reply.finished.connect(self._handle_reply)
        self._timeout.start()

    def _abort_timed_out_request(self):
        if self._reply is not None:
            self._timed_out = True
            self._reply.abort()

    def _handle_reply(self):
        reply = self._reply
        self._reply = None
        self._timeout.stop()

        if reply is None:
            return
        current_version = self._current_version

        status = reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        )
        if self._timed_out:
            self.check_failed.emit("La vérification des mises à jour a expiré.")
            reply.deleteLater()
            return
        if reply.error() != QNetworkReply.NetworkError.NoError:
            detail = reply.errorString()
            if status == 404:
                detail = (
                    "Aucune release publiée ou dépôt GitHub inaccessible."
                )
            self.check_failed.emit(f"Vérification des mises à jour impossible : {detail}")
            reply.deleteLater()
            return

        try:
            release = json.loads(bytes(reply.readAll()))
            if not isinstance(release, dict):
                raise ValueError("Réponse GitHub invalide.")
            tag = release.get("tag_name")
            url = release.get("html_url")
            name = release.get("name") or tag
            if not all(isinstance(value, str) and value for value in (tag, url, name)):
                raise ValueError("La release ne contient pas de tag ou de lien valide.")
            version = _parse_version(tag)
            current_version_tuple = _parse_version(current_version)
            if version is None or current_version_tuple is None:
                raise ValueError(
                    "Le tag de release et la version de l'application doivent être "
                    "au format vX.Y.Z."
                )
            release_url = QUrl(url)
            if release_url.scheme() != "https" or release_url.host() != "github.com":
                raise ValueError("Le lien de release GitHub n'est pas valide.")
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            self.check_failed.emit(f"Réponse GitHub invalide : {error}")
            reply.deleteLater()
            return

        reply.deleteLater()
        if version > current_version_tuple:
            self.release_available.emit(tag, name, url)
        else:
            self.up_to_date.emit(current_version)
