from typing import Dict, List
from ..mtlib import *
from ..mtlib.ncl import *
from ..mtlib.base_editor import *
from ..mtlib.base_exporter import *
from .blender_plugin import *
import bpy
import mathutils

def progressCallback( what, i, count ):
    pass

def assertBlenderMode(expectedMode:str):
    try:
        bpy.context.object.mode == expectedMode
    except AttributeError:
        return expectedMode == 'OBJECT'

class BlenderExportBoneProxy(EditorNodeProxy):
    def __init__(self, bone, editBone, tfm):
        super().__init__(plugin)
        self.node = bone
        self._editBone = editBone
        self._tfm = tfm
        self._parent = None

    def unwrap(self):
        return self.node

    def setParent(self, parent):
        self._parent = parent

    def getTransform(self):
        return self._tfm

    def getParent(self):
        return self._parent

    def getName(self):
        return self.node.name

    def isHidden(self):
        return getattr(self.node, 'hide', False)

    def isBoneHidden(self):
        return getattr(self.node, 'hide', False)

    def isMeshNode(self):
        return False

    def isGroupNode(self):
        return False

    def isBoneNode(self):
        return True

    def isSplineNode(self):
        return False


class BlenderModelExporter(ModelExporterBase):
    def __init__(self) -> None:
        super().__init__(plugin)
        self.progressCallback = progressCallback

    def getObjects( self ):
        temp = list(bpy.data.objects)
        objects = []
        for o in temp:
            if not o in self.processedNodes:
                objects.append( BlenderNodeProxy( o ) )
        return objects

    #Based on the above method to ensure that we get joints as they are not included in bpy.data.objects.
    def getObjectBones( self ):
        armatureObj = None
        activeObj = bpy.context.view_layer.objects.active

        if activeObj is not None and activeObj.type == 'ARMATURE':
            armatureObj = activeObj
        else:
            for candidate in bpy.context.selected_objects:
                if candidate.type == 'ARMATURE':
                    armatureObj = candidate
                    break

        if armatureObj is None:
            return []

        previousActive = bpy.context.view_layer.objects.active
        previousMode = armatureObj.mode
        bpy.context.view_layer.objects.active = armatureObj

        if armatureObj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        tailRotationMatrix = mathutils.Matrix(((0.0, 1.0, 0.0, 0.0),
                                               (-1.0, 0.0, 0.0, 0.0),
                                               (0.0, 0.0, 1.0, 0.0),
                                               (0.0, 0.0, 0.0, 1.0)))
        tailRotationMatrixInv = tailRotationMatrix.inverted()

        editBones = {editBone.name: editBone for editBone in armatureObj.data.edit_bones}
        boneProxyByName: Dict[str, BlenderExportBoneProxy] = dict()
        objects: List[BlenderExportBoneProxy] = []

        for bone in armatureObj.data.bones:
            if bone.name not in editBones:
                continue

            editBone = editBones[bone.name]
            matrix = editBone.matrix.copy()
            matrix = matrix @ tailRotationMatrixInv
            tfm = self.convertMatrix3ToNclMat44(matrix)

            proxy = BlenderExportBoneProxy(bone, editBone, tfm)
            boneProxyByName[bone.name] = proxy
            objects.append(proxy)

        for proxy in objects:
            parent = proxy.node.parent
            if parent is not None:
                proxy.setParent(boneProxyByName.get(parent.name))

        if previousMode != 'EDIT':
            bpy.ops.object.mode_set(mode=previousMode, toggle=False)

        if previousActive is not None:
            bpy.context.view_layer.objects.active = previousActive

        return objects

    # def getObjectBones( self ):
    #     temp = list(bpy.data.objects)
    #     objects = []
    #     for o in temp:
    #         if not o in self.processedNodes:
    #             if o.type == 'ARMATURE' and o.name == bpy.context.selected_objects[0].name:
    #                 for ChildNode in enumerate(bpy.data.armatures[o.name].bones):
    #                     objects.append( BlenderNodeProxy( ChildNode ) )


    #     return objects


    def updateProgress( self, what, value, count = 0 ):
        self.logger.debug( f'updateProgress({what},{value},{count})')
        
    def updateSubProgress( self, what, value, count = 0 ):
        self.logger.debug( f'updateSubProgress({what},{value},{count})')

    def getEditorGroupCustomAttributeData( self, node: EditorNodeProxy  ) -> EditorCustomAttributeSetProxy:
        assertBlenderMode('OBJECT')
        return BlenderCustomAttributeSetProxy(node.unwrap())

    def getEditorPrimitiveCustomAttributeData( self, node: EditorNodeProxy  ) -> EditorCustomAttributeSetProxy:
        assertBlenderMode('OBJECT')
        return BlenderCustomAttributeSetProxy(node.unwrap())

    def getEditorJointCustomAttributeData( self, node: EditorNodeProxy  ) -> EditorCustomAttributeSetProxy:
        assertBlenderMode('OBJECT')
        return BlenderCustomAttributeSetProxy(node.unwrap())

    def convertPoint3ToNclVec3( self, v ) -> NclVec3:
        return NclVec3((v[0], v[1], v[2]))

    def convertPoint3ToNclVec3UV( self, v ) -> NclVec3:
        return NclVec3((v[0], 1 - v[1], v[2]))
        
    def convertPoint3ToNclVec4( self, v, w ) -> NclVec3:
        return NclVec4((v[0], v[1], v[2], w))
    
    def convertMatrix3ToNclMat43( self, v ) -> NclMat43:
        return nclCreateMat43((self.convertPoint3ToNclVec3(v[0]), 
                               self.convertPoint3ToNclVec3(v[1]), 
                               self.convertPoint3ToNclVec3(v[2]), 
                               self.convertPoint3ToNclVec3(v[3])))
        
    def convertMatrix3ToNclMat44( self, v ):
        return nclCreateMat44((self.convertPoint3ToNclVec4(v[0], 0), 
                               self.convertPoint3ToNclVec4(v[1], 0), 
                               self.convertPoint3ToNclVec4(v[2], 0), 
                               self.convertPoint3ToNclVec4(v[3], 1)))

    def processMaterial( self, material: EditorMaterialProxy ):
        self.logger.debug( f'processMaterial({material})')

    def processMesh( self, editorNode: EditorNodeProxy ):
        self.logger.debug( f'processMesh({editorNode})')
