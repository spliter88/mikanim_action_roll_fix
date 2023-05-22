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


import bpy
from . import roll_fix_utilities


# property group for holding action item data
class ACTIONROLLFIX_ActionFixItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    index: bpy.props.IntProperty()


# armature object filter
def p_armature_filter(self, object):
    return object.type == 'ARMATURE'


# property group for holding active properties of our plugin
class ACTIONROLLFIX_Properties(bpy.types.PropertyGroup):
    reference_armature_object: bpy.props.PointerProperty(type=bpy.types.Object, poll=p_armature_filter, description="Armature object before roll changes")
    target_armature_object: bpy.props.PointerProperty(type=bpy.types.Object, poll=p_armature_filter, description="Armature object with roll changes and broken animations")
    save_as_copy: bpy.props.BoolProperty(default=True, name="Save As Copy", description="If checked, we'll save the fixed action as a copy")
    replace_existing: bpy.props.BoolProperty(default=True, name="Replace Existing", description="If checked, we'll replace existing actions that already have the name, otherwise we'll just keep adding new copies")
    copy_name_prefix: bpy.props.StringProperty(default="fixed_", description="Suffix to add to the fixed action")
    copy_name_suffix: bpy.props.StringProperty(default="", description="Suffix to add to the fixed action")
    action_fix_list: bpy.props.CollectionProperty(type=ACTIONROLLFIX_ActionFixItem)
    action_fix_list_index: bpy.props.IntProperty()


# Operator to remove a string from the list
class ACTIONROLLFIX_OT_RemoveActionOperator(bpy.types.Operator):
    bl_idname = "action_roll_fix.remove_action"
    bl_label = "Remove String"

    index: bpy.props.IntProperty()

    def execute(self, context):
        fix_list = context.scene.action_roll_fix.action_fix_list
        if self.index >= 0 and self.index < len(fix_list):
            fix_list.remove(self.index)
            for i in range(len(fix_list)):
                fix_list[i].index = i
        for region in context.area.regions:
            if region.type == "UI":
                region.tag_redraw()
        return {'FINISHED'}


# Operator to add the selected action to the list
class ACTIONROLLFIX_OT_AddActionOperator(bpy.types.Operator):
    bl_idname = "action_roll_fix.add_action_to_fix_list"
    bl_label = "Add Action"
    
    selected_action_name: bpy.props.StringProperty()
    
    def execute(self, context):
        fix_list = context.scene.action_roll_fix.action_fix_list
        if self.selected_action_name:
            for item in fix_list:
                if item.name==self.selected_action_name:
                    return {'FINISHED'}
            index = len(fix_list)
            action_item = fix_list.add()
            action_item.name = self.selected_action_name
            action_item.index = index
            for region in context.area.regions:
                if region.type == "UI":
                    region.tag_redraw()
        return {'FINISHED'}


# Operator to add the selected action to the list
class ACTIONROLLFIX_OT_AddAllActionsOperator(bpy.types.Operator):
    bl_idname = "action_roll_fix.acc_all_actions_to_fix_list"
    bl_label = "Add Action"
    
    def execute(self, context):
        fix_list = context.scene.action_roll_fix.action_fix_list
        fix_list.clear()
        for action in bpy.data.actions:
            index = len(fix_list)
            action_item = fix_list.add()
            action_item.name = action.name
            action_item.index = index
        for region in context.area.regions:
            if region.type == "UI":
                region.tag_redraw()
        return {'FINISHED'}


# Operator to show a menu with actions
class ACTIONROLLFIX_OT_ShowActionMenu(bpy.types.Operator):
    bl_idname = "action_roll_fix.show_action_fix_list"
    bl_label = "Show Action List"

    def execute(self, context):
        bpy.context.window_manager.popup_menu(self.draw_menu, title="Select Action")
        return {'FINISHED'}

    def draw_menu(self, menu, context):
        actions = bpy.data.actions

        for action in actions:
            is_duplicate = False
            for item in bpy.context.scene.action_roll_fix.action_fix_list:
                if item.name == action.name:
                    is_duplicate = True
                    break
            if not is_duplicate:
                menu.layout.operator("action_roll_fix.add_action_to_fix_list", text=action.name).selected_action_name = action.name


