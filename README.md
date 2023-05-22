# mikanim_action_roll_fix
Blender plugin to fix actions after roll changes to the bones.

## Features

- Fixes animation FCurves

## Installation

1. Download the plugin from https://github.com/spliter88/mikanim_action_roll_fix
2. In Blender, go to Edit -> Preferences -> Add-ons.
3. Click the "Install" button and navigate to the downloaded plugin file.
4. Enable the plugin by ticking the checkbox next to it.

## Usage

1. Create a backup of your rig
2. Modify the roll of the joints as you see fit
3. Select the "mikanim" tab
4. Set the "Reference" to your backup rig
5. Set the "Target" to your modified rig
6. Click Add Action to Fix List and chose which actions you want to fix (alternatively, click Add All Actions to Fix List and remove the ones you don't want fixed)
7. If you want to save the fixed action as a copy then make sure "Save as Copy" is selected, and that you have either a prefix or a suffix.
8. If you don't want to create a new separate copy each time you fix the action, check "Replace Existing", this will overwrite the actions whose name matches your new action.
9. If your animations are still broken try clicking "Sanitize Constraint Bones", and running the "Fix Selected Actions" once more.

## License

- Distributed under GPL 3

## Credits

- Made by Mikolaj Kuta
