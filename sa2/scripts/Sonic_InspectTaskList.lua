local core = require "sonic_core"

-- EDIT THESE
-- If you don't know listID bug Tenzit
-- There are 8 lists, 0-7
local listID = 2
local OBJECT_NAME = "MSGER"

-- Constants
local TASKLIST_ARRAY_BASE = 0x801fceb8
local NEXT_OFFSET = 0x4
local PREV_OFFSET = 0x0
local PARENT_OFFSET = 0x8
local CHILD_OFFSET = 0xc
local NAME_OFFSET = 0x44

function getTaskPos(taskPointer)
	local AWK_OFFSET = 0x34
	local taskAwk = ReadValue32(taskPointer + AWK_OFFSET)
	local x = ReadValueFloat(taskAwk + 0x14)
	local y = ReadValueFloat(taskAwk + 0x18)
	local z = ReadValueFloat(taskAwk + 0x1c)
	
	return x,y,z
end

function parseTaskList()
	local HEAD = ReadValue32(TASKLIST_ARRAY_BASE + 4 * listID)

	local node = HEAD
	local first = node
	local text = string.format("\n===== %s objects in List %d =====", OBJECT_NAME, listID)
	local count = 0

	while true do
		count = count + 1
		local nodeName = ReadValueString(ReadValue32(node + NAME_OFFSET), #OBJECT_NAME)
		if nodeName == OBJECT_NAME then
			local nX, nY, nZ = getTaskPos(node)
			text = text .. string.format("\n[%08X] %s @%4.2f,%4.2f,%4.2f", node, nodeName, nX, nY, nZ)
		end
		node = ReadValue32(node + NEXT_OFFSET)
		if node == first then
			break
		end
	end

	text = text .. string.format("\n===== Broke after %d items =====", count)

	SetScreenText(text)
end

function onScriptStart()
	parseTaskList()
end

function onScriptCancel()
	
end

function onScriptUpdate()
	parseTaskList()
end

function onStateLoaded()
	parseTaskList()
end

function onStateSaved()
	
end