# 
# This file is part of the Mikanim Action Roll Fix plugin
# https://github.com/spliter88/mikanim_action_roll_fix
# Copyright (c) 2023 Mikolaj Kuta.
# 
# This program is free software: you can redistribute it and/or modify  
# it under the terms of the GNU General Public License as published by  
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU 
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with this program. If not, see <http://www.gnu.org/licenses/>.


bl_info = {
    "name": "Mikanim Action Roll Fix",
    "author": "Mikolaj Kuta (mkuta)",
    "version": (0, 3, 0),
    "blender": (3, 50, 0),
    "location": "View3D > Sidebar > Mikanim > Action Roll Fix",
    "description": "Fixes the roll in the animations of selected actions",
    "category": "Animation",
}

from . import action_roll_fix_tool
from . import roll_fix_utilities

def register():
    action_roll_fix_tool.register_roll_fix_tool()

def unregister():
    action_roll_fix_tool.unregister_roll_fix_tool()

def unregister_classes():
    action_roll_fix_tool.unregister_roll_fix_tool()

# Register the addon
if __name__ == "__main__":
    register()