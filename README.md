# LSP-OmniSharp

This is a helper package that automatically installs and updates
[OmniSharp](https://github.com/OmniSharp/omnisharp-roslyn) for you.

To use this package, you must have:

- The [LSP](https://packagecontrol.io/packages/LSP) package.
- The [.NET SDK](https://dotnet.microsoft.com/download). (The "Core" version **does not work on macOS**.)
- (Optional but recommended) Install the [LSP-file-watcher-chokidar](https://github.com/sublimelsp/LSP-file-watcher-chokidar) via Package Control to enable functionality to notify the server about new files.


## Applicable Selectors

This language server operates on views with the `source.cs` base scope.

## Plugin Installation

The plugin is available on github. To install, clone the repo in sublime the `Packages` directory.


## Server Installation Location

The server is installed in the $DATA/Package Storage/LSP-OmniSharp directory, where $DATA is the base data path of Sublime Text.
For instance, $DATA is `~/.config/sublime-text` on a Linux system. If you want to force a re-installation of the server,
you can delete the entire $DATA/Package Storage/LSP-OmniSharp directory.

Like any helper package, installation starts when you open a view that is suitable for this language server. In this
case, that means that when you open a view with the `source.cs` base scope, installation commences.

## Configuration

Configure OmniSharp by running `Preferences: LSP-OmniSharp Settings` from the Command Palette.

Alternatively, choose "Settings -> Package Settings -> LSP -> Servers -> LSP OmniSharp"

## Capabilities

OmniSharp can do a lot of cool things, like

- code completion
- signature help
- hover info
- some quality code actions
- formatting
- find references
- goto def

## Unity Support on Mac OS

The following steps will enable OmniSharp on Unity for Mac OS.


1. Install the "Visual Studio" devtool from within Unity.
    This can be done from the Unity Hub when installing a new Unity editor or by choosing "Add modules" to an existing editor installation.

2. Set Visual Studio as the external editor for Unit:
    ```Settings -> External Tools -> External Script Editor```

3. Generate visual studio solution files within a Unity project:
    ```Settings -> External Tools -> Regenerate project files```

    NOTE: This currently needs to be done every time a new .cs file is added to a Unity project

4. Create a sublime project for the Unity project from Sublime:
    ```Project -> Save Project As...```

5. Add the following setting to your .sublime-project file created in step #4

    ```
        "settings":
        {
            "LSP-OmniSharp.omnisharp_source" : "$projectdir"
        }
    ```

6. Use the system installed version of mono instead of the one provided by the plugin.

    From `Settings -> Package Settings -> LSP -> Servers -> LSP OmniSharp`

    Add:

    ```
        "mono_binary" : "mono",
    ```

    or

    ```
        "mono_binary" : "/Library/Frameworks/Mono.framework/Versions/Current/Commands/mono",
    ```

7. Relaunch Sublime
    Check the console to ensure that the `LSP-OmniSharp: Server Command` has the correct path to `mono` and
    includes a `'--source` argument corresponding to the Unity project directory.

At this point Sublime should recognize the built in Unity classes.

Shortcomings:

- When adding a new script in the Unity project you must redo step #3 above, i.e. run "Settings -> External Tools -> Regenerate project files". This will update the .csproj necessary.

- The methods for UnityEngine.MonoBehavior don't show up as autocomplete options. It looks like this is because
they are not actually overridden methods (since there's no `override` keyword) so OmniSharp doesn't
recognize messages as valid completions.

- The default editor for the Unity project is still Visual Studio since project files need to be generated. Sublime must be launched independently.
