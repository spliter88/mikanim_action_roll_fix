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
import mathutils
from math import isclose

class OpResult:
    def __init__(self, success, message=None):
        self.success = success
        self.message = message

    def __bool__(self):
        return self.success

    def __nonzero__(self):#for python 2.x compatibility
        return self.__bool__()


def make_action_copy(action, copy_name, replace_existing):
    action_copy_id = bpy.data.actions.find(copy_name)
    if replace_existing:
        if action_copy_id>=0:
            bpy.data.actions.remove(bpy.data.actions[action_copy_id])
    else:
        test_name = copy_name
        iter = 0
        while action_copy_id >= 0:
            iter+=1
            test_name = copy_name + str(iter).zfill(3)
            action_copy_id = bpy.data.actions.find(test_name)
        copy_name = test_name
    copies_action = action.copy()
    copies_action.name = copy_name
    return copies_action


def apply_action_roll_fix_correction(reference_armature_obj, target_armature_obj, target_action):
    target_armature_obj.animation_data.action = target_action
    print("Called Action roll fix correction")
    identity_rot = mathutils.Quaternion()
    for reference_pose_bone in reference_armature_obj.pose.bones:
        if reference_pose_bone.name not in target_armature_obj.pose.bones:
            continue
        target_pose_bone = target_armature_obj.pose.bones[reference_pose_bone.name]
        if target_pose_bone.rotation_mode != reference_pose_bone.rotation_mode:
            return OpResult(False,f"Reference and Target armatures have incompatible bone rotations on bone \"{reference_pose_bone.name}\", only same-type rotations can be converted")
        reference_bone = reference_pose_bone.bone
        target_bone = target_pose_bone.bone

        bone_rot_old = reference_bone.matrix_local.to_quaternion()
        bone_rot_new = target_bone.matrix_local.to_quaternion()
        #we skip all the bones that don't need adjustment
        if not all(isclose(rot_old,rot_new) for rot_old,rot_new in zip(bone_rot_old,bone_rot_new)):
            correction_rot = bone_rot_new.inverted() @ bone_rot_old
            result = rotate_rotation_fcurves(target_action, target_pose_bone, correction_rot)
            if not result:
                return result
            result = rotate_position_fcurves(target_action, target_pose_bone, correction_rot)
            if not result:
                return result
    return OpResult(True)


def rotate_keyframe(inv_rotation, rotation, src_fcurves, dst_fcurves, keyframeIdx):
    #note: both source and destination curves can be the same curve object
    src_keys = [None,None,None,None]
    dst_keys = [None,None,None,None]
    #We need to guarantee that the quaternion key we're editing exists on both source and destination fcurves, and has the same keyframe times for all its elements
    for i in range(4):
        if(len(src_fcurves[i].keyframe_points)<=keyframeIdx):
            return OpResult(False, "FCurve conversion failed, Fcurve '{src_fcurves.data_path}' has missing keyframes, all curves need to have the same number of keyframes")
        if(len(dst_fcurves[i].keyframe_points)<=keyframeIdx):
            return OpResult(False, "FCurve conversion failed, Fcurve '{dst_fcurves.data_path}' has missing keyframes, all curves need to have the same number of keyframes")
        src_keys[i] = src_fcurves[i].keyframe_points[keyframeIdx]
        dst_keys[i] = dst_fcurves[i].keyframe_points[keyframeIdx]

    key_time = src_keys[i].co.x
    for i in range(4):
        if not isclose(src_keys[i].co.x, key_time):
            return OpResult(False, "FCurve conversion failed, Fcurve '{src_fcurves.data_path}' has keyframes on different frames, all rotation keys have to be on the same frame")
        if not isclose(dst_keys[i].co.x, key_time):
            return OpResult(False, "FCurve conversion failed, Fcurve '{dst_fcurves.data_path}' has keyframes on different frames, all rotation keys have to be on the same frame")
    
    key_quat_co=mathutils.Quaternion()
    key_quat_hl=mathutils.Quaternion()
    key_quat_hr=mathutils.Quaternion()
    for i in range(4):
        key_quat_co[i] = src_keys[i].co.y
        key_quat_hl[i] = src_keys[i].handle_left.y
        key_quat_hr[i] = src_keys[i].handle_right.y

    key_quat_co = rotation @ key_quat_co @ inv_rotation
    key_quat_hl = rotation @ key_quat_hl @ inv_rotation
    key_quat_hr = rotation @ key_quat_hr @ inv_rotation
    for i in range(4):
        dst_keys[i].co.y = key_quat_co[i]
        dst_keys[i].handle_left.y = key_quat_hl[i]
        dst_keys[i].handle_right.y = key_quat_hr[i]
    return OpResult(True)


