from urllib.request import urlretrieve
from zipfile import ZipFile
import os
import shutil

from LSP.plugin import AbstractPlugin
from LSP.plugin import ClientConfig
from LSP.plugin import register_plugin
from LSP.plugin import unregister_plugin
from LSP.plugin import WorkspaceFolder
from LSP.plugin.core.typing import Any, Optional, List, Mapping, Callable
from LSP.plugin.core.views import range_to_region  # TODO: not public API :(
import sublime

VERSION = "1.38.2"
URL = "https://github.com/OmniSharp/omnisharp-roslyn/releases/download/v{}/omnisharp-{}.zip"  # noqa: E501


def _platform_str() -> str:
    platform = sublime.platform()
    if platform == "osx":
        return "osx"
    elif platform == "windows":
        if sublime.arch() == "x64":
            return "win-x64"
        else:
            return "win-x86"
    else:
        if sublime.arch() == "x64":
            return "linux-x64"
        else:
            return "linux-x86"


class OmniSharp(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    def get_settings(cls) -> sublime.Settings:
        return sublime.load_settings(
            "LSP-{}.sublime-settings".format(cls.name())
        )

    @classmethod
    def version_str(cls) -> str:
        return VERSION

    @classmethod
    def installed_version_str(cls) -> str:
        filename = os.path.join(cls.basedir(), "VERSION")
        with open(filename, "r") as f:
            version = f.readline().strip()
            return version

    @classmethod
    def basedir(cls) -> str:
        return os.path.join(cls.storage_path(), "LSP-{}".format(cls.name()))

    @classmethod
    def binary_path(cls) -> str:
        if sublime.platform() == "windows":
            retval = os.path.join(cls.basedir(), "OmniSharp.exe")
        else:
            retval = os.path.join(cls.basedir(), "omnisharp", "OmniSharp.exe")
        return retval

    @classmethod
    def get_command(cls, view) -> List[str]:
        settings = cls.get_settings()
        cmd = settings.get("command")
        if isinstance(cmd, list):
            return cmd
        return getattr(cls, "get_{}_command".format(sublime.platform()))(view)

    @classmethod
    def get_omnisharp_source(cls, view):
        # Project specific source directory for the server command line
        omnisharp_source = cls.get_view_setting_value(view, "LSP-OmniSharp.omnisharp_source")

        # Plugin-wide source directory for the server command line
        if not omnisharp_source:
            settings = cls.get_settings()
            omnisharp_source = settings.get("omnisharp_source")

        return omnisharp_source

    @classmethod
    def get_windows_command(cls, view) -> List[str]:
        retval = [cls.binary_path(), "--languageserver"]
        omnisharp_source = cls.get_omnisharp_source(view)
        if omnisharp_source:
            retval += ["--source", omnisharp_source]
        return retval

    @classmethod
    def get_osx_command(cls, view) -> List[str]:
        return cls.get_linux_command(view)

    @classmethod
    def mono_bin_plugin_path(cls) -> str:
        retval = os.path.join(cls.basedir(), "bin", "mono")
        return retval

    @classmethod
    def mono_bin_override_path(cls, view) -> str:

        # Project specific mono binary override
        retval = cls.get_view_setting_value(view, "LSP-OmniSharp.mono_binary")

        # Plugin specific mono binary override
        if not retval:
            settings = cls.get_settings()
            retval = settings.get("mono_binary")

        # Ok to return None here
        return retval

    @classmethod
    def mono_config_path(cls) -> str:
        return os.path.join(cls.basedir(), "etc", "config")

    @classmethod
    def get_linux_command(cls, view) -> List[str]:
        if cls.mono_bin_override_path(view):
            retval = [ cls.mono_bin_override_path(view) ]

        else:
            retval = [ cls.mono_bin_plugin_path(),
                        "--config",
                        cls.mono_config_path()]

        retval += ["--assembly-loader=strict"]
        retval += cls.get_windows_command(view)

        return retval

    @classmethod
    def get_view_setting_value(cls, view, param):
        view_settings = view.settings()
        retval = view_settings.get(param)

        if retval is None:
            return retval

        window = view.window()
        project_file_name = window.project_file_name()
        if project_file_name is None:
            return retval

        project_dir = os.path.dirname(project_file_name)
        retval = sublime.expand_variables(retval, {"projectdir" : project_dir})

        return retval

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        try:
            if cls.version_str() == cls.installed_version_str():
                return False
        except Exception:
            pass
        return True

    @classmethod
    def install_or_update(cls) -> None:
        shutil.rmtree(cls.basedir(), ignore_errors=True)
        os.makedirs(cls.basedir(), exist_ok=True)
        zipfile = os.path.join(cls.basedir(), "omnisharp.zip")
        try:
            version = cls.version_str()
            urlretrieve(URL.format(version, _platform_str()), zipfile)
            with ZipFile(zipfile, "r") as f:
                f.extractall(cls.basedir())
            os.unlink(zipfile)
            if sublime.platform() != "windows":
                os.chmod(cls.mono_bin_plugin_path(), 0o744)
            with open(os.path.join(cls.basedir(), "VERSION"), "w") as fp:
                fp.write(version)
        except Exception:
            shutil.rmtree(cls.basedir(), ignore_errors=True)
            raise

    @classmethod
    def on_pre_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: List[WorkspaceFolder],
        configuration: ClientConfig
    ) -> Optional[str]:
        configuration.command = cls.get_command(initiating_view)
        print("LSP-OmniSharp: Server Command={}".format(configuration.command))
        return None

    def on_pre_server_command(
        self,
        command: Mapping[str, Any],
        done_callback: Callable[[], None]
    ) -> bool:
        name = command["command"]
        if name == "omnisharp/client/findReferences":
            return self._handle_quick_references(command["arguments"], done_callback)
        return False

    def _handle_quick_references(self, arguments: List[Any], done_callback: Callable[[], None]) -> bool:
        session = self.weaksession()
        if not session:
            return True
        sb = session.get_session_buffer_for_uri_async(arguments[0]["uri"])
        if not sb:
            return True
        for sv in sb.session_views:
            if not sv.view.is_valid():
                continue
            region = range_to_region(arguments[0]["range"], sv.view)
            args = {"point": region.a}
            sv.view.run_command("lsp_symbol_references", args)
            done_callback()
            return True
        return True

    # --- custom notification handlers ----------------------------------------

    def _print(self, sticky: bool, fmt: str, *args: Any) -> None:
        session = self.weaksession()
        if session:
            message = fmt.format(*args)
            if sticky:
                session.set_window_status_async(self.name(), message)
            else:
                session.erase_window_status_async(self.name())
                session.window.status_message(message)

    def m_o__msbuildprojectdiagnostics(self, params: Any) -> None:
        self._print(True, "Compiled {}", params["FileName"])

    def m_o__projectconfiguration(self, params: Any) -> None:
        self._print(False, "Project configured")

    def m_o__unresolveddependencies(self, params: Any) -> None:
        self._print(False, "{} has unresolved dependencies", params["FileName"])

    def _get_assembly_name(self, params: Any) -> Optional[str]:
        project = params.get("MsBuildProject")
        if project:
            assembly_name = project.get("AssemblyName")
            if isinstance(assembly_name, str):
                return assembly_name
        return None

    def m_o__projectadded(self, params: Any) -> None:
        assembly_name = self._get_assembly_name(params)
        if assembly_name:
            self._print(False, "Project added: {}", assembly_name)

    def m_o__projectchanged(self, params: Any) -> None:
        assembly_name = self._get_assembly_name(params)
        if assembly_name:
            self._print(False, "Project changed: {}", assembly_name)


def plugin_loaded() -> None:
    register_plugin(OmniSharp)


def plugin_unloaded() -> None:
    unregister_plugin(OmniSharp)