# Operator to show a menu with actions
class ACTIONROLLFIX_OT_ExecuteRollFix(bpy.types.Operator):
    bl_idname = "action_roll_fix.execute_roll_fix"
    bl_label = "Execute Roll Fix"

    def execute(self, context):
        converted_actions = []
        failed_actions=[]
        plugin_props = context.scene.action_roll_fix
        action_count = len(plugin_props.action_fix_list)
        
        if not plugin_props.reference_armature_object:
            self.report({"ERROR"},"Missing Reference Armature")
            return {'CANCELLED'}
        if not plugin_props.target_armature_object:
            self.report({"ERROR"},"Missing Target Armature")
            return {'CANCELLED'}
        if plugin_props.save_as_copy:
            if not plugin_props.copy_name_prefix and not plugin_props.copy_name_suffix and plugin_props.replace_existing:
                self.report({"ERROR"},"Make Copy with Replace Existing is selected, but no preffix or suffix specified, this would replace the original action, to do that please uncheck \"Make Copy\"")
                return {'CANCELLED'}
        success_count = 0
        for i in range(action_count):
            action_item = plugin_props.action_fix_list[i]
            print("Converting action " + action_item.name)
            action_id = bpy.data.actions.find(action_item.name)
            if action_id>=0:
                action = bpy.data.actions[action_id]
                fix_action = action
                if plugin_props.save_as_copy:
                    copy_name = plugin_props.copy_name_prefix + action_item.name + plugin_props.copy_name_suffix
                    fix_action = roll_fix_utilities.make_action_copy(action,copy_name,plugin_props.replace_existing)

                result = roll_fix_utilities.apply_action_roll_fix_correction(plugin_props.reference_armature_object,plugin_props.target_armature_object,fix_action)
                if result:
                    success_count = success_count+1
                    completed_count = i+1
                    tally_message = f"[{completed_count}/{action_count}]"
                    if plugin_props.save_as_copy:
                        self.report({"INFO"}, tally_message + " Successfully converted action " + action_item.name + " saved as "+ fix_action.name)
                    else:
                        self.report({"INFO"}, tally_message + " Successfully converted action " + action_item.name)
                else:
                    self.report({"ERROR"},result.message)
                    bpy.ops.ed.undo_redo()
                    return {'CANCELLED'}
            else:
                print("Could not find action  " + action_item.name)
        tally_message = f"[{success_count}/{action_count}]"
        self.report({"INFO"}, "Successfully converted " + tally_message +" actions")
        bpy.ops.ed.undo_push(message="Converted Action Rolls")

        return {'FINISHED'}

class ACTIONROLLFIX_OT_SanitizeBoneRolls(bpy.types.Operator):
    bl_idname = "action_roll_fix.sanitize_rolls"
    bl_label = "Sanitize Constraint Bones"

    def execute(self, context):
        plugin_props = context.scene.action_roll_fix
        armature_obj = plugin_props.target_armature_object
        if not armature_obj:
            return {'CANCELLED'}
        bones_to_correct=[]
        for pose_bone in armature_obj.pose.bones:
            for constraint in pose_bone.constraints:
                if constraint.type != 'COPY_ROTATION' and constraint.type != 'COPY_LOCATION' and constraint.type != 'COPY_TRANSFORMS':
                    continue
                if constraint.target != armature_obj:
                    continue
                if not constraint.subtarget:
                    continue
                target_bone_id = armature_obj.data.bones.find(constraint.subtarget)
                if target_bone_id<0:
                    continue
                target_bone = armature_obj.data.bones[target_bone_id]
                bones_to_correct.append((pose_bone.name,target_bone.name))
        if len(bones_to_correct)>0:
            prev_mode = bpy.context.mode
            prev_active = bpy.context.view_layer.objects.active
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='EDIT')
            for bone_tuple in bones_to_correct:
                src_edit_bone = armature_obj.data.edit_bones[bone_tuple[0]]
                dst_edit_bone = armature_obj.data.edit_bones[bone_tuple[1]]
                dst_edit_bone.roll = src_edit_bone.roll
            bpy.context.view_layer.objects.active = prev_active
            bpy.ops.object.mode_set(mode=prev_mode)
        bpy.ops.ed.undo_push(message="Sanitized Bones")
        return {'FINISHED'}