#retrieves curves from action and stores them in an existing list
def gather_fcurves(action, data_path, max_index, out_fcurves):
    for fcurve in action.fcurves:
        if fcurve.data_path == data_path:
            if fcurve.array_index>=max_index:
                break
            out_fcurves[fcurve.array_index] = fcurve
    curve_count = 0
    for fcurve in out_fcurves:
        if fcurve:
            curve_count+=1
    return curve_count


#This checks if two curves are compatible, ie: if they have the same number of keyframes, and the keyframes have the same times set.
def check_fcurve_keyframe_compatibility(fcurve1, fcurve2):
    key_count1 = len(fcurve1.keyframe_points)
    key_count2 = len(fcurve2.keyframe_points)
    if(key_count1!=key_count2):
        return OpResult(False,f"FCurves have different numbers of keyframes, they all need to have the same keyframe count")
    for i in range(key_count1):
        if not isclose(fcurve1.keyframe_points[i].co.x,fcurve2.keyframe_points[i].co.x):
            return OpResult(False,f"FCurve keyframes have different times, they all need to have the same time")
    return OpResult(True)


#just a small helper class that lets us store keyframe values as quaternions
class QuatKey:
    value:mathutils.Quaternion
    handle_left:mathutils.Quaternion
    handle_right:mathutils.Quaternion
    
    def __init__(self):
        self.value = mathutils.Quaternion()
        self.handle_left = mathutils.Quaternion()
        self.handle_right = mathutils.Quaternion()

#just a small helper class that lets us store keyframe values as vectors
class VectorKey:
    value:mathutils.Vector
    handle_left:mathutils.Vector
    handle_right:mathutils.Vector
    
    def __init__(self):
        self.value = mathutils.Vector()
        self.handle_left = mathutils.Vector()
        self.handle_right = mathutils.Vector()

# RotationCurveDesc's descendants provide functionality for writing to and from fcurves of particular types.
class CurveDesc:
    data_path: str
    param_count: int

    def __init__(self, pose_bone):
        self.data_path = pose_bone.path_from_id(self.get_param_id())
        self.param_count = len(getattr(pose_bone,self.get_param_id()))

    def get_param_id(self):
        raise NotImplementedError("Subclasses must implement the get_keyframe_count() method")
        return ""

# RotationCurveDesc's descendants provide functionality for writing to and from fcurves of particular types.
class RotationCurveDesc(CurveDesc):
    def set_quat_key_from_keys(self, dst_quat_key, src_keys):
        raise NotImplementedError("Subclasses must implement the set_quat_key_from_keys() method")

    def set_keys_from_quat_key(self, dst_keys, src_quat_key):
        raise NotImplementedError("Subclasses must implement the set_keys_from_quat_key() method")


# QuaternionRotationCurveDesc is used to help converting quaternion fcurves
class QuaternionRotationCurveDesc(RotationCurveDesc):
    def get_param_id(self):
        return "rotation_quaternion"

    def set_quat_key_from_keys(self, dst_quat_key, src_keys):
        assert len(src_keys) == 4 
        for i in range(4):
            dst_quat_key.value[i] = src_keys[i].co.y
            dst_quat_key.handle_left[i]= src_keys[i].handle_left.y
            dst_quat_key.handle_right[i] = src_keys[i].handle_right.y

    def set_keys_from_quat_key(self, dst_keys, src_quat_key):
        assert len(dst_keys) == 4 
        for i in range(4):
            dst_keys[i].co.y = src_quat_key.value[i]
            dst_keys[i].handle_left.y = src_quat_key.handle_left[i]
            dst_keys[i].handle_right.y = src_quat_key.handle_right[i]


