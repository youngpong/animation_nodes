import bpy, math
from bpy.types import Node
from mn_node_base import AnimationNode
from mn_execution import nodePropertyChanged
from mn_utils import *
from mn_object_utils import *
from mn_node_helper import *

class BakedSoundPropertyGroup(bpy.types.PropertyGroup):
	low = bpy.props.FloatProperty(name = "Lowest Frequency", default = 10.0)
	high = bpy.props.FloatProperty(name = "Highest Frequency", default = 5000.0)
	path = bpy.props.StringProperty(name = "Path", default = "")
	propertyName = bpy.props.StringProperty(name = "Property Path", default = "")

class SoundInputNode(Node, AnimationNode):
	bl_idname = "SoundInputNode"
	bl_label = "Sound Input"
	
	bakedSound = bpy.props.CollectionProperty(type = BakedSoundPropertyGroup)
	soundObjectName = bpy.props.StringProperty()
	filePath = bpy.props.StringProperty()
	
	def init(self, context):
		self.inputs.new("FloatSocket", "Value")
		self.outputs.new("FloatListSocket", "Strengths")
		self.outputs.new("FloatSocket", "Strength")
		
	def draw_buttons(self, context, layout):
		row = layout.row(align = True)
		row.prop(self, "filePath", text = "")
		selectPath = row.operator("mn.select_sound_file_path", "Select Path")
		selectPath.nodeTreeName = self.id_data.name
		selectPath.nodeName = self.name
		
		row = layout.row(align = True)
		bake = row.operator("mn.bake_sound_to_node", "Bake")
		bake.nodeTreeName = self.id_data.name
		bake.nodeName = self.name
		loadSound = row.operator("mn.set_sound_in_sequence_editor", "Load Sound")
		loadSound.filePath = self.filePath
		
		layout.label("Value from 0 to 1 for different frequences.")
		
	def execute(self, input):
		output = {}
		soundObject = self.getSoundObject()
		strenghts = self.getStrengthList(soundObject)
		output["Strengths"] = strenghts
		output["Strength"] = self.mapValueToStrengthList(strenghts, input["Value"])
		return output
		
	def getStrengthList(self, soundObject):
		strenghts = []
		for item in self.bakedSound:
			strenghts.append(soundObject[item.propertyName])
		return strenghts
		
	def mapValueToStrengthList(self, strengths, value):
		if len(strengths) > 0:
			length = len(strengths)
			value *= length
			lower = strengths[max(min(math.floor(value), length - 1), 0)]
			upper = strengths[max(min(math.ceil(value), length - 1), 0)]
			influence = value % 1.0
			return lower * (1 - influence) + upper * influence
		return 0.0
		
	def bakeSound(self):
		bpy.context.scene.frame_current = 1
		soundObject = self.getSoundObject()
		self.removeSoundCurves(soundObject)
		soundCombinations = [(0, 50), (50, 150), (150, 300), (300, 500), (500, 1000), (1000, 2000), (2000, 4000), (4000, 10000), (10000, 20000)]
		wm = bpy.context.window_manager
		wm.progress_begin(0.0, len(soundCombinations))
		wm.progress_update(0.0)
		for index, (low, high) in enumerate(soundCombinations):
			self.bakeIndividualSound(soundObject, self.filePath, low, high)
			wm.progress_update(index + 1.0)
		wm.progress_end()
		soundObject.hide = True
		
	def getSoundObject(self):
		soundObject = bpy.data.objects.get(self.soundObjectName)
		if soundObject is None:
			soundObject = bpy.data.objects.new(getPossibleObjectName("sound object"), None)
			soundObject.parent = getMainObjectContainer()
			self.soundObjectName = soundObject.name
			bpy.context.scene.objects.link(soundObject)
		return soundObject
		
	def removeSoundCurves(self, soundObject):
		for item in self.bakedSound:
			fCurve = getFCurveWithDataPath(soundObject, '["' + item.propertyName + '"]')
			if fCurve is not None:
				soundObject.animation_data.action.fcurves.remove(fCurve)
		self.bakedSound.clear()
		
	def bakeIndividualSound(self, soundObject, filePath, low, high):
		propertyName = "sound " + str(low) + " - " + str(high)
		propertyPath = '["' + propertyName + '"]'
		deselectAllFCurves(soundObject)
		soundObject[propertyName] = 0.0
		soundObject.keyframe_insert(frame = 1, data_path = propertyPath)
		bpy.context.area.type = "GRAPH_EDITOR"
		soundObject.hide = False
		deselectAll()
		setActive(soundObject)
		bpy.ops.graph.sound_bake(
			filepath = filePath,
			low = low,
			high = high)
		bpy.context.area.type = "NODE_EDITOR"
		
		item = self.bakedSound.add()
		item.low = low
		item.high = high
		item.path = filePath
		item.propertyName = propertyName
		
	def copy(self, node):
		self.soundObjectName = ""
		self.bakedSound.clear()
		
	def free(self):
		bpy.context.scene.objects.unlink(self.getSoundObject())
		
class BakeSoundToNode(bpy.types.Operator):
	bl_idname = "mn.bake_sound_to_node"
	bl_label = "Bake Sound to Node"
	
	nodeTreeName = bpy.props.StringProperty()
	nodeName = bpy.props.StringProperty()
	
	def execute(self, context):
		node = getNode(self.nodeTreeName, self.nodeName)
		node.bakeSound()
		return {'FINISHED'}	
		
class SelectSoundFilePath(bpy.types.Operator):
	bl_idname = "mn.select_sound_file_path"
	bl_label = "Select Sound File"
	
	nodeTreeName = bpy.props.StringProperty()
	nodeName = bpy.props.StringProperty()
	filepath = bpy.props.StringProperty(subtype = "FILE_PATH")
	
	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return { 'RUNNING_MODAL' }
		
	def execute(self, context):
		node = getNode(self.nodeTreeName, self.nodeName)
		node.filePath = self.filepath
		return {'FINISHED'}	
		
class SetSoundInSequenceEditor(bpy.types.Operator):
	bl_idname = "mn.set_sound_in_sequence_editor"
	bl_label = "Load Sound in Blender"
	
	filePath = bpy.props.StringProperty()
		
	def execute(self, context):
		scene = bpy.context.scene
		scene.sequence_editor_clear()
		scene.sequence_editor_create()
		scene.sequence_editor.sequences.new_sound("Sound", self.filePath, channel = 0, frame_start = 1)
		return {'FINISHED'}	
		
		
# register
################################
		
def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)