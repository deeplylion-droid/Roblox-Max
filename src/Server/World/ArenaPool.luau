--!nonstrict
-- Slot per istanze (incursioni e visite) lontani dall'hub, riutilizzabili.
local Workspace = game:GetService("Workspace")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Config = require(ReplicatedStorage.Shared.Config)
local WorldBuilder = require(script.Parent.WorldBuilder)

local ArenaPool = {}
local free = {}
local inUse = {}

function ArenaPool.Init()
	for i = 1, Config.Arenas.Count do
		table.insert(free, i)
	end
end

function ArenaPool.Acquire(tag)
	local index = table.remove(free, 1)
	if not index then
		return nil
	end
	local folder = Instance.new("Folder")
	folder.Name = string.format("Arena_%d_%s", index, tag or "x")
	folder.Parent = Workspace.Arenas
	inUse[index] = folder
	return { Index = index, Origin = WorldBuilder.ArenaOrigin(index), Folder = folder }
end

function ArenaPool.Release(slot)
	if not slot or not inUse[slot.Index] then
		return
	end
	inUse[slot.Index]:Destroy()
	inUse[slot.Index] = nil
	table.insert(free, slot.Index)
end

return ArenaPool
