"""Download a verified release asset and hand installation off to Windows."""

import base64
import hashlib
import os
import subprocess
import sys

from PySide6.QtCore import QFile, QIODevice, QObject, QTemporaryDir, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from update_checker import INSTALLER_NAME


UPDATE_ERROR_ARGUMENT = "--gradeipsi-update-error="
_UNINSTALL_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
    r"\{97342157-634C-4FAF-87AA-69BDCB694E43}_is1"
)
_DOWNLOAD_HOSTS = {
    "github.com",
    "release-assets.githubusercontent.com",
    "objects.githubusercontent.com",
}


def is_inno_installation():
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return False

    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, _UNINSTALL_KEY,
            access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
        ) as key:
            location, _ = winreg.QueryValueEx(key, "InstallLocation")
        return os.path.samefile(location, os.path.dirname(sys.executable))
    except (OSError, TypeError, ValueError):
        return False


class InstallerDownload(QObject):
    progress = Signal(int)
    finished = Signal()

    def __init__(self, asset, parent=None):
        super().__init__(parent)
        self.asset = asset
        self.error = ""
        self.cancelled = False
        self._directory = QTemporaryDir()
        self._file = QFile(self._directory.filePath(INSTALLER_NAME), self)
        self._digest = hashlib.sha256()
        self._size = 0
        self._manager = QNetworkAccessManager(self)
        self._reply = None

    def start(self):
        if not self._directory.isValid() or not self._file.open(
            QIODevice.OpenModeFlag.WriteOnly
        ):
            self.error = "Impossible de créer le fichier temporaire de mise à jour."
            self.finished.emit()
            return

        request = QNetworkRequest(QUrl(self.asset.url))
        request.setRawHeader(b"User-Agent", b"GradeIPSI-updater")
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.UserVerifiedRedirectPolicy,
        )
        request.setTransferTimeout(30_000)
        self._reply = self._manager.get(request)
        self._reply.redirected.connect(self._follow_redirect)
        self._reply.readyRead.connect(self._read)
        self._reply.finished.connect(self._complete)

    def cancel(self):
        if self._reply is not None:
            self.cancelled = True
            self._reply.abort()

    def _follow_redirect(self, url):
        if url.scheme() == "https" and url.host() in _DOWNLOAD_HOSTS and url.port(443) == 443:
            self._reply.redirectAllowed.emit()
        else:
            self.error = "Le téléchargement a été redirigé vers une adresse inattendue."
            self._reply.abort()

    def _read(self):
        if self.cancelled or self.error or self._reply.attribute(
            QNetworkRequest.Attribute.HttpStatusCodeAttribute
        ) != 200:
            return
        chunk = bytes(self._reply.readAll())
        self._size += len(chunk)
        if self._size > self.asset.size or self._file.write(chunk) != len(chunk):
            self.error = "Impossible d'enregistrer le fichier de mise à jour complet."
            if not self._reply.isFinished():
                self._reply.abort()
            return
        self._digest.update(chunk)
        self.progress.emit(100 * self._size // self.asset.size)

    def _complete(self):
        reply = self._reply
        if reply.bytesAvailable():
            self._read()
        if not self.cancelled and not self.error:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.error = f"Échec du téléchargement. {reply.errorString()}"
            elif self._size != self.asset.size or self._digest.hexdigest() != self.asset.sha256:
                self.error = "Le fichier téléchargé est incomplet ou son empreinte SHA-256 diffère."
            elif not self._file.flush():
                self.error = "Impossible de terminer l'enregistrement du fichier de mise à jour."
        self._file.close()
        self._reply = None
        reply.deleteLater()
        self.finished.emit()

    def launch_installer(self):
        environment = os.environ.copy()
        environment.update(
            GRADEIPSI_UPDATE_DIRECTORY=self._directory.path(),
            GRADEIPSI_UPDATE_EXE=sys.executable,
            GRADEIPSI_UPDATE_PID=str(os.getpid()),
            PYINSTALLER_RESET_ENVIRONMENT="1",
        )
        system_root = environment.get("SystemRoot", r"C:\Windows")
        powershell = os.path.join(
            system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
        )
        command = base64.b64encode(_INSTALL_COMMAND.encode("utf-16-le")).decode("ascii")
        subprocess.Popen(
            [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", command],
            cwd=system_root,
            env=environment,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        self._directory.setAutoRemove(False)


# The helper runs outside the PyInstaller bundle so Windows can replace its files.
# Only the installer is elevated. The helper restarts GradeIPSI as the original user.
_INSTALL_COMMAND = r"""
$ErrorActionPreference = 'Stop'
$directory = $env:GRADEIPSI_UPDATE_DIRECTORY
$application = $env:GRADEIPSI_UPDATE_EXE
$applicationDirectory = Split-Path -LiteralPath $application
$oldProcessId = [int]$env:GRADEIPSI_UPDATE_PID
$result = ''
try {
    Wait-Process -Id $oldProcessId -Timeout 60 -ErrorAction SilentlyContinue
    if (Get-Process -Id $oldProcessId -ErrorAction SilentlyContinue) {
        return
    }
    $installer = Join-Path $directory 'GradeIPSI_setup.exe'
    $arguments = '/SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /RESTARTEXITCODE=20 /NOFORCECLOSEAPPLICATIONS /LOG /DIR="' + $applicationDirectory + '"'
    $setup = Start-Process -FilePath $installer -ArgumentList $arguments -Verb RunAs -PassThru
    $setup.WaitForExit()
    if ($setup.ExitCode -ne 0) {
        $result = '--gradeipsi-update-error=' + $setup.ExitCode
    }
} catch {
    $result = '--gradeipsi-update-error=launch'
} finally {
    Remove-Item -LiteralPath (Join-Path $directory 'GradeIPSI_setup.exe') -Force -ErrorAction SilentlyContinue
    try {
        [System.IO.Directory]::Delete($directory)
    } catch [System.IO.IOException], [System.UnauthorizedAccessException] {}
}
if ($result) {
    Start-Process -FilePath $application -WorkingDirectory $applicationDirectory -ArgumentList $result
} else {
    Start-Process -FilePath $application -WorkingDirectory $applicationDirectory
}
"""