# EulerRotationCurveDesc is used to help converting euler fcurves
class EulerRotationCurveDesc(RotationCurveDesc):
    euler_order:str

    def __init__(self, pose_bone):
        super().__init__(pose_bone)
        self.euler_order = pose_bone.rotation_euler.order

    def get_param_id(self):
        return "rotation_euler"

    def set_quat_key_from_keys(self, dst_quat_key, src_keys):
        assert len(src_keys) == 3
        euler_val =          mathutils.Euler((src_keys[0].co.y,           src_keys[1].co.y,           src_keys[2].co.y),           self.euler_order)
        euler_handle_left =  mathutils.Euler((src_keys[0].handle_left.y,  src_keys[1].handle_left.y,  src_keys[2].handle_left.y),  self.euler_order)
        euler_handle_right = mathutils.Euler((src_keys[0].handle_right.y, src_keys[1].handle_right.y, src_keys[2].handle_right.y), self.euler_order)
        dst_quat_key.value = euler_val.to_quaternion()
        dst_quat_key.handle_left= euler_handle_left.to_quaternion()
        dst_quat_key.handle_right = euler_handle_right.to_quaternion()

    def set_keys_from_quat_key(self, dst_keys, src_quat_key):
        assert len(dst_keys) == 3
        #note: we re-create the euler keys because we need them for the compatibility calculations
        old_euler_val =          mathutils.Euler((dst_keys[0].co.y,           dst_keys[1].co.y,           dst_keys[2].co.y),           self.euler_order)
        old_euler_handle_left =  mathutils.Euler((dst_keys[0].handle_left.y,  dst_keys[1].handle_left.y,  dst_keys[2].handle_left.y),  self.euler_order)
        old_euler_handle_right = mathutils.Euler((dst_keys[0].handle_right.y, dst_keys[1].handle_right.y, dst_keys[2].handle_right.y), self.euler_order)
        euler_val =          src_quat_key.value.to_euler(       self.euler_order,old_euler_val)
        euler_handle_left =  src_quat_key.handle_left.to_euler( self.euler_order,old_euler_handle_left)
        euler_handle_right = src_quat_key.handle_right.to_euler(self.euler_order,old_euler_handle_right)
        for i in range(3):
            dst_keys[i].co.y = euler_val[i]
            dst_keys[i].handle_left.y = euler_handle_left[i]
            dst_keys[i].handle_right.y = euler_handle_right[i]


# AxisAngleCurveDesc is used to help converting axis-angle fcurves
class AxisAngleCurveDesc(RotationCurveDesc):
    def get_param_id(self):
        return "rotation_axis_angle"

    def set_quat_key_from_keys(self, dst_quat_key, src_keys):
        assert len(src_keys) == 4 
        dst_quat_key.value =        mathutils.Quaternion((src_keys[1].co.y,           src_keys[2].co.y,           src_keys[3].co.y),           src_keys[0].co.y)
        dst_quat_key.handle_left=   mathutils.Quaternion((src_keys[1].handle_left.y,  src_keys[2].handle_left.y,  src_keys[3].handle_left.y),  src_keys[0].handle_left.y)
        dst_quat_key.handle_right = mathutils.Quaternion((src_keys[1].handle_right.y, src_keys[2].handle_right.y, src_keys[3].handle_right.y), src_keys[0].handle_right.y)

    def set_keys_from_quat_key(self, dst_keys, src_quat_key):
        assert len(dst_keys) == 4 
        aangle_val = src_quat_key.value.to_axis_angle()
        aangle_handle_left = src_quat_key.handle_left.to_axis_angle()
        aangle_handle_right = src_quat_key.handle_right.to_axis_angle()
        for i in range(3):
            dst_keys[i+1].co.y = aangle_val[0][i]
            dst_keys[i+1].handle_left.y = aangle_handle_left[0][i]
            dst_keys[i+1].handle_right.y = aangle_handle_right[0][i]
        dst_keys[0].co.y = aangle_val[1]
        dst_keys[0].handle_left.y = aangle_handle_left[1]
        dst_keys[0].handle_right.y = aangle_handle_right[1]


# PositionCurveDesc is used to help converting position fcurves
class PositionCurveDesc(CurveDesc):
    def get_param_id(self):
        return "location"

    def set_vec_key_from_keys(self, dst_quat_key, src_keys):
        assert len(src_keys) == self.param_count
        for i in range(self.param_count):
            dst_quat_key.value[i] = src_keys[i].co.y
            dst_quat_key.handle_left[i]= src_keys[i].handle_left.y
            dst_quat_key.handle_right[i] = src_keys[i].handle_right.y

    def set_keys_from_vec_key(self, dst_keys, src_quat_key):
        assert len(dst_keys) == self.param_count
        for i in range(self.param_count):
            dst_keys[i].co.y = src_quat_key.value[i]
            dst_keys[i].handle_left.y = src_quat_key.handle_left[i]
            dst_keys[i].handle_right.y = src_quat_key.handle_right[i]