# Action list that displays a list of fix actions where each element can be removed.
class ACTIONROLLFIX_UL_ActionFixList(bpy.types.UIList):
    """Action Roll Fix List"""
    filter_text: bpy.props.StringProperty(default='')
    order_by_text: bpy.props.BoolProperty(default=True)

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        item_icon = 'ACTION'
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row()
            row.label(text=item.name, icon = item_icon)
            row.operator("action_roll_fix.remove_action", text="", icon="X").index = item.index
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text='', icon = item_icon)

    def draw_filter(self, context, layout):
        layout.separator()
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'filter_text', text='', icon='VIEWZOOM')

    def filter_items(self, context, data, propname):
        filtered = []
        ordered = []
        items = getattr(data, propname)
        helper_funcs = bpy.types.UI_UL_list
        if self.filter_text:
            filtered = helper_funcs.filter_items_by_name(self.filter_text, self.bitflag_filter_item, items, "name",)
        if not filtered:
            filtered = [self.bitflag_filter_item] * len(items)
        if self.order_by_text:
            ordered = helper_funcs.sort_items_by_name(items,"name")
        return filtered, ordered


# ActionRollFix side Panel
class ACTIONROLLFIX_PT_Panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mikanim"
    bl_label = "Action Roll Fix"
    
    def draw(self, context):
        layout = self.layout
        params = context.scene.action_roll_fix
        layout.prop(params, "reference_armature_object",text="Reference")
        layout.prop(params, "target_armature_object",text="Target")
        layout.template_list("ACTIONROLLFIX_UL_ActionFixList", "action_fix_list", params,"action_fix_list", params, "action_fix_list_index")
        layout.operator("action_roll_fix.show_action_fix_list", text="Add Action to Fix List", icon="ADD")
        layout.operator("action_roll_fix.acc_all_actions_to_fix_list", text="Add All Actions to Fix List", icon="ADD")
        layout.separator()
        layout.prop(params,"save_as_copy")
        if params.save_as_copy:
            layout.prop(params,"copy_name_prefix",text="Prefix")
            layout.prop(params,"copy_name_suffix",text="Suffix")
            layout.prop(params,"replace_existing",text="Replace Existing");
        layout.separator()
        layout.operator("action_roll_fix.execute_roll_fix", text="Fix Selected Actions")
        layout.separator()
        layout.operator("action_roll_fix.sanitize_rolls", text="Sanitize Constraint Bones")
        

# Register the classes
classes = (
    ACTIONROLLFIX_ActionFixItem,
    ACTIONROLLFIX_Properties,
    ACTIONROLLFIX_OT_RemoveActionOperator,
    ACTIONROLLFIX_OT_AddActionOperator,
    ACTIONROLLFIX_OT_AddAllActionsOperator,
    ACTIONROLLFIX_OT_ShowActionMenu,
    ACTIONROLLFIX_OT_ExecuteRollFix,
    ACTIONROLLFIX_OT_SanitizeBoneRolls,
    ACTIONROLLFIX_UL_ActionFixList,
    ACTIONROLLFIX_PT_Panel
)

def register_roll_fix_tool():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.action_roll_fix = bpy.props.PointerProperty(type=ACTIONROLLFIX_Properties)


def unregister_roll_fix_tool():
    del bpy.types.Scene.action_roll_fix
    for cls in classes:
        bpy.utils.unregister_class(cls)