#returns the curve descriptor that matches the pose_bone's rotation_mode
def get_curve_desc_for_bone(pose_bone):
    if pose_bone.rotation_mode=='QUATERNION':
        return QuaternionRotationCurveDesc(pose_bone)
    if pose_bone.rotation_mode=='AXIS_ANGLE':
        return AxisAngleCurveDesc(pose_bone)
    return EulerRotationCurveDesc(pose_bone)

#this just holds the curves
class CurveCollection:
    curve_count: int
    fcurves:[]
    key_count: int
    is_valid: bool
    error_message:str
    curve_desc:CurveDesc

    def __init__(self, action, curve_desc):
        self.is_valid = False
        self.curve_desc = curve_desc
        self.fcurves = [None]*curve_desc.param_count
        self.curve_count = gather_fcurves(action, curve_desc.data_path, curve_desc.param_count, self.fcurves)
        self.error_message = None
        self.key_count = 0
        if self.curve_count==0:
            self.is_valid = True
            return
        if self.curve_count!=curve_desc.param_count:
            self.error_message = f"Action {action.name} cannot be converted: it has the wrong number of curves for {curve_desc.data_path} (has {self.curve_count} but should have {curve_desc.param_count})"
            return
        for i in range(1, self.curve_count):
            result = check_fcurve_keyframe_compatibility(self.fcurves[0], self.fcurves[i])
            if not result:
                self.error_message = f"Action {action.name} cannot be converted: {result.message}"
                return
        self.key_count = len(self.fcurves[0].keyframe_points)
        self.is_valid = True

    def __bool__(self):
        return self.is_valid

#helper func for converting rotation curves
def set_quat_key_from_fcurve(curve_collection, key_index, dst_quat_key):
    keys=[]
    for fcurve in curve_collection.fcurves:
        keys.append(fcurve.keyframe_points[key_index])
    return curve_collection.curve_desc.set_quat_key_from_keys(dst_quat_key, keys)

def set_fcurve_from_quat_key(curve_collection, key_index, src_quat_key):
    keys=[]
    for fcurve in curve_collection.fcurves:
        keys.append(fcurve.keyframe_points[key_index])
    return curve_collection.curve_desc.set_keys_from_quat_key(keys, src_quat_key)

#helper func for converting position curves
def set_vec_key_from_fcurve(curve_collection, key_index, dst_quat_key):
    keys=[]
    for fcurve in curve_collection.fcurves:
        keys.append(fcurve.keyframe_points[key_index])
    return curve_collection.curve_desc.set_vec_key_from_keys(dst_quat_key, keys)

def set_fcurve_from_vec_key(curve_collection, key_index, src_quat_key):
    keys=[]
    for fcurve in curve_collection.fcurves:
        keys.append(fcurve.keyframe_points[key_index])
    return curve_collection.curve_desc.set_keys_from_vec_key(keys, src_quat_key)


def rotate_rotation_fcurves(action, pose_bone, rotation):
    curve_desc = get_curve_desc_for_bone(pose_bone)
    curve_collection = CurveCollection(action,curve_desc)
    if not curve_collection.is_valid:
        return OpResult(False, f"Failed to convert action {action.name}, reason: {curve_collection.error_message}")
    
    inv_rotation = rotation.inverted()

    quat_key = QuatKey()
    for key_index in range(curve_collection.key_count):
        set_quat_key_from_fcurve(curve_collection, key_index, quat_key)
        quat_key.value = rotation @ quat_key.value @ inv_rotation
        quat_key.handle_left = rotation @ quat_key.handle_left @ inv_rotation
        quat_key.handle_right = rotation @ quat_key.handle_right @ inv_rotation
        set_fcurve_from_quat_key(curve_collection, key_index, quat_key)
    
    return OpResult(True)


def rotate_position_fcurves(action, pose_bone, rotation):
    curve_desc = PositionCurveDesc(pose_bone)
    curve_collection = CurveCollection(action,curve_desc)
    if not curve_collection.is_valid:
        return OpResult(False, f"Failed to convert action {action.name}, reason: {curve_collection.error_message}")
    
    pos_key = VectorKey()
    for key_index in range(curve_collection.key_count):
        set_vec_key_from_fcurve(curve_collection, key_index,pos_key)
        pos_key.value = rotation @ pos_key.value
        pos_key.handle_left = rotation @ pos_key.handle_left
        pos_key.handle_right = rotation @ pos_key.handle_right
        set_fcurve_from_vec_key(curve_collection, key_index,pos_key)
    
    return OpResult(True)